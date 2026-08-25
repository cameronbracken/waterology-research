import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.archive import ArchiveError, verify_project_archive
from waterology.core.assessments import assess_run
from waterology.core.config import ProjectConfig, project_config_toml
from waterology.core.database import open_database
from waterology.core.execution import start_direct_run
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.repair import repair_index

runner = CliRunner()


def make_assessed_run(path: Path) -> tuple[Path, str, str]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Researcher"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    config = ProjectConfig(
        name="repair-study",
        artifact_roots=("artifacts",),
        command=("python3", "model.py"),
        outputs=("artifacts/result.txt",),
    )
    (path / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    (path / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "Add baseline"], check=True)
    experiment = create_experiment(
        path,
        hypothesis="Repair this experiment index.",
        experiment_id="exp-repair",
    )
    worktree = path / experiment.worktree
    (worktree / "model.py").write_text(
        """\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/result.txt").write_text("result\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(worktree), "add", "model.py"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "Add variant"],
        check=True,
    )
    run = start_direct_run(path, experiment.id, run_id="run-repair")
    assess_run(
        path,
        run.run_id,
        kind="answer",
        conclusion="The archived result answers the hypothesis.",
        author="cam",
        evidence=(f".waterology/runs/{run.run_id}/artifacts/artifacts/result.txt",),
    )
    return path, experiment.id, run.run_id


def test_repair_index_rebuilds_experiment_run_assessment_and_artifact(tmp_path: Path) -> None:
    root, experiment_id, run_id = make_assessed_run(tmp_path / "study")
    database_path = root / ".waterology" / "state.sqlite"
    assert verify_project_archive(root, run_id).valid is True
    database_path.unlink()

    result = repair_index(root)

    assert result.experiments == 1
    assert result.runs == 1
    assert result.assessments == 1
    assert result.artifacts == 1
    with open_database(database_path) as database:
        experiment = database.connection.execute(
            "SELECT status FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
        run = database.connection.execute(
            "SELECT operational_state FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        assessment_count = database.connection.execute(
            "SELECT COUNT(*) FROM assessments"
        ).fetchone()[0]
        integrity = database.connection.execute("PRAGMA integrity_check").fetchone()[0]
    assert experiment[0] == "frozen"
    assert run[0] == "completed"
    assert assessment_count == 1
    assert integrity == "ok"


def test_repair_index_keeps_existing_database_when_archive_is_invalid(tmp_path: Path) -> None:
    root, _, run_id = make_assessed_run(tmp_path / "study")
    database_path = root / ".waterology" / "state.sqlite"
    before = database_path.read_bytes()
    (root / ".waterology" / "runs" / run_id / "stdout.log").write_text(
        "tampered\n", encoding="utf-8"
    )

    with pytest.raises(ArchiveError, match="failed checksum verification"):
        repair_index(root)

    assert database_path.read_bytes() == before


def test_repair_index_cli_reports_import_counts(tmp_path: Path) -> None:
    root, _, _ = make_assessed_run(tmp_path / "study")
    (root / ".waterology" / "state.sqlite").unlink()

    result = runner.invoke(app, ["repair-index", "--path", str(root), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "result": {
            "artifacts": 1,
            "assessments": 1,
            "experiments": 1,
            "projects": 1,
            "runs": 1,
            "warnings": [],
        },
        "status": "pass",
    }
