import json
import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")


def _portable_project_path(value: str) -> str:
    if not value or "\\" in value or "\x00" in value:
        raise ValueError("must be a relative project path using forward slashes")
    path = PurePosixPath(value)
    if path.is_absolute() or _WINDOWS_ABSOLUTE.match(value) or ".." in path.parts:
        raise ValueError("must be a relative project path within the project")
    if path.as_posix() in {".", ""}:
        raise ValueError("must name a relative project path")
    return path.as_posix()


def _portable_project_paths(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_portable_project_path(value) for value in values)


class ConcurrencyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_runs: int = Field(default=1, ge=1)


class ArchiveConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allow_missing_outputs: bool = False
    environment_allowlist: tuple[str, ...] = ()


class MetricExtractor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    path: str
    format: Literal["json"] = "json"
    field: str = Field(min_length=1)

    _validate_path = field_validator("path")(_portable_project_path)


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=120)
    artifact_roots: tuple[str, ...] = ("artifacts",)
    command: tuple[str, ...] = ()
    environment_files: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    default_compute_profile: str = Field(default="direct", min_length=1)
    concurrency: ConcurrencyConfig = ConcurrencyConfig()
    archive: ArchiveConfig = ArchiveConfig()
    metrics: tuple[MetricExtractor, ...] = ()

    _validate_artifact_roots = field_validator("artifact_roots")(_portable_project_paths)
    _validate_environment_files = field_validator("environment_files")(_portable_project_paths)
    _validate_outputs = field_validator("outputs")(_portable_project_paths)

    @field_validator("name", "default_compute_profile")
    @classmethod
    def _strip_nonempty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("command")
    @classmethod
    def _validate_command(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not argument or "\x00" in argument for argument in value):
            raise ValueError("command arguments must be nonempty and contain no null bytes")
        return value


def load_project_config(path: Path) -> ProjectConfig:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    return ProjectConfig.model_validate(data)


def default_project_config(name: str) -> ProjectConfig:
    return ProjectConfig(name=name)


def project_config_toml(config: ProjectConfig) -> str:
    lines = [
        f"schema_version = {config.schema_version}",
        f"name = {json.dumps(config.name)}",
        f"artifact_roots = {_toml_array(config.artifact_roots)}",
        f"command = {_toml_array(config.command)}",
        f"environment_files = {_toml_array(config.environment_files)}",
        f"outputs = {_toml_array(config.outputs)}",
        f"default_compute_profile = {json.dumps(config.default_compute_profile)}",
        "",
        "[concurrency]",
        f"max_runs = {config.concurrency.max_runs}",
        "",
        "[archive]",
        f"allow_missing_outputs = {str(config.archive.allow_missing_outputs).lower()}",
        f"environment_allowlist = {_toml_array(config.archive.environment_allowlist)}",
    ]
    for metric in config.metrics:
        lines.extend(
            [
                "",
                "[[metrics]]",
                f"name = {json.dumps(metric.name)}",
                f"path = {json.dumps(metric.path)}",
                f"format = {json.dumps(metric.format)}",
                f"field = {json.dumps(metric.field)}",
            ]
        )
    return "\n".join(lines) + "\n"


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"
