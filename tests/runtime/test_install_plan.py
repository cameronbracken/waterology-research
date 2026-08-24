from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    ("runtime", "expected_manifests"),
    [
        (Runtime.CLAUDE, {".claude/.waterology-install.json"}),
        (
            Runtime.CODEX,
            {".agents/.waterology-install.json", ".codex/.waterology-install.json"},
        ),
        (Runtime.OPENCODE, {".opencode/.waterology-install.json"}),
    ],
)
def test_project_plans_put_manifests_at_runtime_roots(
    tmp_path: Path, runtime: Runtime, expected_manifests: set[str]
) -> None:
    plan = build_install_plan(
        runtime=runtime,
        scope=InstallScope.PROJECT,
        target=tmp_path,
        mode=InstallMode.COPY,
        catalog=AssetCatalog.discover(),
    )

    manifests = {action.manifest.relative_to(tmp_path).as_posix() for action in plan.actions}

    assert manifests == expected_manifests


def test_plan_actions_are_deterministic_catalog_relative_and_dry(tmp_path: Path) -> None:
    catalog = AssetCatalog.discover()

    plan = build_install_plan(
        runtime=Runtime.CLAUDE,
        scope=InstallScope.PROJECT,
        target=tmp_path,
        mode=InstallMode.LINK,
        catalog=catalog,
    )

    source_ids = [action.source_id for action in plan.actions]
    skill_ids = [source_id for source_id in source_ids if source_id.startswith("skills/")]
    agent_ids = [source_id for source_id in source_ids if source_id.startswith("agents/")]
    command_ids = [source_id for source_id in source_ids if source_id.startswith("commands/")]

    assert source_ids == skill_ids + agent_ids + command_ids
    assert skill_ids == sorted(skill_ids)
    assert agent_ids == sorted(agent_ids)
    assert command_ids == sorted(command_ids)
    assert all(
        action.source_id == action.source.relative_to(catalog.root).as_posix()
        for action in plan.actions
    )
    assert all("\\" not in action.source_id for action in plan.actions)
    assert all(action.source.is_dir() for action in plan.actions[: len(skill_ids)])
    assert all(action.source.is_file() for action in plan.actions[len(skill_ids) :])
    assert not any(tmp_path.iterdir())


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


def test_user_claude_plan_uses_home_directories(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    plan = build_install_plan(
        runtime=Runtime.CLAUDE,
        scope=InstallScope.USER,
        target=Path("unused"),
        mode=InstallMode.COPY,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".claude/skills/project-conventions" in destinations
    assert ".claude/agents/researcher.md" in destinations
    assert ".claude/commands/deepresearch.md" in destinations


def test_user_opencode_plan_honors_xdg_config_home(tmp_path: Path, monkeypatch) -> None:
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: (_ for _ in ()).throw(AssertionError("Path.home() was called"))),
    )

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
