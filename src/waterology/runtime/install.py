import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from waterology.runtime.assets import AssetCatalog


class Runtime(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"


class InstallScope(StrEnum):
    PROJECT = "project"
    USER = "user"


class InstallMode(StrEnum):
    COPY = "copy"
    LINK = "link"


@dataclass(frozen=True)
class InstallAction:
    source: Path
    source_id: str
    destination: Path
    operation: str
    manifest: Path


@dataclass(frozen=True)
class InstallPlan:
    runtime: Runtime
    scope: InstallScope
    mode: InstallMode
    actions: tuple[InstallAction, ...]


def build_install_plan(
    runtime: Runtime,
    scope: InstallScope,
    target: Path,
    mode: InstallMode,
    catalog: AssetCatalog,
) -> InstallPlan:
    directories = _destination_directories(runtime, scope, target)
    actions = (
        _skill_actions(catalog, directories["skills"], mode)
        + _file_actions(catalog, _agent_directory(runtime), directories["agents"], mode)
        + _command_actions(catalog, directories.get("commands"), mode)
    )
    return InstallPlan(runtime=runtime, scope=scope, mode=mode, actions=actions)


def _destination_directories(
    runtime: Runtime,
    scope: InstallScope,
    target: Path,
) -> dict[str, Path]:
    if scope is InstallScope.PROJECT:
        return _runtime_directories(runtime, target)

    if runtime is Runtime.OPENCODE:
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            base = Path(config_home) / "opencode"
            return {"skills": base / "skills", "agents": base / "agents"}

        base = Path.home() / ".config" / "opencode"
        return {
            "skills": base / "skills",
            "agents": base / "agents",
        }
    return _runtime_directories(runtime, Path.home())


def _runtime_directories(runtime: Runtime, base: Path) -> dict[str, Path]:
    if runtime is Runtime.CLAUDE:
        return {
            "skills": base / ".claude" / "skills",
            "agents": base / ".claude" / "agents",
            "commands": base / ".claude" / "commands",
        }
    if runtime is Runtime.CODEX:
        return {"skills": base / ".agents" / "skills", "agents": base / ".codex" / "agents"}
    return {"skills": base / ".opencode" / "skills", "agents": base / ".opencode" / "agents"}


def _agent_directory(runtime: Runtime) -> str:
    if runtime is Runtime.CLAUDE:
        return "agents"
    if runtime is Runtime.CODEX:
        return ".codex/agents"
    return ".opencode/agents"


def _skill_actions(
    catalog: AssetCatalog, destination: Path, mode: InstallMode
) -> tuple[InstallAction, ...]:
    return tuple(
        _action(catalog, source, destination / source.name, mode)
        for source in catalog.skill_directories()
    )


def _file_actions(
    catalog: AssetCatalog,
    source_directory: str,
    destination: Path,
    mode: InstallMode,
) -> tuple[InstallAction, ...]:
    sources = sorted(catalog.path(source_directory).glob("*.md"))
    if source_directory == ".codex/agents":
        sources = sorted(catalog.path(source_directory).glob("*.toml"))
    return tuple(_action(catalog, source, destination / source.name, mode) for source in sources)


def _command_actions(
    catalog: AssetCatalog,
    destination: Path | None,
    mode: InstallMode,
) -> tuple[InstallAction, ...]:
    if destination is None:
        return ()
    sources = sorted(catalog.path("commands").glob("*.md"))
    return tuple(_action(catalog, source, destination / source.name, mode) for source in sources)


def _action(
    catalog: AssetCatalog, source: Path, destination: Path, mode: InstallMode
) -> InstallAction:
    source_id = source.relative_to(catalog.root.resolve()).as_posix()
    return InstallAction(
        source=source,
        source_id=source_id,
        destination=destination,
        operation=mode.value,
        manifest=destination.parent.parent / ".waterology-install.json",
    )
