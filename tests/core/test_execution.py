import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.config import ProjectConfig, project_config_toml
from waterology.core.database import open_database
from waterology.core.execution import RunPreparationError, start_direct_run
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project

runner = CliRunner()


def make_experiment(path: Path) -> tuple[Path, str, Path]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Researcher"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    config = ProjectConfig(
        name="execution-study",
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
        hypothesis="The variant writes a useful result.",
        experiment_id="exp-direct",
    )
    worktree = path / experiment.worktree
    return path, experiment.id, worktree


def commit_variant(worktree: Path, source: str) -> str:
    (worktree / "model.py").write_text(source, encoding="utf-8")
    subprocess.run(["git", "-C", str(worktree), "add", "model.py"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "Test variant"],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_direct_run_requires_and_archives_a_clean_committed_variant(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit = commit_variant(
        worktree,
        """\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/result.txt").write_text("42\\n", encoding="utf-8")
print("completed variant")
""",
    )

    run = start_direct_run(root, experiment_id, run_id="run-direct")

    assert run.run_id == "run-direct"
    assert run.commit_sha == commit
    assert run.terminal_state == "completed"
    archive = root / ".waterology" / "runs" / run.run_id
    assert (archive / "stdout.log").read_text(encoding="utf-8") == "completed variant\n"
    assert (archive / "artifacts" / "artifacts" / "result.txt").read_text(
        encoding="utf-8"
    ) == "42\n"
    with open_database(root / ".waterology" / "state.sqlite") as database:
        indexed = database.connection.execute(
            "SELECT operational_state, commit_sha, archive_path FROM runs WHERE id = ?",
            (run.run_id,),
        ).fetchone()
        transitions = [
            event.payload["to"]
            for event in database.list_events()
            if event.kind == "run.transition" and event.phase == "observation"
        ]
    assert tuple(indexed) == ("completed", commit, f".waterology/runs/{run.run_id}")
    assert transitions == ["preparing", "running", "collecting", "completed"]


def test_direct_run_rejects_unchanged_baseline(tmp_path: Path) -> None:
    root, experiment_id, _ = make_experiment(tmp_path / "study")

    with pytest.raises(RunPreparationError, match="committed variant"):
        start_direct_run(root, experiment_id, run_id="run-baseline")


def test_direct_run_rejects_dirty_worktree(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_variant(worktree, "print('committed variant')\n")
    (worktree / "model.py").write_text("print('dirty')\n", encoding="utf-8")

    with pytest.raises(RunPreparationError, match="must be clean"):
        start_direct_run(root, experiment_id, run_id="run-dirty")


def test_failed_direct_run_preserves_logs_and_missing_artifacts(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_variant(
        worktree,
        """\
import sys

print("model failed", file=sys.stderr)
raise SystemExit(7)
""",
    )

    run = start_direct_run(root, experiment_id, run_id="run-failed")

    assert run.terminal_state == "failed"
    assert run.exit_code == 7
    assert run.missing_artifacts == ("artifacts/result.txt",)
    archive = root / ".waterology" / "runs" / run.run_id
    assert (archive / "stderr.log").read_text(encoding="utf-8") == "model failed\n"


def test_run_cli_starts_lists_and_reads_direct_run(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_variant(
        worktree,
        """\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/result.txt").write_text("saved\\n", encoding="utf-8")
print("cli run")
""",
    )

    started = runner.invoke(
        app,
        [
            "run",
            "start",
            experiment_id,
            "--id",
            "run-cli-direct",
            "--path",
            str(root),
            "--json",
        ],
    )
    listed = runner.invoke(app, ["run", "list", "--path", str(root), "--json"])
    status = runner.invoke(app, ["run", "status", "run-cli-direct", "--path", str(root), "--json"])
    logs = runner.invoke(app, ["run", "logs", "run-cli-direct", "--path", str(root), "--json"])

    assert started.exit_code == listed.exit_code == status.exit_code == logs.exit_code == 0
    assert json.loads(started.stdout)["run"]["terminal_state"] == "completed"
    assert [item["run_id"] for item in json.loads(listed.stdout)["runs"]] == ["run-cli-direct"]
    assert json.loads(status.stdout)["run"]["exit_code"] == 0
    assert json.loads(logs.stdout)["logs"] == {"stderr": "", "stdout": "cli run\n"}
