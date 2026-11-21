import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from waterology.cli import app
from waterology.runtime.assets import AssetCatalog

runner = CliRunner()
COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".pixi",
    ".pytest_cache",
    ".ruff_cache",
    ".superpowers",
    ".worktrees",
    "__pycache__",
    "*.pyc",
)


def copied_catalog(tmp_path: Path) -> AssetCatalog:
    source = AssetCatalog.discover().root
    destination = tmp_path / "assets"
    shutil.copytree(source, destination, ignore=COPY_IGNORE)
    return AssetCatalog.discover(destination)


def test_render_check_reports_current_generated_assets() -> None:
    result = runner.invoke(app, ["render", "--check"])

    assert result.exit_code == 0
    assert "Generated assets are current" in result.stdout


def test_render_check_returns_exit_one_for_stale_generated_assets(
    monkeypatch, tmp_path: Path
) -> None:
    catalog = copied_catalog(tmp_path)
    catalog.path(".codex/agents/researcher.toml").write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(AssetCatalog, "discover", classmethod(lambda cls: catalog))

    result = runner.invoke(app, ["render", "--check"])

    assert result.exit_code == 1
    assert "Generated files are stale" in result.stdout


def test_doctor_json_reports_runtime_commands_and_extras(monkeypatch, tmp_path: Path) -> None:
    codex = tmp_path / "bin" / "codex"
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(tmp_path / "missing-config.toml"))
    monkeypatch.setattr("shutil.which", lambda name: str(codex) if name == "codex" else None)

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    assert "\x1b" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["assets"]["status"] == "pass"
    assert payload["runtimes"]["antigravity"]["status"] == "warn"
    assert payload["runtimes"]["codex"]["status"] == "pass"
    assert payload["runtimes"]["claude"]["status"] == "warn"
    assert payload["runtimes"]["pi"]["status"] == "warn"
    assert payload["mcp"]["sdk"]["status"] in {"pass", "warn"}
    assert payload["mcp"]["server"]["status"] == "warn"
    assert payload["zotero"]["sdk"]["status"] in {"pass", "warn"}
    assert payload["user"]["config"]["status"] == "pass"


def test_doctor_fails_on_invalid_user_config(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text("[credentials]\nfile = [123]\n", encoding="utf-8")
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["user"]["config"]["status"] == "fail"


def test_doctor_detects_requested_pi_runtime(monkeypatch, tmp_path: Path) -> None:
    pi = tmp_path / "bin" / "pi"
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(tmp_path / "missing-config.toml"))
    monkeypatch.setattr("shutil.which", lambda name: str(pi) if name == "pi" else None)

    result = runner.invoke(app, ["doctor", "--runtime", "pi", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["runtimes"]["pi"]["status"] == "pass"


def test_doctor_returns_exit_one_when_requested_runtime_is_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(tmp_path / "missing-config.toml"))
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = runner.invoke(app, ["doctor", "--runtime", "codex", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["runtimes"]["codex"]["status"] == "fail"


def test_doctor_json_reports_a_missing_canonical_agent(monkeypatch, tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    catalog.path("agent-definitions/reviewer.md").unlink()
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(tmp_path / "missing-config.toml"))
    monkeypatch.setattr(AssetCatalog, "discover", classmethod(lambda cls: catalog))

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["assets"]["status"] == "fail"


def test_doctor_json_reports_a_missing_canonical_directory(monkeypatch, tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    shutil.rmtree(catalog.path("agent-definitions"))
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(tmp_path / "missing-config.toml"))
    monkeypatch.setattr(AssetCatalog, "discover", classmethod(lambda cls: catalog))

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["assets"]["status"] == "fail"
