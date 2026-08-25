import json
import shutil
import subprocess
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
    assert payload["torc"]["binary"]["status"] == "warn"
    assert payload["mcp"]["sdk"]["status"] in {"pass", "warn"}
    assert payload["mcp"]["server"]["status"] == "warn"


def test_doctor_reports_valid_optional_torc_profiles(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    monkeypatch.setattr("shutil.which", lambda name: f"/bin/{name}" if name == "torc" else None)

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["torc"]["binary"]["status"] == "pass"
    assert payload["torc"]["profiles"]["status"] == "pass"


def test_doctor_checks_requested_torc_version_and_api(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    monkeypatch.setattr("shutil.which", lambda name: "/bin/torc" if name == "torc" else None)

    def fake_run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        stdout = "torc 0.39.0\n" if "--version" in arguments else '{"items": []}\n'
        return subprocess.CompletedProcess(arguments, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = runner.invoke(app, ["doctor", "--torc-profile", "local", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["torc"]["connectivity"]["status"] == "pass"
    assert "0.39.0" in payload["torc"]["connectivity"]["message"]


def test_doctor_rejects_incompatible_torc_version(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    monkeypatch.setattr("shutil.which", lambda name: "/bin/torc" if name == "torc" else None)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="torc 0.35.0\n", stderr=""
        ),
    )

    result = runner.invoke(app, ["doctor", "--torc-profile", "local", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["torc"]["connectivity"]["status"] == "fail"
    assert "0.39.0 or newer" in payload["torc"]["connectivity"]["message"]


def test_doctor_returns_exit_one_when_requested_runtime_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = runner.invoke(app, ["doctor", "--runtime", "codex", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["runtimes"]["codex"]["status"] == "fail"


def test_doctor_json_reports_a_missing_canonical_agent(monkeypatch, tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    catalog.path("agent-definitions/writer.md").unlink()
    monkeypatch.setattr(AssetCatalog, "discover", classmethod(lambda cls: catalog))

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["assets"]["status"] == "fail"


def test_doctor_json_reports_a_missing_canonical_directory(monkeypatch, tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    shutil.rmtree(catalog.path("agent-definitions"))
    monkeypatch.setattr(AssetCatalog, "discover", classmethod(lambda cls: catalog))

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["assets"]["status"] == "fail"
