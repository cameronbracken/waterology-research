import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core import archive as archive_module
from waterology.core.archive import ArchiveArtifactMissingError, build_run_archive, load_archive
from waterology.core.assessments import assess_run
from waterology.core.config import (
    MetricExtractor,
    ProjectConfig,
    load_project_config,
    project_config_toml,
)
from waterology.core.database import open_database
from waterology.core.execution import (
    MetricExtractionError,
    RunExecutionError,
    RunPreparationError,
    start_direct_run,
)
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.repair import repair_index

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
    assert run.process_id is not None
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


def test_launch_failure_seals_durable_failed_run(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    config = load_project_config(worktree / "waterology.toml").model_copy(
        update={"command": ("missing-waterology-command",)}
    )
    (worktree / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    subprocess.run(["git", "-C", str(worktree), "add", "waterology.toml"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "Set missing command"],
        check=True,
    )

    with pytest.raises(RunExecutionError, match="Unable to start"):
        start_direct_run(root, experiment_id, run_id="run-launch-failed")

    archive = root / ".waterology" / "runs" / "run-launch-failed"
    manifest = load_archive(root, "run-launch-failed")
    assert manifest.terminal_state == "failed"
    assert manifest.process_id is None
    assert (archive / "stdout.log").is_file()
    assert (archive / "stderr.log").is_file()
    assert not (root / ".waterology" / "staging" / "run-launch-failed").exists()
    with open_database(root / ".waterology" / "state.sqlite") as database:
        state = database.connection.execute(
            "SELECT operational_state FROM runs WHERE id = 'run-launch-failed'"
        ).fetchone()[0]
        launch_events = [
            event
            for event in database.list_events()
            if event.kind == "run.launch" and event.entity_id == "run-launch-failed"
        ]
    assert state == "failed"
    assert [event.phase for event in launch_events] == ["intent", "observation"]

    (root / ".waterology" / "state.sqlite").unlink()
    repair_index(root)
    with open_database(root / ".waterology" / "state.sqlite") as database:
        repaired_state = database.connection.execute(
            "SELECT operational_state FROM runs WHERE id = 'run-launch-failed'"
        ).fetchone()[0]
    assert repaired_state == "failed"


def test_interrupted_collection_can_seal_from_staging_without_rerunning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_variant(
        worktree,
        """\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/result.txt").write_text("preserved\\n", encoding="utf-8")
print("ran exactly once")
        """,
    )

    def interrupt_collection(*_: object) -> None:
        raise OSError("injected collection interruption")

    with monkeypatch.context() as patcher:
        patcher.setattr(
            archive_module,
            "_write_source_archive",
            interrupt_collection,
        )
        with pytest.raises(OSError, match="injected collection interruption"):
            start_direct_run(root, experiment_id, run_id="run-interrupted")

    staging = root / ".waterology" / "staging" / "run-interrupted"
    metadata = json.loads((staging / "execution.json").read_text(encoding="utf-8"))
    assert metadata["state"] == "completed"
    assert metadata["process_id"] is not None
    assert (staging / "stdout.log").read_text(encoding="utf-8") == "ran exactly once\n"
    with open_database(root / ".waterology" / "state.sqlite") as database:
        state = database.connection.execute(
            "SELECT operational_state FROM runs WHERE id = 'run-interrupted'"
        ).fetchone()[0]
    assert state == "collecting"

    build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-interrupted",
        commit_sha=metadata["commit_sha"],
        command=tuple(metadata["command"]),
        started_at=metadata["started_at"],
        finished_at=metadata["finished_at"],
        terminal_state=metadata["state"],
        exit_code=metadata["exit_code"],
        stdout=(staging / "stdout.log").read_text(encoding="utf-8"),
        stderr=(staging / "stderr.log").read_text(encoding="utf-8"),
        metrics={},
        process_id=metadata["process_id"],
    )

    recovered = load_archive(root, "run-interrupted")
    assert recovered.process_id == metadata["process_id"]
    assert (root / ".waterology" / "runs" / "run-interrupted" / "execution.json").exists() is False


def test_missing_metric_remains_collecting_with_durable_staging(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    config = load_project_config(worktree / "waterology.toml").model_copy(
        update={
            "metrics": (MetricExtractor(name="rmse", path="artifacts/missing.json", field="rmse"),)
        }
    )
    (worktree / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    commit_variant(
        worktree,
        """\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/result.txt").write_text("result\\n", encoding="utf-8")
""",
    )
    subprocess.run(["git", "-C", str(worktree), "add", "waterology.toml"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "Add metric contract"],
        check=True,
    )

    with pytest.raises(MetricExtractionError, match="Metric source does not exist"):
        start_direct_run(root, experiment_id, run_id="run-missing-metric")

    staging = root / ".waterology" / "staging" / "run-missing-metric"
    metadata = json.loads((staging / "execution.json").read_text(encoding="utf-8"))
    assert metadata["state"] == "completed"
    with open_database(root / ".waterology" / "state.sqlite") as database:
        state = database.connection.execute(
            "SELECT operational_state FROM runs WHERE id = 'run-missing-metric'"
        ).fetchone()[0]
    assert state == "collecting"


def test_missing_declared_output_remains_collecting_with_durable_staging(
    tmp_path: Path,
) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_variant(worktree, "print('no artifact')\n")

    with pytest.raises(ArchiveArtifactMissingError, match="Declared artifacts are missing"):
        start_direct_run(root, experiment_id, run_id="run-missing-output")

    staging = root / ".waterology" / "staging" / "run-missing-output"
    metadata = json.loads((staging / "execution.json").read_text(encoding="utf-8"))
    assert metadata["state"] == "completed"
    with open_database(root / ".waterology" / "state.sqlite") as database:
        state = database.connection.execute(
            "SELECT operational_state FROM runs WHERE id = 'run-missing-output'"
        ).fetchone()[0]
    assert state == "collecting"


def test_direct_run_uses_committed_worktree_config_and_extracts_metrics(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    worktree_config = load_project_config(worktree / "waterology.toml").model_copy(
        update={
            "outputs": ("artifacts/metrics.json",),
            "metrics": (
                MetricExtractor(
                    name="rmse",
                    path="artifacts/metrics.json",
                    field="scores.rmse",
                ),
            ),
        }
    )
    (worktree / "waterology.toml").write_text(
        project_config_toml(worktree_config), encoding="utf-8"
    )
    (worktree / "model.py").write_text(
        """\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/metrics.json").write_text(
    '{"scores": {"rmse": 1.5}}\\n', encoding="utf-8"
)
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(worktree), "add", "model.py", "waterology.toml"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "Add metrics"],
        check=True,
    )
    main_config = load_project_config(root / "waterology.toml").model_copy(
        update={"command": ("command-that-must-not-run",)}
    )
    (root / "waterology.toml").write_text(project_config_toml(main_config), encoding="utf-8")

    run = start_direct_run(worktree, experiment_id, run_id="run-worktree-config")

    archive = root / ".waterology" / "runs" / run.run_id
    assert json.loads((archive / "metrics.json").read_text(encoding="utf-8")) == {"rmse": 1.5}
    assert run.declared_artifacts == ("artifacts/metrics.json",)


def test_direct_run_rejects_frozen_experiment(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_variant(
        worktree,
        """\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/result.txt").write_text("answer\\n", encoding="utf-8")
""",
    )
    run = start_direct_run(root, experiment_id, run_id="run-freeze")
    assess_run(
        root,
        run.run_id,
        kind="answer",
        conclusion="This run answers the experiment.",
        author="cam",
        evidence=(f".waterology/runs/{run.run_id}/metrics.json",),
    )

    with pytest.raises(RunPreparationError, match="is frozen"):
        start_direct_run(root, experiment_id, run_id="run-after-freeze")


def test_direct_run_rejects_detached_or_wrong_branch(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_variant(worktree, "print('variant')\n")
    subprocess.run(["git", "-C", str(worktree), "checkout", "--detach", "--quiet"], check=True)

    with pytest.raises(RunPreparationError, match="recorded branch"):
        start_direct_run(root, experiment_id, run_id="run-detached")


def test_direct_run_rejects_commit_outside_experiment_ancestry(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_variant(worktree, "print('variant')\n")
    tree = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD^{tree}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    unrelated = subprocess.run(
        ["git", "-C", str(worktree), "commit-tree", tree, "-m", "Unrelated root"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "-C", str(worktree), "checkout", "--detach", "--quiet"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "branch", "--force", f"waterology/{experiment_id}", unrelated],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(worktree), "checkout", "--quiet", f"waterology/{experiment_id}"],
        check=True,
    )

    with pytest.raises(RunPreparationError, match="not descended"):
        start_direct_run(root, experiment_id, run_id="run-unrelated")


def test_direct_run_rejects_second_active_run_for_worktree(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit = commit_variant(worktree, "print('variant')\n")
    with open_database(root / ".waterology" / "state.sqlite") as database, database.connection:
        database.connection.execute(
            """
            INSERT INTO runs (
                id, experiment_id, commit_sha, operational_state, executor, started_at
            ) VALUES ('run-active', ?, ?, 'running', 'direct', '2026-08-25T00:00:00Z')
            """,
            (experiment_id, commit),
        )

    with pytest.raises(RunPreparationError, match="active run: run-active"):
        start_direct_run(root, experiment_id, run_id="run-concurrent")


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
