import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "reinstall_plugins.py"
SPEC = importlib.util.spec_from_file_location("reinstall_plugins", SCRIPT)
assert SPEC and SPEC.loader
reinstall_plugins = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reinstall_plugins
SPEC.loader.exec_module(reinstall_plugins)


def test_detects_existing_runtime_install_details() -> None:
    codex = reinstall_plugins.detect_codex_install(
        {"installed": [{"pluginId": "waterology@waterology", "enabled": True}]}
    )
    claude = reinstall_plugins.detect_claude_install(
        [
            {
                "id": "waterology@waterology",
                "scope": "local",
                "enabled": False,
            }
        ]
    )

    assert codex == reinstall_plugins.Installation("codex", None, True)
    assert claude == reinstall_plugins.Installation("claude", "local", False)


def test_default_selection_reinstalls_only_previous_installs() -> None:
    installs = {
        "codex": reinstall_plugins.Installation("codex", None, True),
        "claude": None,
    }

    assert reinstall_plugins.select_runtimes("auto", installs) == ("codex",)
    with pytest.raises(reinstall_plugins.ReinstallError, match="No previous Waterology"):
        reinstall_plugins.select_runtimes("auto", {"codex": None, "claude": None})


def test_plan_preserves_claude_scope_data_and_disabled_state(tmp_path: Path) -> None:
    install = reinstall_plugins.Installation("claude", "project", False)

    plan = reinstall_plugins.build_plan(
        "claude",
        install,
        marketplace_present=True,
        marketplace_matches=False,
        project_root=tmp_path,
        requested_scope=None,
    )

    assert plan == (
        (
            "claude",
            "plugin",
            "uninstall",
            "waterology@waterology",
            "--scope",
            "project",
            "--keep-data",
            "-y",
        ),
        ("claude", "plugin", "marketplace", "remove", "waterology", "--scope", "project"),
        (
            "claude",
            "plugin",
            "marketplace",
            "add",
            str(tmp_path.resolve()),
            "--scope",
            "project",
        ),
        (
            "claude",
            "plugin",
            "install",
            "waterology@waterology",
            "--scope",
            "project",
            "-y",
        ),
        (
            "claude",
            "plugin",
            "disable",
            "waterology@waterology",
            "--scope",
            "project",
        ),
    )


def test_existing_claude_scope_is_not_overridden(tmp_path: Path) -> None:
    install = reinstall_plugins.Installation("claude", "local", True)

    plan = reinstall_plugins.build_plan(
        "claude",
        install,
        marketplace_present=True,
        marketplace_matches=True,
        project_root=tmp_path,
        requested_scope="user",
    )

    assert all("local" in command for command in plan)
    assert all("user" not in command for command in plan)


def test_cache_buster_restores_manifests_after_failure(tmp_path: Path) -> None:
    paths = []
    for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        path = tmp_path / relative
        path.parent.mkdir()
        path.write_text(json.dumps({"name": "waterology", "version": "0.5.2"}) + "\n")
        paths.append(path)
    originals = [(path.read_bytes(), path.stat().st_mode) for path in paths]

    with (
        pytest.raises(RuntimeError, match="stop"),
        reinstall_plugins.cache_busted_manifests(tmp_path) as version,
    ):
        assert version.startswith("0.5.2+dev.")
        assert all(json.loads(path.read_text())["version"] == version for path in paths)
        raise RuntimeError("stop")

    assert [(path.read_bytes(), path.stat().st_mode) for path in paths] == originals
