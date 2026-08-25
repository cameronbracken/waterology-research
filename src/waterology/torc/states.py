from typing import Literal

from waterology.core.errors import WaterologyError

OperationalState = Literal["queued", "preparing", "running", "collecting", "unknown"]


class TorcStateError(WaterologyError):
    code = "torc_state_invalid"


_STATE_MAP: dict[str, OperationalState] = {
    "blocked": "preparing",
    "created": "preparing",
    "initialized": "preparing",
    "uninitialized": "preparing",
    "pending": "queued",
    "queued": "queued",
    "ready": "preparing",
    "starting": "preparing",
    "running": "running",
    "completed": "collecting",
    "failed": "collecting",
    "canceled": "collecting",
    "cancelled": "collecting",
    "terminated": "collecting",
}


def map_torc_state(state: str) -> OperationalState:
    return _STATE_MAP.get(state.strip().lower(), "unknown")
