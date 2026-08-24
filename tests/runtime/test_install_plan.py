from pathlib import Path

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.install import (
    InstallMode,
    InstallScope,
    Runtime,
    build_install_plan,
)


def test_project_codex_plan_uses_shared_skills_and_codex_agents(tmp_path: Path) -> None:
    plan = build_install_plan(
        runtime=Runtime.CODEX,
        scope=InstallScope.PROJECT,
        target=tmp_path,
        mode=InstallMode.COPY,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".agents/skills/project-conventions" in destinations
    assert ".codex/agents/researcher.toml" in destinations
    assert all(action.operation == "copy" for action in plan.actions)


def test_project_claude_plan_keeps_command_shims(tmp_path: Path) -> None:
    plan = build_install_plan(
        runtime=Runtime.CLAUDE,
        scope=InstallScope.PROJECT,
        target=tmp_path,
        mode=InstallMode.LINK,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".claude/skills/deep-research" in destinations
    assert ".claude/agents/researcher.md" in destinations
    assert ".claude/commands/deepresearch.md" in destinations
    assert all(action.operation == "link" for action in plan.actions)


def test_project_opencode_plan_uses_v2_paths(tmp_path: Path) -> None:
    plan = build_install_plan(
        runtime=Runtime.OPENCODE,
        scope=InstallScope.PROJECT,
        target=tmp_path,
        mode=InstallMode.COPY,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".opencode/skills/project-conventions" in destinations
    assert ".opencode/agents/researcher.md" in destinations


def test_user_codex_plan_uses_home_directories(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    plan = build_install_plan(
        runtime=Runtime.CODEX,
        scope=InstallScope.USER,
        target=Path("unused"),
        mode=InstallMode.LINK,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".agents/skills/project-conventions" in destinations
    assert ".codex/agents/researcher.toml" in destinations


def test_user_opencode_plan_honors_xdg_config_home(tmp_path: Path, monkeypatch) -> None:
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    plan = build_install_plan(
        runtime=Runtime.OPENCODE,
        scope=InstallScope.USER,
        target=Path("unused"),
        mode=InstallMode.COPY,
        catalog=AssetCatalog.discover(),
    )

    destinations = {
        action.destination.relative_to(config_home).as_posix() for action in plan.actions
    }
    assert "opencode/skills/project-conventions" in destinations
    assert "opencode/agents/researcher.md" in destinations


def test_user_opencode_plan_falls_back_when_xdg_config_home_is_empty(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", "")

    plan = build_install_plan(
        runtime=Runtime.OPENCODE,
        scope=InstallScope.USER,
        target=Path("unused"),
        mode=InstallMode.COPY,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".config/opencode/skills/project-conventions" in destinations
