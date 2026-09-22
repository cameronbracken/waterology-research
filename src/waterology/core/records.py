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


def _portable_record_path(value: str) -> str:
    return _portable_record_paths((value,))[0]


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    project_id: str = Field(min_length=1)
    parent_experiment_id: str | None = None
    hypothesis: str = Field(min_length=1)
    workflow: str | None = None
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


SessionState = Literal[
    "created",
    "running",
    "waiting",
    "completed",
    "failed",
    "cancelled",
    "lost",
]


class AgentAttemptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    number: int = Field(ge=1)
    state: SessionState
    prompt_path: str
    events_path: str
    stderr_path: str
    started_at: str | None = None
    finished_at: str | None = None
    supervisor_pid: int | None = Field(default=None, ge=1)
    process_pid: int | None = Field(default=None, ge=1)
    native_session_id: str | None = None
    exit_code: int | None = None
    initial_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    resulting_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40,64}$")

    _validate_paths = field_validator("prompt_path", "events_path", "stderr_path")(
        _portable_record_path
    )


class AgentSessionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^session-[0-9a-f]{16}$")
    project_id: str = Field(min_length=1)
    experiment_id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    runtime: Literal["claude", "codex", "opencode"]
    role: str = Field(min_length=1)
    compute_profile: str = Field(min_length=1)
    worktree: str = Field(min_length=1)
    task_path: str = Field(min_length=1)
    state: SessionState = "created"
    native_session_id: str | None = None
    supervisor_pid: int | None = Field(default=None, ge=1)
    process_pid: int | None = Field(default=None, ge=1)
    created_at: str
    updated_at: str
    finished_at: str | None = None
    exit_code: int | None = None
    initial_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    resulting_commits: tuple[str, ...] = ()
    attempts: tuple[AgentAttemptRecord, ...] = ()

    _validate_paths = field_validator("worktree", "task_path")(_portable_record_path)

    @field_validator("role", "compute_profile")
    @classmethod
    def _nonblank_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class AgentProcessRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pid: int = Field(ge=1, strict=True)
    started_at: str
    native_session_id: str | None = None


class AgentStartingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    started_at: str
    containment: Literal["process_group", "windows_job"]


class AgentResultRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["completed", "failed", "cancelled"]
    exit_code: int = Field(strict=True)
    finished_at: str
    native_session_id: str | None = None
    process_pid: int | None = Field(default=None, ge=1, strict=True)
    resulting_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")


class SessionNoteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^note-[0-9a-f]{16}$")
    session_id: str = Field(pattern=r"^session-[0-9a-f]{16}$")
    text: str = Field(min_length=1)
    author: str | None = None
    created_at: str


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^evidence-[0-9a-f]{16}$")
    experiment_id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    claim: str = Field(min_length=1)
    kind: Literal["note", "metric", "source", "artifact"] = "note"
    path: str | None = None
    run_id: str | None = Field(default=None, pattern=r"^run-[a-z0-9][a-z0-9-]{0,62}$")
    session_id: str | None = Field(default=None, pattern=r"^session-[0-9a-f]{16}$")
    created_at: str

    @field_validator("path")
    @classmethod
    def _validate_optional_path(cls, value: str | None) -> str | None:
        return _portable_record_path(value) if value is not None else None


class ArtifactReferenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^artifact-[0-9a-f]{16}$")
    experiment_id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    path: str = Field(min_length=1)
    label: str | None = None
    run_id: str | None = Field(default=None, pattern=r"^run-[a-z0-9][a-z0-9-]{0,62}$")
    session_id: str | None = Field(default=None, pattern=r"^session-[0-9a-f]{16}$")
    created_at: str

    _validate_path = field_validator("path")(_portable_record_path)


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
    seal_state: Literal["clean", "revised", "tampered", "unlocked"] = "unlocked"
    seal_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


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
    sessions: int = 0
    session_notes: int = 0
    evidence: int = 0
    artifact_references: int = 0
    rejected_records: int = 0
    warnings: tuple[str, ...] = ()
