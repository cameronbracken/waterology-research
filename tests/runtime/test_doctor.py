import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from waterology.cli import app
from waterology.runtime.assets import AssetCatalog

runner = CliRunner()


def test_render_check_reports_current_generated_assets() -> None:
    result = runner.invoke(app, ["render", "--check"])

    assert result.exit_code == 0
    assert "Generated agents are current" in result.stdout


def test_render_check_returns_exit_one_for_stale_generated_assets(
    monkeypatch, tmp_path: Path
) -> None:
    source = AssetCatalog.discover().root
    destination = tmp_path / "assets"
    shutil.copytree(source, destination)
    catalog = AssetCatalog.discover(destination)
    catalog.path(".codex/agents/researcher.toml").write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(AssetCatalog, "discover", classmethod(lambda cls: catalog))

    result = runner.invoke(app, ["render", "--check"])

    assert result.exit_code == 1
    assert "Generated agent files are stale" in result.stdout


def test_doctor_json_reports_runtime_commands(monkeypatch, tmp_path: Path) -> None:
    codex = tmp_path / "bin" / "codex"
    monkeypatch.setattr("shutil.which", lambda name: str(codex) if name == "codex" else None)

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    assert "\x1b" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["assets"]["status"] == "pass"
    assert payload["runtimes"]["codex"]["status"] == "pass"
    assert payload["runtimes"]["claude"]["status"] == "warn"


def test_doctor_returns_exit_one_when_requested_runtime_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = runner.invoke(app, ["doctor", "--runtime", "codex", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["runtimes"]["codex"]["status"] == "fail"
