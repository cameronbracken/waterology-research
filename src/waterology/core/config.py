import json
import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

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


class ResourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cpus: int = Field(default=1, ge=1)
    memory_mb: int = Field(default=1024, ge=1)
    walltime_minutes: int | None = Field(default=None, ge=1)
    gpus: int = Field(default=0, ge=0)


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


class WorkflowConfig(BaseModel):
    """Portable execution and evidence contract; TORC owns job dependencies."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    command: tuple[str, ...] = ()
    torc_file: str | None = None
    outputs: tuple[str, ...] = ()
    metrics: tuple[MetricExtractor, ...] = ()
    environment_files: tuple[str, ...] = ()
    input_files: dict[str, str] = Field(default_factory=dict)
    input_instructions: dict[str, str] = Field(default_factory=dict)
    restore: tuple[tuple[str, ...], ...] = ()
    environment_probe: tuple[str, ...] = ()
    description: str = ""

    _paths = field_validator("outputs", "environment_files")(_portable_project_paths)

    @model_validator(mode="after")
    def validate_contract(self):
        if bool(self.command) == bool(self.torc_file):
            raise ValueError("Specify exactly one of command or torc_file")
        if self.torc_file:
            _portable_project_path(self.torc_file)
        for command in (self.command, self.environment_probe, *self.restore):
            if any(not arg or "\x00" in arg for arg in command):
                raise ValueError("Command arguments must be nonempty and contain no null bytes")
        if any(not command for command in self.restore):
            raise ValueError("Restore commands cannot be empty")
        for path, digest in self.input_files.items():
            _portable_project_path(path)
            if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ValueError("Input identity must be a SHA-256 digest")
        for path in self.input_instructions:
            _portable_project_path(path)
        if any(
            PurePosixPath(p).parts[0] in {".git", ".waterology", ".waterology-reference"}
            for p in self.outputs
        ):
            raise ValueError("Outputs cannot overlap workflow control state")
        paths = [PurePosixPath(p) for p in self.outputs]
        for i, path in enumerate(paths):
            if any(path in other.parents or other in path.parents for other in paths[i + 1 :]):
                raise ValueError("Output paths may not overlap")
        return self


class OutputCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    mode: Literal["bytes", "numeric", "statistical"] = "bytes"
    field: str | None = None
    atol: float = Field(default=0, ge=0, allow_inf_nan=False)
    rtol: float = Field(default=0, ge=0, allow_inf_nan=False)
    validator: str | None = None
    _path = field_validator("path")(_portable_project_path)

    @model_validator(mode="after")
    def validate_check(self):
        if self.mode == "numeric" and not self.field:
            raise ValueError("Numeric checks require a JSON field")
        if self.mode == "statistical" and not self.validator:
            raise ValueError("Statistical checks require a validator workflow")
        if self.mode != "numeric" and (self.field is not None or self.atol != 0 or self.rtol != 0):
            raise ValueError("Field and tolerances apply only to numeric checks")
        if self.mode != "statistical" and self.validator:
            raise ValueError("validator applies only to statistical checks")
        return self


class DeliverableConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    workflow: str
    reference_run: str = Field(pattern=r"^run-[a-z0-9][a-z0-9-]{0,62}$")
    checks: tuple[OutputCheck, ...] = Field(min_length=1)
    description: str = ""


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=120)
    artifact_roots: tuple[str, ...] = ("artifacts",)
    command: tuple[str, ...] = ()
    environment_files: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    default_compute_profile: str = Field(default="direct", min_length=1)
    workflows: dict[str, WorkflowConfig] = Field(default_factory=dict)
    deliverables: dict[str, DeliverableConfig] = Field(default_factory=dict)
    study_contracts: dict[str, str] = Field(default_factory=dict)
    discovery: dict[str, object] = Field(default_factory=dict)
    torc_file: str | None = None
    restore: tuple[tuple[str, ...], ...] = ()
    environment_probe: tuple[str, ...] = ()
    concurrency: ConcurrencyConfig = ConcurrencyConfig()
    resources: ResourceConfig = ResourceConfig()
    archive: ArchiveConfig = ArchiveConfig()
    metrics: tuple[MetricExtractor, ...] = ()

    _validate_artifact_roots = field_validator("artifact_roots")(_portable_project_paths)
    _validate_environment_files = field_validator("environment_files")(_portable_project_paths)

    @model_serializer(mode="wrap")
    def serialize_compatible(self, handler):
        payload = handler(self)
        for key in (
            "workflows",
            "deliverables",
            "study_contracts",
            "discovery",
            "torc_file",
            "restore",
            "environment_probe",
        ):
            if not payload.get(key):
                payload.pop(key, None)
        return payload

    @model_validator(mode="after")
    def validate_registry(self):
        for group in (self.workflows, self.deliverables, self.study_contracts):
            for name in group:
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,95}", name):
                    raise ValueError("Invalid registry name")
        for relative in self.study_contracts.values():
            _portable_project_path(relative)
        if self.torc_file:
            _portable_project_path(self.torc_file)
            if self.command != ("torc", "workflow", self.torc_file):
                raise ValueError("Use a named workflow for native TORC YAML")
        return self

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
        "[resources]",
        f"cpus = {config.resources.cpus}",
        f"gpus = {config.resources.gpus}",
    ]
    lines.append(f"memory_mb = {config.resources.memory_mb}")
    if config.resources.walltime_minutes is not None:
        lines.append(f"walltime_minutes = {config.resources.walltime_minutes}")
    lines.extend(
        [
            "",
            "[archive]",
            f"allow_missing_outputs = {str(config.archive.allow_missing_outputs).lower()}",
            f"environment_allowlist = {_toml_array(config.archive.environment_allowlist)}",
            f"log_redactions = {_toml_array(config.archive.log_redactions)}",
        ]
    )
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
    import tomlkit

    document = tomlkit.parse("\n".join(lines) + "\n")
    for key in (
        "workflows",
        "deliverables",
        "study_contracts",
        "discovery",
        "torc_file",
        "restore",
        "environment_probe",
    ):
        value = (
            config.model_dump(mode="json", exclude_none=True).get(key)
            if key != "torc_file"
            else config.torc_file
        )
        if value:
            document[key] = value
    return tomlkit.dumps(document)


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"
