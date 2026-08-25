import json
import os
import re
import tempfile
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from waterology.core.errors import WaterologyError

_PROFILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class MachineConfigError(WaterologyError):
    code = "machine_config_invalid"


class ComputeProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["torc"] = "torc"
    mode: Literal["local", "remote", "slurm"]
    target_shell: Literal["posix", "windows"] = "windows" if os.name == "nt" else "posix"
    api_url: str = Field(min_length=1)
    torc_profile: str | None = None
    slurm_account: str | None = None
    ssh_alias: str | None = None
    local_output_root: str | None = None
    dashboard_url: str | None = None
    trusted: bool = False

    @field_validator("api_url", "dashboard_url")
    @classmethod
    def _validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("must be an HTTP or HTTPS URL")
        if any(character.isspace() or ord(character) < 32 for character in value):
            raise ValueError("must not contain whitespace or control characters")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("must not contain credentials")
        return value.rstrip("/")

    @model_validator(mode="after")
    def _require_remote_fields(self) -> "ComputeProfile":
        if self.mode == "remote" and not self.ssh_alias:
            raise ValueError("remote profiles require ssh_alias")
        if self.mode == "slurm" and not self.slurm_account:
            raise ValueError("slurm profiles require slurm_account")
        return self


class MachineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trusted_profiles: tuple[str, ...] = ()
    profiles: dict[str, ComputeProfile] = Field(default_factory=dict)

    @field_validator("trusted_profiles")
    @classmethod
    def _unique_trusted_profiles(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(values)) != len(values):
            raise ValueError("trusted_profiles must not contain duplicates")
        return values

    @model_validator(mode="after")
    def _known_trusted_profiles(self) -> "MachineConfig":
        invalid = sorted(name for name in self.profiles if _PROFILE_NAME.fullmatch(name) is None)
        if invalid:
            raise ValueError(f"invalid compute profile names: {', '.join(invalid)}")
        missing = sorted(set(self.trusted_profiles) - set(self.profiles))
        if missing:
            raise ValueError(f"trusted profiles do not exist: {', '.join(missing)}")
        return self

    def profile(self, name: str) -> ComputeProfile:
        try:
            profile = self.profiles[name]
        except KeyError as error:
            raise MachineConfigError(f"Compute profile does not exist: {name}") from error
        return profile.model_copy(update={"trusted": name in self.trusted_profiles})


def machine_config_path(environment: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environment is None else environment
    if explicit := values.get("WATEROLOGY_CONFIG"):
        return Path(explicit).expanduser()
    if xdg := values.get("XDG_CONFIG_HOME"):
        return Path(xdg).expanduser() / "waterology" / "config.toml"
    return Path.home() / ".config" / "waterology" / "config.toml"


def load_machine_config(path: Path | None = None) -> MachineConfig:
    source = path or machine_config_path()
    if not source.exists():
        return MachineConfig()
    if source.is_symlink() or not source.is_file():
        raise MachineConfigError(f"Machine configuration must be a regular file: {source}")
    try:
        with source.open("rb") as stream:
            config = MachineConfig.model_validate(tomllib.load(stream))
        profiles = {
            name: _normalize_profile_paths(profile, source.parent)
            for name, profile in config.profiles.items()
        }
        return config.model_copy(update={"profiles": profiles})
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        if isinstance(error, MachineConfigError):
            raise
        raise MachineConfigError(f"Invalid machine configuration: {source}: {error}") from error


def trust_profile(path: Path, name: str) -> MachineConfig:
    config = load_machine_config(path)
    config.profile(name)
    trusted = tuple(sorted(set(config.trusted_profiles) | {name}))
    updated = config.model_copy(update={"trusted_profiles": trusted})
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, machine_config_toml(updated))
    return updated


def machine_config_toml(config: MachineConfig) -> str:
    lines = [f"trusted_profiles = {_toml_array(config.trusted_profiles)}"]
    for name in sorted(config.profiles):
        profile = config.profiles[name]
        lines.extend(
            [
                "",
                f"[profiles.{json.dumps(name)}]",
                f"provider = {json.dumps(profile.provider)}",
                f"mode = {json.dumps(profile.mode)}",
                f"api_url = {json.dumps(profile.api_url)}",
            ]
        )
        for field in (
            "torc_profile",
            "slurm_account",
            "target_shell",
            "ssh_alias",
            "local_output_root",
            "dashboard_url",
        ):
            if value := getattr(profile, field):
                lines.append(f"{field} = {json.dumps(value)}")
    return "\n".join(lines) + "\n"


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def _normalize_profile_paths(profile: ComputeProfile, config_directory: Path) -> ComputeProfile:
    if profile.local_output_root is None:
        return profile
    root = Path(profile.local_output_root).expanduser()
    if not root.is_absolute():
        root = config_directory / root
    return profile.model_copy(update={"local_output_root": str(root.absolute())})


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.chmod(temporary, 0o600)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = -1
        with stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
        raise
