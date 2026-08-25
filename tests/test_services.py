import json
import subprocess
from pathlib import Path

from waterology import services
from waterology.core.database import open_database
from waterology.core.experiments import create_experiment
from waterology.core.profiles import MachineConfig
from waterology.core.project import initialize_project
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


def test_dashboard_snapshot_reconciles_active_torc_runs(
    monkeypatch: object, tmp_path: Path
) -> None:
    root = tmp_path / "study"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.org"], check=True
    )
    initialize_project(root)
    (root / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(root), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "commit", "--quiet", "-m", "base"], check=True)
    experiment = create_experiment(
        root,
        hypothesis="Dashboard refresh reconciles compute state.",
        experiment_id="exp-dashboard",
    )
    with open_database(root / ".waterology/state.sqlite") as database, database.connection:
        database.connection.execute(
            """
            INSERT INTO runs (
                id, experiment_id, commit_sha, operational_state, executor,
                compute_profile, started_at
            ) VALUES (?, ?, ?, 'running', 'torc', 'local', ?)
            """,
            ("run-dashboard", experiment.id, experiment.base_commit, experiment.created_at),
        )
    observed: list[str] = []

    def complete(_path: Path, run_id: str) -> dict[str, object]:
        observed.append(run_id)
        return {
            "run_id": run_id,
            "terminal_state": "completed",
            "finished_at": "2026-08-25T12:00:00Z",
        }

    monkeypatch.setattr(services, "run_status", complete)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        services, "load_machine_config", lambda _path: MachineConfig()
    )

    snapshot = services.dashboard_snapshot(root)

    assert observed == ["run-dashboard"]
    assert snapshot["managed_runs"][0]["operational_state"] == "completed"  # type: ignore[index]
    assert snapshot["counts"]["active_runs"] == 0  # type: ignore[index]
    json.dumps(snapshot)


def test_dashboard_snapshot_marks_dead_direct_process_unknown(
    monkeypatch: object, tmp_path: Path
) -> None:
    root = tmp_path / "study"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.org"], check=True
    )
    initialize_project(root)
    (root / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(root), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "commit", "--quiet", "-m", "base"], check=True)
    experiment = create_experiment(
        root,
        hypothesis="Dashboard detects an interrupted direct run.",
        experiment_id="exp-direct-dashboard",
    )
    with open_database(root / ".waterology/state.sqlite") as database, database.connection:
        database.connection.execute(
            """
            INSERT INTO runs (
                id, experiment_id, commit_sha, operational_state, executor,
                process_id, started_at
            ) VALUES (?, ?, ?, 'running', 'direct', 987654321, ?)
            """,
            ("run-direct-dashboard", experiment.id, experiment.base_commit, experiment.created_at),
        )
    staging = root / ".waterology/staging/run-direct-dashboard"
    staging.mkdir()
    (staging / "execution.json").write_text(
        json.dumps({"state": "running", "process_id": 987654321}), encoding="utf-8"
    )
    monkeypatch.setattr(services, "_process_alive", lambda _pid: False)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        services, "load_machine_config", lambda _path: MachineConfig()
    )

    snapshot = services.dashboard_snapshot(root)

    run = snapshot["managed_runs"][0]  # type: ignore[index]
    assert run["operational_state"] == "unknown"
    assert "no longer running" in run["inspection_error"]

    (staging / "execution.json").write_text(
        json.dumps({"state": "completed", "process_id": 987654321}), encoding="utf-8"
    )
    collecting = services.dashboard_snapshot(root)["managed_runs"][0]  # type: ignore[index]
    assert collecting["operational_state"] == "collecting"
    assert "without a sealed archive" in collecting["inspection_error"]
