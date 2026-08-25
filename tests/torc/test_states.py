import pytest

from waterology.torc.states import map_torc_state


@pytest.mark.parametrize(
    ("torc_state", "waterology_state"),
    [
        ("pending", "queued"),
        ("ready", "preparing"),
        ("running", "running"),
        ("completed", "collecting"),
        ("failed", "collecting"),
        ("canceled", "collecting"),
    ],
)
def test_map_torc_state(torc_state: str, waterology_state: str) -> None:
    assert map_torc_state(torc_state) == waterology_state


def test_map_torc_state_preserves_unknown_future_state() -> None:
    assert map_torc_state("future-state") == "unknown"
