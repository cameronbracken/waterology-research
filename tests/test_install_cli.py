import json
from pathlib import Path

from typer.testing import CliRunner

from waterology.cli import app
from waterology.runtime.assets import AssetCatalog

runner = CliRunner()


def test_install_dry_run_json_makes_no_files(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "install",
            "opencode",
            "--target",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert "\x1b" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["runtime"] == "opencode"
    assert payload["scope"] == "project"
    assert payload["dry_run"] is True
    assert not (tmp_path / ".opencode").exists()


def test_install_rejects_target_with_user_scope(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "codex", "--scope", "user", "--target", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "--target" in result.output
    assert not any(tmp_path.iterdir())


def test_install_conflict_returns_exit_one_without_writing_other_assets(tmp_path: Path) -> None:
    collision = tmp_path / ".opencode" / "agents" / "researcher.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("user-owned\n", encoding="utf-8")

    result = runner.invoke(app, ["install", "opencode", "--target", str(tmp_path)])

    assert result.exit_code == 1
    assert "destination is not owned" in result.stdout
    assert not (tmp_path / ".opencode" / "skills").exists()


def test_install_link_mode_creates_links_to_source_assets(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "opencode", "--target", str(tmp_path), "--mode", "link"],
    )

    installed = tmp_path / ".opencode" / "skills" / "project-conventions"
    assert result.exit_code == 0
    assert installed.is_symlink()
    assert installed.resolve() == AssetCatalog.discover().path("skills/project-conventions")


def test_install_force_replaces_an_owned_modified_asset(tmp_path: Path) -> None:
    initial = runner.invoke(app, ["install", "opencode", "--target", str(tmp_path)])
    destination = tmp_path / ".opencode" / "agents" / "researcher.md"
    destination.write_text("locally modified\n", encoding="utf-8")

    result = runner.invoke(app, ["install", "opencode", "--target", str(tmp_path), "--force"])

    assert initial.exit_code == 0
    assert result.exit_code == 0
    assert (
        destination.read_bytes()
        == AssetCatalog.discover().path(".opencode/agents/researcher.md").read_bytes()
    )


def test_install_all_preflights_every_runtime_before_writes(tmp_path: Path) -> None:
    collision = tmp_path / ".codex" / "agents" / "researcher.toml"
    collision.parent.mkdir(parents=True)
    collision.write_text("user-owned\n", encoding="utf-8")

    result = runner.invoke(app, ["install", "all", "--target", str(tmp_path)])

    assert result.exit_code == 1
    assert "destination is not owned" in result.stdout
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".agents").exists()
