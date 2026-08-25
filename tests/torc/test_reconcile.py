from pathlib import Path

from waterology.core.providers import ProviderInspection
from waterology.torc.gateway import (
    TorcUnavailableError,
    TorcWorkflowNotFoundError,
    TorcWorkflowObservation,
)
from waterology.torc.reconcile import reconcile_workflow


class FakeGateway:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome

    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome  # type: ignore[return-value]


def test_unreachable_torc_becomes_reversible_unknown(tmp_path: Path) -> None:
    result = reconcile_workflow(
        FakeGateway(TorcUnavailableError("offline")),  # type: ignore[arg-type]
        "42",
        cwd=tmp_path,
        prior_known_state="running",
    )

    assert result == ProviderInspection(state="unknown", prior_known_state="running")


def test_confirmed_absent_workflow_becomes_lost(tmp_path: Path) -> None:
    result = reconcile_workflow(
        FakeGateway(TorcWorkflowNotFoundError("gone")),  # type: ignore[arg-type]
        "42",
        cwd=tmp_path,
        prior_known_state="running",
    )

    assert result.state == "lost"
    assert result.terminal_state == "lost"


def test_terminal_torc_state_waits_for_collection(tmp_path: Path) -> None:
    result = reconcile_workflow(
        FakeGateway(TorcWorkflowObservation("42", "completed", (), {})),  # type: ignore[arg-type]
        "42",
        cwd=tmp_path,
        prior_known_state="running",
    )

    assert result.state == "collecting"
    assert result.terminal_state == "completed"
