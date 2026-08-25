import re
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")


def _portable_record_paths(values: tuple[str, ...]) -> tuple[str, ...]:
    validated = []
    for value in values:
        path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or any(ord(character) < 32 for character in value)
            or path.is_absolute()
            or _WINDOWS_ABSOLUTE.match(value)
            or ".." in path.parts
            or path.as_posix() == "."
        ):
            raise ValueError("must contain relative project paths")
        validated.append(path.as_posix())
    if len(set(validated)) != len(validated):
        raise ValueError("must not contain duplicate project paths")
    return tuple(validated)


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    project_id: str = Field(min_length=1)
    parent_experiment_id: str | None = None
    hypothesis: str = Field(min_length=1)
    base_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    branch: str = Field(min_length=1)
    worktree: str = Field(min_length=1)
    owner: str | None = None
    status: Literal["provisional", "frozen"] = "provisional"
    created_at: str
    frozen_at: str | None = None
    decision_required: bool = False


class ExperimentNoteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^note-[0-9a-f]{16}$")
    experiment_id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    text: str = Field(min_length=1)
    author: str | None = None
    created_at: str


class WorktreeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: str
    branch: str
    path: str
    owner: str | None = None
    exists: bool


class ExecutorReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["torc"] = "torc"
    compute_profile: str = Field(min_length=1)
    api_url: str = Field(min_length=1)
    execution_mode: Literal["local", "remote", "slurm"]
    workflow_id: str = Field(min_length=1)
    job_ids: tuple[str, ...] = ()
    torc_version: str = Field(min_length=1)
    workflow_spec_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class ManagedRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(pattern=r"^run-[a-z0-9][a-z0-9-]{0,62}$")
    experiment_id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    operational_state: Literal[
        "queued",
        "preparing",
        "running",
        "collecting",
        "completed",
        "failed",
        "cancelled",
        "unknown",
        "lost",
    ]
    started_at: str
    last_observed_at: str | None = None
    reference: ExecutorReference | None = None


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    run_id: str = Field(pattern=r"^run-[a-z0-9][a-z0-9-]{0,62}$")
    project_id: str
    experiment_id: str
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    command: tuple[str, ...]
    started_at: str
    finished_at: str
    executor: Literal["direct", "torc"] = "direct"
    executor_reference: ExecutorReference | None = None
    process_id: int | None = Field(default=None, ge=1)
    terminal_state: Literal["completed", "failed", "cancelled", "lost"]
    exit_code: int | None
    declared_artifacts: tuple[str, ...]
    collected_artifacts: tuple[str, ...]
    missing_artifacts: tuple[str, ...]

    _validate_declared_artifacts = field_validator("declared_artifacts")(_portable_record_paths)
    _validate_collected_artifacts = field_validator("collected_artifacts")(_portable_record_paths)
    _validate_missing_artifacts = field_validator("missing_artifacts")(_portable_record_paths)

    @model_validator(mode="after")
    def _consistent_executor_reference(self) -> "RunManifest":
        if self.executor == "torc" and self.executor_reference is None:
            raise ValueError("TORC manifests require an executor reference")
        if self.executor == "direct" and self.executor_reference is not None:
            raise ValueError("direct manifests must not contain a TORC executor reference")
        return self


class ArchiveVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    valid: bool
    missing: tuple[str, ...]
    changed: tuple[str, ...]
    unexpected: tuple[str, ...]


class AssessmentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^assessment-[0-9a-f]{16}$")
    run_id: str = Field(pattern=r"^run-[a-z0-9][a-z0-9-]{0,62}$")
    experiment_id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    kind: Literal["invalid", "no_answer", "answer"]
    conclusion: str = Field(min_length=1)
    author: str = Field(min_length=1)
    evidence: tuple[str, ...] = ()
    note: str | None = None
    created_at: str


class RepairResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projects: int
    experiments: int
    runs: int
    assessments: int
    artifacts: int
    rejected_records: int = 0
    warnings: tuple[str, ...] = ()
