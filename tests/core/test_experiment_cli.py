import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.project import initialize_project

runner = CliRunner()


def make_committed_project(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Researcher"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    (path / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(path), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "Add baseline"], check=True)
    return path


def test_experiment_cli_create_list_show_and_note_json(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    created = runner.invoke(
        app,
        [
            "experiment",
            "create",
            "A revised parameter improves fit.",
            "--id",
            "exp-fit",
            "--owner",
            "cam",
            "--path",
            str(root),
            "--json",
        ],
    )
    noted = runner.invoke(
        app,
        [
            "experiment",
            "note",
            "exp-fit",
            "Try the dry years first.",
            "--author",
            "cam",
            "--path",
            str(root),
            "--json",
        ],
    )
    listed = runner.invoke(app, ["experiment", "list", "--path", str(root), "--json"])
    shown = runner.invoke(app, ["experiment", "show", "exp-fit", "--path", str(root), "--json"])

    assert created.exit_code == noted.exit_code == listed.exit_code == shown.exit_code == 0
    created_payload = json.loads(created.stdout)
    assert created_payload["experiment"]["id"] == "exp-fit"
    assert created_payload["experiment"]["owner"] == "cam"
    assert json.loads(noted.stdout)["note"]["text"] == "Try the dry years first."
    assert [item["id"] for item in json.loads(listed.stdout)["experiments"]] == ["exp-fit"]
    shown_payload = json.loads(shown.stdout)
    assert shown_payload["experiment"]["hypothesis"] == "A revised parameter improves fit."
    assert [item["author"] for item in shown_payload["notes"]] == ["cam"]


def test_worktree_cli_lists_and_resolves_experiment_path(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    runner.invoke(
        app,
        [
            "experiment",
            "create",
            "Create a worktree.",
            "--id",
            "exp-tree",
            "--path",
            str(root),
            "--json",
        ],
    )

    listed = runner.invoke(app, ["worktree", "list", "--path", str(root), "--json"])
    opened = runner.invoke(app, ["worktree", "open", "exp-tree", "--path", str(root), "--json"])

    assert listed.exit_code == opened.exit_code == 0
    worktrees = json.loads(listed.stdout)["worktrees"]
    assert worktrees[0]["branch"] == "waterology/exp-tree"
    opened_path = Path(json.loads(opened.stdout)["worktree"]["path"])
    assert opened_path == root / ".waterology" / "worktrees" / "exp-tree"
    assert opened_path.is_dir()


def test_experiment_cli_returns_structured_conflict(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    arguments = [
        "experiment",
        "create",
        "First.",
        "--id",
        "exp-same",
        "--path",
        str(root),
        "--json",
    ]
    first = runner.invoke(app, arguments)
    second = runner.invoke(app, arguments)

    assert first.exit_code == 0
    assert second.exit_code == 1
    payload = json.loads(second.stdout)
    assert payload["error"]["code"] == "experiment_conflict"
    assert payload["status"] == "fail"
