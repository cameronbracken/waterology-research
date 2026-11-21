"""Optional personal settings, kept outside distributable runtime assets."""

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from waterology.core.errors import WaterologyError


class UserConfigError(WaterologyError):
    code = "user_config_invalid"


class CredentialSettings(BaseModel):
    """Dotenv file that fills missing research API keys. An empty path disables it."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    # User-level location resolved against each user's home directory.
    file: str = "~/.config/secrets/research.env"  # waterology: allow-abs-path

    @field_validator("file")
    @classmethod
    def valid_file(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Credentials path must not contain NUL")
        return value.strip()


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    credentials: CredentialSettings = Field(default_factory=CredentialSettings)


def user_config_path(environment: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environment is None else environment
    if explicit := values.get("WATEROLOGY_CONFIG"):
        return Path(explicit).expanduser()
    if xdg := values.get("XDG_CONFIG_HOME"):
        return Path(xdg).expanduser() / "waterology" / "config.toml"
    return Path.home() / ".config" / "waterology" / "config.toml"


def load_user_config(path: Path | None = None) -> UserSettings:
    source = path or user_config_path()
    if not source.exists():
        return UserSettings()
    if source.is_symlink() or not source.is_file():
        raise UserConfigError(f"User configuration must be a regular file: {source}")
    try:
        with source.open("rb") as stream:
            return UserSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        raise UserConfigError(f"Invalid user configuration: {source}") from error
