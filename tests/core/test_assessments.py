import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.assessments import AssessmentEvidenceError, assess_run
from waterology.core.config import ProjectConfig, project_config_toml
from waterology.core.execution import start_direct_run
from waterology.core.experiments import create_experiment, load_experiment
from waterology.core.project import initialize_project

runner = CliRunner()


def make_experiment(path: Path) -> tuple[Path, str, Path]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Researcher"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    config = ProjectConfig(
        name="assessment-study",
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
        hypothesis="Assess a committed result.",
        experiment_id="exp-assess",
    )
    return path, experiment.id, path / experiment.worktree


def commit_working_model(worktree: Path, value: str) -> str:
    (worktree / "model.py").write_text(
        f"""\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/result.txt").write_text("{value}\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(worktree), "add", "model.py"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", f"Variant {value}"],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_answer_assessment_freezes_experiment_and_supplies_child_commit(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    answer_commit = commit_working_model(worktree, "answer")
    run = start_direct_run(root, experiment_id, run_id="run-answer")
    assert load_experiment(root, experiment_id).status == "provisional"

    assessment = assess_run(
        root,
        run.run_id,
        kind="answer",
        conclusion="The variant answers the hypothesis.",
        author="cam",
        evidence=(f".waterology/runs/{run.run_id}/metrics.json",),
    )
    frozen = load_experiment(root, experiment_id)
    child = create_experiment(
        root,
        hypothesis="Follow the answered result.",
        parent_experiment_id=experiment_id,
        experiment_id="exp-child",
    )

    assert assessment.commit_sha == answer_commit
    assert frozen.status == "frozen"
    assert frozen.frozen_at == assessment.created_at
    assert child.base_commit == answer_commit
    assert child.parent_experiment_id == experiment_id


def test_two_consecutive_no_answer_assessments_require_a_decision(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_working_model(worktree, "first")
    first = start_direct_run(root, experiment_id, run_id="run-first")
    assess_run(
        root,
        first.run_id,
        kind="no_answer",
        conclusion="The first result is inconclusive.",
        author="cam",
    )
    (worktree / "artifacts" / "result.txt").unlink()
    (worktree / "artifacts").rmdir()
    commit_working_model(worktree, "second")
    second = start_direct_run(root, experiment_id, run_id="run-second")
    assess_run(
        root,
        second.run_id,
        kind="no_answer",
        conclusion="The second result is also inconclusive.",
        author="cam",
    )

    experiment = load_experiment(root, experiment_id)
    assert experiment.status == "provisional"
    assert experiment.decision_required is True


def test_assessment_rejects_evidence_outside_allowed_roots(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_working_model(worktree, "result")
    run = start_direct_run(root, experiment_id, run_id="run-evidence")
    outside = tmp_path / "outside.txt"
    outside.write_text("not project evidence\n", encoding="utf-8")

    with pytest.raises(AssessmentEvidenceError, match="relative project path"):
        assess_run(
            root,
            run.run_id,
            kind="answer",
            conclusion="Do not accept external evidence.",
            author="cam",
            evidence=(str(outside),),
        )


def test_run_assess_cli_writes_structured_assessment(tmp_path: Path) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    commit_working_model(worktree, "cli")
    run = start_direct_run(root, experiment_id, run_id="run-cli-assess")
    evidence = f".waterology/runs/{run.run_id}/metrics.json"

    result = runner.invoke(
        app,
        [
            "run",
            "assess",
            run.run_id,
            "answer",
            "The CLI assessment answers the hypothesis.",
            "--author",
            "cam",
            "--evidence",
            evidence,
            "--path",
            str(root),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["assessment"]["kind"] == "answer"
    assert payload["assessment"]["evidence"] == [evidence]
    assert payload["experiment"]["status"] == "frozen"
