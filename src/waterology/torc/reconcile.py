from pathlib import Path

from waterology.core.providers import OperationalState, ProviderInspection
from waterology.torc.gateway import (
    TorcGateway,
    TorcUnavailableError,
    TorcWorkflowNotFoundError,
)
from waterology.torc.states import map_torc_state


def reconcile_workflow(
    gateway: TorcGateway,
    workflow_id: str,
    *,
    cwd: Path,
    prior_known_state: OperationalState,
) -> ProviderInspection:
    try:
        observation = gateway.inspect(workflow_id, cwd=cwd)
    except TorcWorkflowNotFoundError:
        return ProviderInspection(
            state="lost",
            prior_known_state=prior_known_state,
            terminal_state="lost",
        )
    except TorcUnavailableError:
        return ProviderInspection(state="unknown", prior_known_state=prior_known_state)

    state = map_torc_state(observation.state)
    normalized = observation.state.strip().lower()
    terminal_state = None
    exit_code = None
    if normalized == "completed":
        terminal_state = "completed"
        exit_code = 0
    elif normalized == "failed":
        terminal_state = "failed"
        exit_code = _first_exit_code(observation.jobs)
    elif normalized in {"canceled", "cancelled"}:
        terminal_state = "cancelled"
    return ProviderInspection(
        state=state,
        prior_known_state=prior_known_state,
        terminal_state=terminal_state,
        exit_code=exit_code,
    )


def _first_exit_code(jobs: tuple[dict[str, object], ...]) -> int | None:
    for job in jobs:
        for field in ("return_code", "exit_code"):
            value = job.get(field)
            if isinstance(value, int):
                return value
    return None
