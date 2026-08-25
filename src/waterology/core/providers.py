from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from waterology.core.records import ExecutorReference

OperationalState = Literal[
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


@dataclass(frozen=True)
class PreparedRun:
    run_id: str
    experiment_id: str
    commit_sha: str
    worktree: Path
    staging: Path


@dataclass(frozen=True)
class ProviderLaunch:
    state: OperationalState
    reference: ExecutorReference | None
    process_id: int | None = None


@dataclass(frozen=True)
class ProviderInspection:
    state: OperationalState
    prior_known_state: OperationalState | None = None
    terminal_state: Literal["completed", "failed", "cancelled", "lost"] | None = None
    exit_code: int | None = None


@dataclass(frozen=True)
class ProviderCollection:
    stdout: str
    stderr: str
    metrics: dict[str, object]
    exit_code: int | None
    terminal_state: Literal["completed", "failed", "cancelled", "lost"]


class ExecutionProvider(Protocol):
    def prepare(self) -> PreparedRun: ...

    def launch(self, prepared: PreparedRun) -> ProviderLaunch: ...

    def inspect(self, prepared: PreparedRun) -> ProviderInspection: ...

    def cancel(self, prepared: PreparedRun) -> ProviderInspection: ...

    def collect(self, prepared: PreparedRun) -> ProviderCollection: ...
