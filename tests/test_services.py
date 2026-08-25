from pathlib import Path

from waterology import services
from waterology.core.records import ExperimentRecord


def test_service_project_status_is_json_serializable(monkeypatch: object, tmp_path: Path) -> None:
    project = type(
        "Project", (), {"config": type("Config", (), {"name": "study"})(), "root": tmp_path}
    )()
    status = type(
        "Status",
        (),
        {
            "project": project,
            "database_exists": True,
            "experiments": 2,
            "runs": 3,
            "assessments": 1,
        },
    )()
    monkeypatch.setattr(services, "inspect_project", lambda path: status)  # type: ignore[attr-defined]

    payload = services.project_status(tmp_path)

    assert payload == {
        "assessments": 1,
        "database_exists": True,
        "experiments": 2,
        "name": "study",
        "root": str(tmp_path),
        "runs": 3,
    }


def test_service_experiment_payload_uses_core_model(monkeypatch: object, tmp_path: Path) -> None:
    record = ExperimentRecord(
        id="exp-one",
        project_id="study",
        hypothesis="Test the service boundary.",
        base_commit="a" * 40,
        branch="waterology/exp-one",
        worktree=".waterology/worktrees/exp-one",
        created_at="2026-08-25T00:00:00Z",
    )
    monkeypatch.setattr(services, "load_experiment", lambda path, identifier: record)  # type: ignore[attr-defined]

    assert services.experiment_status(tmp_path, "exp-one") == record.model_dump(mode="json")
