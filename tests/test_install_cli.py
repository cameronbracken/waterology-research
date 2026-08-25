import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from waterology import cli
from waterology.cli import app
from waterology.runtime.assets import AssetCatalog

runner = CliRunner()


def test_install_dry_run_json_makes_no_files(monkeypatch, tmp_path: Path) -> None:
    def fail_apply(*args: object, **kwargs: object) -> None:
        raise AssertionError("dry run called apply_install_plan")

    monkeypatch.setattr(cli, "apply_install_plan", fail_apply)
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
    assert payload["mode"] == "copy"
    assert list(tmp_path.iterdir()) == []


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


def test_install_unowned_destination_json_reports_a_structured_conflict(tmp_path: Path) -> None:
    collision = tmp_path / ".opencode" / "agents" / "researcher.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("user-owned\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["install", "opencode", "--target", str(tmp_path), "--json"],
    )

    assert result.exit_code == 1
    assert "\x1b" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["error"]["type"] == "InstallConflictError"
    assert payload["conflicts"] == [
        {"destination": str(collision), "reason": "destination is not owned"}
    ]
    assert not (tmp_path / ".opencode" / "skills").exists()


def test_install_existing_lock_json_preserves_lock_without_writing_assets(tmp_path: Path) -> None:
    lock = tmp_path / ".waterology-install.lock"
    lock.write_text("active\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["install", "opencode", "--target", str(tmp_path), "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["error"]["type"] == "InstallConflictError"
    assert payload["conflicts"] == [
        {
            "destination": str(lock),
            "reason": "another Waterology install is in progress",
        }
    ]
    assert lock.read_text(encoding="utf-8") == "active\n"
    assert list(tmp_path.iterdir()) == [lock]


def test_install_non_object_manifest_assets_json_reports_type_error(tmp_path: Path) -> None:
    manifest = tmp_path / ".opencode" / ".waterology-install.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "waterology_version": "0.2.0",
                "runtime": "opencode",
                "mode": "copy",
                "assets": [],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["install", "opencode", "--target", str(tmp_path), "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["error"] == {
        "message": f"Install manifest assets must be an object: {manifest}",
        "type": "TypeError",
    }
    assert payload["conflicts"] == []
    assert list(manifest.parent.iterdir()) == [manifest]


def test_install_plan_construction_failure_json_reports_type_error(
    monkeypatch, tmp_path: Path
) -> None:
    def fail_plan(*args: object, **kwargs: object) -> object:
        raise TypeError("injected plan failure")

    monkeypatch.setattr(cli, "build_install_plan", fail_plan)

    result = runner.invoke(
        app,
        ["install", "opencode", "--target", str(tmp_path), "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["error"] == {"message": "injected plan failure", "type": "TypeError"}
    assert payload["conflicts"] == []
    assert list(tmp_path.iterdir()) == []


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


@pytest.mark.parametrize(
    "arguments",
    [
        ["install", "invalid-runtime"],
        ["install", "opencode", "--scope", "invalid-scope"],
        ["install", "opencode", "--mode", "invalid-mode"],
    ],
)
def test_install_invalid_runtime_scope_or_mode_is_usage_error(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 2
