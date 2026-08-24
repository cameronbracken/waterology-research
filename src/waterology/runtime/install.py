import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from waterology import __version__
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


@dataclass(frozen=True)
class InstallConflict:
    destination: Path
    reason: str


class InstallConflictError(RuntimeError):
    def __init__(self, conflicts: tuple[InstallConflict, ...]) -> None:
        self.conflicts = conflicts
        super().__init__("Install destinations conflict with existing files")


@dataclass(frozen=True)
class InstallResult:
    changed: tuple[Path, ...]
    unchanged: tuple[Path, ...]
    manifests: tuple[Path, ...]


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


def preflight(plan: InstallPlan, force: bool = False) -> tuple[InstallConflict, ...]:
    records = _load_manifests(plan)
    conflicts = []
    blocked_parents: set[Path] = set()
    for action in plan.actions:
        blocked_parent = _blocked_parent(action.destination.parent)
        if blocked_parent is not None and blocked_parent not in blocked_parents:
            conflicts.append(
                InstallConflict(blocked_parent, "destination parent is not a directory")
            )
            blocked_parents.add(blocked_parent)

        if not action.destination.exists() and not action.destination.is_symlink():
            continue
        key = action.destination.relative_to(action.manifest.parent).as_posix()
        prior = records[action.manifest]["assets"].get(key)
        if not isinstance(prior, dict):
            conflicts.append(InstallConflict(action.destination, "destination is not owned"))
            continue
        prior_sha256 = prior.get("sha256")
        if not isinstance(prior_sha256, str):
            conflicts.append(
                InstallConflict(action.destination, "manifest ownership record is invalid")
            )
            continue
        unchanged_since_install = _fingerprint(action.destination) == prior_sha256
        if not unchanged_since_install and not force:
            conflicts.append(InstallConflict(action.destination, "owned destination was modified"))
    return tuple(conflicts)


def apply_install_plan(plan: InstallPlan, force: bool = False) -> InstallResult:
    conflicts = preflight(plan, force=force)
    if conflicts:
        raise InstallConflictError(conflicts)

    changed, unchanged = _apply_actions(plan.actions)
    manifests = _write_install_manifests(plan)
    return InstallResult(tuple(changed), tuple(unchanged), tuple(manifests))


def _load_manifests(plan: InstallPlan) -> dict[Path, dict]:
    records = {}
    for manifest in sorted({action.manifest for action in plan.actions}):
        if manifest.is_symlink():
            raise ValueError(f"Install manifest must be a regular file: {manifest}")
        if not manifest.exists():
            records[manifest] = {"assets": {}}
            continue
        if not manifest.is_file():
            raise ValueError(f"Install manifest must be a regular file: {manifest}")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema") != 1:
            schema = data.get("schema") if isinstance(data, dict) else None
            raise ValueError(f"Unsupported install manifest schema in {manifest}: {schema}")
        if not isinstance(data.get("assets"), dict):
            raise TypeError(f"Install manifest assets must be an object: {manifest}")
        records[manifest] = data
    return records


def _blocked_parent(parent: Path) -> Path | None:
    candidate = parent
    while not candidate.exists() and not candidate.is_symlink():
        if candidate.parent == candidate:
            return None
        candidate = candidate.parent
    if candidate.is_dir():
        return None
    return candidate


def _apply_actions(
    actions: tuple[InstallAction, ...],
) -> tuple[list[Path], list[Path]]:
    changed = []
    unchanged = []
    for action in actions:
        if _matches_planned_source(action):
            unchanged.append(action.destination)
            continue
        _apply_action(action)
        changed.append(action.destination)
    return changed, unchanged


def _matches_planned_source(action: InstallAction) -> bool:
    destination = action.destination
    if action.operation == InstallMode.LINK.value:
        return destination.is_symlink() and destination.resolve() == action.source.resolve()
    if destination.is_symlink():
        return False
    if action.source.is_dir():
        return destination.is_dir() and _fingerprint(destination) == _fingerprint(action.source)
    return destination.is_file() and _fingerprint(destination) == _fingerprint(action.source)


def _apply_action(action: InstallAction) -> None:
    action.destination.parent.mkdir(parents=True, exist_ok=True)
    staged = _reserve_sibling(action.destination, "stage")
    try:
        if action.operation == InstallMode.COPY.value:
            if action.source.is_dir():
                staged.unlink()
                shutil.copytree(action.source, staged)
            else:
                shutil.copy2(action.source, staged)
        elif action.operation == InstallMode.LINK.value:
            staged.unlink()
            staged.symlink_to(
                action.source,
                target_is_directory=action.source.is_dir(),
            )
        else:
            raise ValueError(f"Unsupported install operation: {action.operation}")
        _replace_staged(staged, action.destination)
    finally:
        _remove_path(staged)


def _reserve_sibling(destination: Path, purpose: str) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.waterology-{purpose}-",
        dir=destination.parent,
    )
    os.close(descriptor)
    return Path(name)


def _replace_staged(staged: Path, destination: Path) -> None:
    destination_is_directory = destination.is_dir() and not destination.is_symlink()
    staged_is_directory = staged.is_dir() and not staged.is_symlink()
    destination_exists = destination.exists() or destination.is_symlink()
    if not destination_exists or not (destination_is_directory or staged_is_directory):
        os.replace(staged, destination)
        return

    backup = _reserve_sibling(destination, "backup")
    backup.unlink()
    os.replace(destination, backup)
    try:
        os.replace(staged, destination)
    except BaseException:
        os.replace(backup, destination)
        raise
    _remove_path(backup)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _write_install_manifests(plan: InstallPlan) -> tuple[Path, ...]:
    manifests = []
    for manifest in sorted({action.manifest for action in plan.actions}):
        actions = [action for action in plan.actions if action.manifest == manifest]
        assets = {}
        for action in actions:
            key = action.destination.relative_to(manifest.parent).as_posix()
            assets[key] = {
                "source": action.source_id,
                "sha256": _fingerprint(action.destination),
                "kind": "symlink"
                if action.destination.is_symlink()
                else "directory"
                if action.destination.is_dir()
                else "file",
            }
        payload = {
            "schema": 1,
            "waterology_version": __version__,
            "runtime": plan.runtime.value,
            "mode": plan.mode.value,
            "assets": assets,
        }
        serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if not manifest.exists() or manifest.read_text(encoding="utf-8") != serialized:
            manifest.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = _reserve_sibling(manifest, "stage")
            try:
                temporary_path.write_text(serialized, encoding="utf-8")
                os.replace(temporary_path, manifest)
            finally:
                _remove_path(temporary_path)
        manifests.append(manifest)
    return tuple(manifests)


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(str(path.resolve()).encode())
    elif path.is_dir():
        for child in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
            digest.update(child.relative_to(path).as_posix().encode())
            digest.update(b"\0")
            digest.update(child.read_bytes())
    else:
        digest.update(path.read_bytes())
    return digest.hexdigest()


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
