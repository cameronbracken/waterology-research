import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

import waterology.cli as cli_module
from waterology.cli import app
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project

runner = CliRunner()


def make_project(path: Path) -> tuple[Path, str]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    (path / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(path), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "base"], check=True)
    experiment = create_experiment(
        path,
        hypothesis="The CLI can supervise this experiment.",
        experiment_id="exp-cli-agent",
    )
    return path, experiment.id


def test_agent_start_and_list_emit_stable_json(tmp_path: Path, monkeypatch: object) -> None:
    root, experiment_id = make_project(tmp_path / "study")
    monkeypatch.setattr(  # type: ignore[attr-defined]
        cli_module,
        "launch_session",
        lambda path, session_id, prompt: cli_module.load_session(path, session_id),
    )

    started = runner.invoke(
        app,
        [
            "agent",
            "start",
            experiment_id,
            "Inspect the baseline.",
            "--runtime",
            "codex",
            "--role",
            "researcher",
            "--path",
            str(root),
            "--json",
        ],
    )
    listed = runner.invoke(app, ["agent", "list", "--path", str(root), "--json"])

    assert started.exit_code == 0
    payload = json.loads(started.stdout)
    assert payload["session"]["experiment_id"] == experiment_id
    assert payload["session"]["runtime"] == "codex"
    assert listed.exit_code == 0
    assert json.loads(listed.stdout)["sessions"][0]["id"] == payload["session"]["id"]


def test_agent_start_reads_task_file(tmp_path: Path, monkeypatch: object) -> None:
    root, experiment_id = make_project(tmp_path / "study")
    task = tmp_path / "task.md"
    task.write_text("Compare two configurations.\n", encoding="utf-8")
    captured: dict[str, str] = {}

    def fake_launch(path: Path, session_id: str, *, prompt: str):
        captured["prompt"] = prompt
        return cli_module.load_session(path, session_id)

    monkeypatch.setattr(cli_module, "launch_session", fake_launch)  # type: ignore[attr-defined]

    result = runner.invoke(
        app,
        [
            "agent",
            "start",
            experiment_id,
            "--task-file",
            str(task),
            "--path",
            str(root),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured["prompt"] == "Compare two configurations.\n"


def test_agent_status_and_logs_use_durable_session_files(
    tmp_path: Path, monkeypatch: object
) -> None:
    root, experiment_id = make_project(tmp_path / "study")
    monkeypatch.setattr(  # type: ignore[attr-defined]
        cli_module,
        "launch_session",
        lambda path, session_id, prompt: cli_module.load_session(path, session_id),
    )
    started = runner.invoke(
        app,
        ["agent", "start", experiment_id, "Inspect.", "--path", str(root), "--json"],
    )
    session_id = json.loads(started.stdout)["session"]["id"]

    status = runner.invoke(app, ["agent", "status", session_id, "--path", str(root), "--json"])
    logs = runner.invoke(app, ["agent", "logs", session_id, "--path", str(root), "--json"])

    assert status.exit_code == 0
    assert json.loads(status.stdout)["session"]["state"] == "created"
    assert logs.exit_code == 0
    assert json.loads(logs.stdout)["attempts"] == []


def test_agent_start_requires_exactly_one_task_source(tmp_path: Path) -> None:
    root, experiment_id = make_project(tmp_path / "study")
    task = tmp_path / "task.md"
    task.write_text("Task file.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "agent",
            "start",
            experiment_id,
            "Inline task.",
            "--task-file",
            str(task),
            "--path",
            str(root),
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "invalid_input"
