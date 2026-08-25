import json
import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")


def _portable_project_path(value: str) -> str:
    if not value or "\\" in value or any(ord(character) < 32 for character in value):
        raise ValueError("must be a relative project path using forward slashes")
    path = PurePosixPath(value)
    if path.is_absolute() or _WINDOWS_ABSOLUTE.match(value) or ".." in path.parts:
        raise ValueError("must be a relative project path within the project")
    if path.as_posix() in {".", ""}:
        raise ValueError("must name a relative project path")
    return path.as_posix()


def _portable_project_paths(values: tuple[str, ...]) -> tuple[str, ...]:
    validated = tuple(_portable_project_path(value) for value in values)
    if len(set(validated)) != len(validated):
        raise ValueError("project paths must not contain duplicates")
    return validated


class ConcurrencyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_runs: int = Field(default=1, ge=1)


class ArchiveConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allow_missing_outputs: bool = False
    environment_allowlist: tuple[str, ...] = ()
    log_redactions: tuple[str, ...] = ()

    @field_validator("log_redactions")
    @classmethod
    def _validate_log_redactions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value:
                raise ValueError("log redaction patterns must not be empty")
            try:
                re.compile(value)
            except re.error as error:
                raise ValueError(f"invalid log redaction pattern: {error}") from error
        return values


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

    @field_validator("outputs")
    @classmethod
    def _validate_outputs(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        validated = _portable_project_paths(values)
        paths = tuple(PurePosixPath(value) for value in validated)
        for index, path in enumerate(paths):
            if any(path in other.parents or other in path.parents for other in paths[index + 1 :]):
                raise ValueError("declared outputs must not overlap")
        return validated

    @field_validator("metrics")
    @classmethod
    def _validate_metrics(cls, values: tuple[MetricExtractor, ...]) -> tuple[MetricExtractor, ...]:
        names = [metric.name for metric in values]
        if len(set(names)) != len(names):
            raise ValueError("metric names must be unique")
        return values

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
        f"log_redactions = {_toml_array(config.archive.log_redactions)}",
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
