import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import waterology.cli as cli_module
from waterology.cli import app
from waterology.core.config import ProjectConfig, project_config_toml
from waterology.core.records import ExecutorReference, ManagedRunRecord
from waterology.torc.runs import TorcRunError

runner = CliRunner()


def write_profiles(path: Path) -> None:
    path.write_text(
        """\
trusted_profiles = ["cluster"]

[profiles.local]
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"

[profiles.cluster]
mode = "slurm"
api_url = "http://control.example:8085/torc-service/v1"
torc_profile = "cluster"
slurm_account = "project-123"
dashboard_url = "http://localhost:8085/dashboard"
""",
        encoding="utf-8",
    )


def test_compute_profile_commands_use_machine_config(tmp_path: Path, monkeypatch: object) -> None:
    path = tmp_path / "config.toml"
    write_profiles(path)
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(path))  # type: ignore[attr-defined]

    listed = runner.invoke(app, ["compute", "profile", "list", "--json"])
    shown = runner.invoke(app, ["compute", "profile", "show", "cluster", "--json"])
    inspected = runner.invoke(app, ["compute", "inspect", "cluster", "--dashboard", "--json"])

    assert listed.exit_code == shown.exit_code == inspected.exit_code == 0
    assert [item["name"] for item in json.loads(listed.stdout)["profiles"]] == [
        "cluster",
        "local",
    ]
    assert json.loads(shown.stdout)["profile"]["trusted"] is True
    assert json.loads(inspected.stdout)["target"] == "http://localhost:8085/dashboard"


def test_compute_inspect_tui_uses_current_torc_client_endpoint(
    tmp_path: Path, monkeypatch: object
) -> None:
    path = tmp_path / "config.toml"
    write_profiles(path)
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(path))  # type: ignore[attr-defined]

    result = runner.invoke(app, ["compute", "inspect", "local", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["target"] == (
        "torc --url http://localhost:8080/torc-service/v1 tui"
    )


def test_profile_trust_requires_explicit_yes(tmp_path: Path, monkeypatch: object) -> None:
    path = tmp_path / "config.toml"
    write_profiles(path)
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(path))  # type: ignore[attr-defined]

    result = runner.invoke(app, ["compute", "profile", "trust", "local", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "invalid_input"


def test_run_start_uses_committed_default_compute_profile(
    tmp_path: Path, monkeypatch: object
) -> None:
    config = ProjectConfig(
        name="study",
        command=("python", "model.py"),
        default_compute_profile="cluster",
    )
    (tmp_path / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    captured: dict[str, str] = {}

    monkeypatch.setattr(  # type: ignore[attr-defined]
        cli_module,
        "load_worktree",
        lambda path, experiment_id: SimpleNamespace(path=str(tmp_path)),
    )

    def fake_start(*args: object, profile_name: str, **kwargs: object) -> ManagedRunRecord:
        captured["profile"] = profile_name
        return ManagedRunRecord(
            run_id="run-one",
            experiment_id="exp-one",
            commit_sha="a" * 40,
            operational_state="running",
            started_at="2026-08-25T00:00:00Z",
            reference=ExecutorReference(
                compute_profile="cluster",
                api_url="http://localhost:8080",
                execution_mode="slurm",
                workflow_id="42",
                torc_version="torc 0.39.0",
            ),
        )

    monkeypatch.setattr(cli_module, "start_torc_run", fake_start)  # type: ignore[attr-defined]

    result = runner.invoke(
        app,
        ["run", "start", "exp-one", "--path", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    assert captured["profile"] == "cluster"


def test_run_start_cli_does_not_print_redacted_secret(monkeypatch: object) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise TorcRunError("TORC launch failed: token=[REDACTED]")

    monkeypatch.setattr(cli_module, "start_torc_run", fail)  # type: ignore[attr-defined]

    result = runner.invoke(
        app,
        ["run", "start", "exp-one", "--profile", "cluster", "--json"],
    )

    assert result.exit_code == 1
    assert "secret-value" not in result.stdout
    assert json.loads(result.stdout)["error"]["code"] == "torc_run_failed"
