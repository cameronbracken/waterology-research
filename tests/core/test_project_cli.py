import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from waterology.cli import app

runner = CliRunner()


def make_git_repository(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    return path


def test_init_json_initializes_the_git_root(tmp_path: Path) -> None:
    root = make_git_repository(tmp_path / "river-study")
    nested = root / "analysis"
    nested.mkdir()

    result = runner.invoke(
        app,
        ["init", "--path", str(nested), "--name", "river-model", "--json"],
    )

    assert result.exit_code == 0
    assert "\x1b" not in result.stdout
    assert json.loads(result.stdout) == {
        "created_config": True,
        "project": {"name": "river-model", "root": str(root.resolve())},
        "status": "pass",
        "updated_gitignore": True,
    }


def test_status_json_reports_initialized_state(tmp_path: Path) -> None:
    root = make_git_repository(tmp_path / "study")
    initialized = runner.invoke(app, ["init", "--path", str(root), "--json"])

    result = runner.invoke(app, ["status", "--path", str(root), "--json"])

    assert initialized.exit_code == 0
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "project": {
            "name": "study",
            "root": str(root.resolve()),
            "schema_version": 1,
        },
        "state": {
            "assessments": 0,
            "database_exists": False,
            "experiments": 0,
            "runs": 0,
        },
        "status": "pass",
    }


def test_status_json_reports_structured_missing_project_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["status", "--path", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["error"]["code"] == "project_not_found"
    assert "waterology.toml" in payload["error"]["message"]


def test_status_json_reports_malformed_configuration_as_one_error_object(
    tmp_path: Path,
) -> None:
    root = make_git_repository(tmp_path / "study")
    initialized = runner.invoke(app, ["init", "--path", str(root), "--json"])
    assert initialized.exit_code == 0
    (root / "waterology.toml").write_text("not valid = [\n", encoding="utf-8")

    result = runner.invoke(app, ["status", "--path", str(root), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["error"]["code"] == "invalid_input"
    assert "\x1b" not in result.stdout
