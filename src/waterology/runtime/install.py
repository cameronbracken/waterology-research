import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from waterology import __version__
from waterology.runtime.assets import AssetCatalog

_RECOVERY_LOCK_NAME = ".waterology-install-recovery.lock"
_TRANSACTION_NAME = ".waterology-install-transaction.json"
_INSTALL_LOCK_NAME = ".waterology-install.lock"
_LOCAL_ASSET_PATTERNS = ("__pycache__", "*.pyc", "*.pyo", ".DS_Store")


class Runtime(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"
    PI = "pi"


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
    trusted_root: Path


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


@dataclass
class _PreparedChange:
    destination: Path
    staged: Path | None
    expected: "_PathState"
    backup: Path | None = None
    installed_state: "_PathState | None" = None
    installed: bool = False


@dataclass(frozen=True)
class _PathState:
    kind: str
    sha256: str | None


def build_install_plan(
    runtime: Runtime,
    scope: InstallScope,
    target: Path,
    mode: InstallMode,
    catalog: AssetCatalog,
) -> InstallPlan:
    directories, trusted_root = _installation_layout(runtime, scope, target)
    agent_directory = _agent_directory(runtime)
    actions = (
        _skill_actions(catalog, directories["skills"], mode)
        + (
            _file_actions(catalog, agent_directory, directories["agents"], mode)
            if agent_directory is not None
            else ()
        )
        + _command_actions(catalog, directories.get("commands"), mode)
        + _mcp_configuration_actions(catalog, runtime, scope, trusted_root)
    )
    return InstallPlan(
        runtime=runtime,
        scope=scope,
        mode=mode,
        actions=actions,
        trusted_root=trusted_root,
    )


def preflight(plan: InstallPlan, force: bool = False) -> tuple[InstallConflict, ...]:
    conflicts, _ = _preflight(plan, force=force)
    return conflicts


def _preflight(
    plan: InstallPlan, force: bool = False
) -> tuple[tuple[InstallConflict, ...], dict[Path, _PathState]]:
    _require_no_transaction(plan.trusted_root)
    path_conflicts = _plan_path_conflicts(plan)
    if path_conflicts:
        return path_conflicts, {}
    expected_states = _snapshot_plan_paths(plan)
    records = _load_manifests(plan)
    expected_states.update(_record_states(records))
    conflicts = list(_retired_conflicts(plan, records))
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
        if (
            action.operation == InstallMode.LINK.value
            and action.destination.resolve() != action.source.resolve()
            and not force
        ):
            conflicts.append(
                InstallConflict(
                    action.destination,
                    "owned symlink points to a different source",
                )
            )
            continue
        unchanged_since_install = _fingerprint(action.destination).lower() == prior_sha256.lower()
        is_config = action.source_id in {".mcp.json", ".codex/config.toml", "opencode.json"}
        if not unchanged_since_install and (not force or is_config):
            conflicts.append(InstallConflict(action.destination, "owned destination was modified"))
    conflicts.extend(_state_conflicts(expected_states, "path changed during preflight"))
    return tuple(conflicts), expected_states


def _plan_path_conflicts(plan: InstallPlan) -> tuple[InstallConflict, ...]:
    trusted_root = _absolute_lexical(plan.trusted_root)
    paths = [
        *(action.destination for action in plan.actions),
        *(sorted({action.manifest for action in plan.actions})),
    ]
    conflicts = []
    relative_paths: dict[Path, Path] = {}
    for path in paths:
        lexical = _absolute_lexical(path)
        if path != lexical:
            conflicts.append(InstallConflict(path, "path is not normalized"))
            continue
        try:
            relative_paths[path] = lexical.relative_to(trusted_root)
        except ValueError:
            conflicts.append(InstallConflict(path, "path escapes the trusted root"))
    for action in plan.actions:
        try:
            _absolute_lexical(action.destination).relative_to(
                _absolute_lexical(action.manifest.parent)
            )
        except ValueError:
            conflicts.append(
                InstallConflict(action.destination, "destination is outside its manifest root")
            )
    if conflicts:
        return tuple(conflicts)

    linked_parents: set[Path] = set()
    for path, relative in relative_paths.items():
        current = trusted_root
        for part in relative.parts[:-1]:
            current /= part
            if current.is_symlink() and current not in linked_parents:
                conflicts.append(InstallConflict(current, "destination parent traverses a symlink"))
                linked_parents.add(current)
                break
    return tuple(conflicts)


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(path))


def apply_install_plan(plan: InstallPlan, force: bool = False) -> InstallResult:
    conflicts, _ = _preflight(plan, force=force)
    if conflicts:
        raise InstallConflictError(conflicts)

    _require_no_transaction(plan.trusted_root)
    lock, lock_parents = _acquire_install_lock(plan.trusted_root)
    try:
        conflicts, expected_states = _preflight(plan, force=force)
        if conflicts:
            raise InstallConflictError(conflicts)
        return _apply_locked_plan(plan, expected_states)
    finally:
        lock.unlink(missing_ok=True)
        _cleanup_created_parents(lock_parents)


def _apply_locked_plan(plan: InstallPlan, expected_states: dict[Path, _PathState]) -> InstallResult:
    prepared: list[_PreparedChange] = []
    created_parents: list[Path] = []
    changed = []
    unchanged = []
    manifests = tuple(sorted({action.manifest for action in plan.actions}))
    committed = False
    records = _load_manifests(plan)
    for destination in _retired_paths(plan, records):
        if expected_states[destination].kind != "missing":
            prepared.append(_PreparedChange(destination, None, expected_states[destination]))
            changed.append(destination)
    try:
        for action in plan.actions:
            if _matches_planned_source(action):
                unchanged.append(action.destination)
                continue
            staged = _stage_action(action, plan.trusted_root, created_parents)
            prepared.append(
                _PreparedChange(
                    action.destination,
                    staged,
                    expected_states[action.destination],
                )
            )
            changed.append(action.destination)
        staged_assets = {
            change.destination: change.staged for change in prepared if change.staged is not None
        }
        prepared.extend(
            _stage_install_manifests(
                plan,
                staged_assets,
                expected_states,
                created_parents,
            )
        )
        _run_transaction(prepared, expected_states, plan)
        committed = True
    finally:
        _cleanup_staged_paths(prepared)
        if committed:
            _cleanup_backups(prepared)
        else:
            _cleanup_created_parents(created_parents)
    return InstallResult(tuple(changed), tuple(unchanged), manifests)


def _acquire_install_lock(trusted_root: Path) -> tuple[Path, list[Path]]:
    created_parents: list[Path] = []
    _ensure_parent(trusted_root, trusted_root.parent, created_parents)
    lock = trusted_root / _INSTALL_LOCK_NAME
    _check_recovery_lock(trusted_root)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        _cleanup_created_parents(created_parents)
        raise InstallConflictError(
            (InstallConflict(lock, "another Waterology install is in progress"),)
        ) from error
    except BaseException:
        _cleanup_created_parents(created_parents)
        raise
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        _check_recovery_lock(trusted_root)
    except BaseException:
        lock.unlink(missing_ok=True)
        _cleanup_created_parents(created_parents)
        raise
    return lock, created_parents


def _load_manifests(plan: InstallPlan) -> dict[Path, dict]:
    records = {}
    planned = _planned_actions_by_manifest(plan)
    for manifest in sorted({action.manifest for action in plan.actions}):
        if manifest.is_symlink():
            raise ValueError(f"Install manifest must be a regular file: {manifest}")
        if not manifest.exists():
            records[manifest] = {"assets": {}}
            continue
        if not manifest.is_file():
            raise ValueError(f"Install manifest must be a regular file: {manifest}")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        schema = data.get("schema") if isinstance(data, dict) else None
        if not isinstance(data, dict) or type(schema) is not int or schema != 1:
            raise ValueError(f"Unsupported install manifest schema in {manifest}: {schema}")
        if data.get("runtime") != plan.runtime.value:
            raise ValueError(f"Install manifest runtime does not match the plan: {manifest}")
        if data.get("mode") != plan.mode.value:
            raise ValueError(f"Install manifest mode does not match the plan: {manifest}")
        version = data.get("waterology_version")
        if not isinstance(version, str) or not version:
            raise ValueError(
                f"Install manifest waterology_version must be a nonempty string: {manifest}"
            )
        if not isinstance(data.get("assets"), dict):
            raise TypeError(f"Install manifest assets must be an object: {manifest}")
        _validate_manifest_assets(manifest, data["assets"], planned[manifest])
        records[manifest] = data
    return records


def _planned_actions_by_manifest(plan: InstallPlan) -> dict[Path, dict[str, InstallAction]]:
    planned = {manifest: {} for manifest in {action.manifest for action in plan.actions}}
    for action in plan.actions:
        key = action.destination.relative_to(action.manifest.parent).as_posix()
        planned[action.manifest][key] = action
    return planned


def _validate_manifest_assets(
    manifest: Path,
    assets: dict,
    planned: dict[str, InstallAction],
) -> None:
    for key, record in assets.items():
        if not _is_normalized_relative_key(key):
            raise ValueError(
                f"Install manifest asset key must be a normalized relative path: {manifest}: {key}"
            )
        if not isinstance(record, dict) or set(record) != {"source", "sha256", "kind"}:
            raise ValueError(f"Invalid install manifest asset record: {manifest}: {key}")
        source = record.get("source")
        sha256 = record.get("sha256")
        kind = record.get("kind")
        if (
            not isinstance(source, str)
            or not isinstance(sha256, str)
            or re.fullmatch(r"[0-9a-fA-F]{64}", sha256) is None
            or not isinstance(kind, str)
            or kind not in {"file", "directory", "symlink"}
        ):
            raise ValueError(f"Invalid install manifest asset record: {manifest}: {key}")
        action = planned.get(key)
        if action is None:
            _validate_retired_record(manifest, key, record, planned)
            continue
        if source != action.source_id:
            raise ValueError(
                f"Install manifest asset source does not match the plan: {manifest}: {key}"
            )
        expected_kind = _planned_kind(action)
        if kind != expected_kind:
            raise ValueError(
                f"Install manifest asset kind does not match the plan: {manifest}: {key}"
            )
        actual_kind = _path_kind(action.destination)
        destination_exists = action.destination.exists() or action.destination.is_symlink()
        if destination_exists and actual_kind != kind:
            raise ValueError(
                f"Install manifest asset kind does not match the destination: {manifest}: {key}"
            )


def _validate_retired_record(
    manifest: Path, key: str, record: dict, planned: dict[str, InstallAction]
) -> None:
    # Old names are allowed only within a known asset family, with the same
    # source/destination mapping. A manifest cannot claim arbitrary user files.
    relative = PurePosixPath(key)
    source = PurePosixPath(record["source"])
    for candidate_key, action in planned.items():
        candidate = PurePosixPath(candidate_key)
        candidate_source = PurePosixPath(action.source_id)
        if (
            len(relative.parts) == 2
            and relative.parent == candidate.parent
            and source == candidate_source.parent / relative.name
            and relative.suffix == candidate.suffix
            and record["kind"] == _planned_kind(action)
        ):
            return
    raise ValueError(f"Install manifest asset is not in a managed asset family: {manifest}: {key}")


def _record_states(records: dict[Path, dict]) -> dict[Path, _PathState]:
    return {
        manifest.parent / key: _path_state(manifest.parent / key)
        for manifest, data in records.items()
        for key in data["assets"]
    }


def _retired_paths(plan: InstallPlan, records: dict[Path, dict]) -> tuple[Path, ...]:
    current = {action.destination for action in plan.actions}
    return tuple(path for path in _record_states(records) if path not in current)


def _retired_conflicts(plan: InstallPlan, records: dict[Path, dict]) -> tuple[InstallConflict, ...]:
    current = {action.destination for action in plan.actions}
    return tuple(
        InstallConflict(
            manifest.parent / key, "retired owned destination was modified; manual cleanup required"
        )
        for manifest, data in records.items()
        for key, record in data["assets"].items()
        if manifest.parent / key not in current
        and _path_state(manifest.parent / key).kind != "missing"
        and _path_state(manifest.parent / key)
        != _PathState(record["kind"], record["sha256"].lower())
    )


def build_uninstall_plan(
    runtime: Runtime, scope: InstallScope, target: Path, catalog: AssetCatalog
) -> InstallPlan:
    plan = build_install_plan(runtime, scope, target, InstallMode.COPY, catalog)
    conflicts = _plan_path_conflicts(plan)
    if conflicts:
        raise InstallConflictError(conflicts)
    modes = set()
    for manifest in {action.manifest for action in plan.actions}:
        if manifest.is_symlink():
            raise ValueError(f"Install manifest must be a regular file: {manifest}")
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Invalid install manifest: {manifest}")
            modes.add(InstallMode(data.get("mode")))
    if len(modes) > 1:
        raise ValueError("Installation manifests disagree on install mode; manual cleanup required")
    if modes:
        plan = build_install_plan(runtime, scope, target, modes.pop(), catalog)
    return plan


def uninstall_preflight(plan: InstallPlan) -> tuple[InstallConflict, ...]:
    conflicts, _ = _uninstall_preflight(plan)
    return conflicts


def _uninstall_preflight(
    plan: InstallPlan,
) -> tuple[tuple[InstallConflict, ...], dict[Path, _PathState]]:
    _require_no_transaction(plan.trusted_root)
    conflicts = _plan_path_conflicts(plan)
    if conflicts:
        return conflicts, {}
    expected = {
        manifest: _path_state(manifest) for manifest in {action.manifest for action in plan.actions}
    }
    records = _load_manifests(plan)
    expected.update(_record_states(records))
    conflicts = []
    for manifest, data in records.items():
        for key, record in data["assets"].items():
            path = manifest.parent / key
            state = expected[path]
            if state.kind != "missing" and state != _PathState(
                record["kind"], record["sha256"].lower()
            ):
                conflicts.append(
                    InstallConflict(path, "owned destination was modified; manual cleanup required")
                )
    conflicts.extend(_state_conflicts(expected, "path changed during uninstall preflight"))
    return tuple(conflicts), expected


def uninstall_paths(plan: InstallPlan) -> tuple[Path, ...]:
    """Return recorded assets and manifests, including assets retired upstream."""
    records = _load_manifests(plan)
    return tuple(_record_states(records)) + tuple(path for path in records if path.exists())


def apply_uninstall_plan(plan: InstallPlan) -> InstallResult:
    """Remove an unchanged managed installation, preserving unowned paths."""
    conflicts, expected = _uninstall_preflight(plan)
    if conflicts:
        raise InstallConflictError(conflicts)
    if all(state.kind == "missing" for state in expected.values()):
        return InstallResult((), (), ())
    _require_no_transaction(plan.trusted_root)
    lock, parents = _acquire_install_lock(plan.trusted_root)
    prepared = []
    committed = False
    try:
        conflicts, expected = _uninstall_preflight(plan)
        if conflicts:
            raise InstallConflictError(conflicts)
        prepared = [
            _PreparedChange(path, None, state)
            for path, state in expected.items()
            if state.kind != "missing"
        ]
        _run_transaction(prepared, expected, plan)
        committed = True
        return InstallResult(tuple(change.destination for change in prepared), (), ())
    finally:
        if committed:
            _cleanup_backups(prepared)
        lock.unlink(missing_ok=True)
        _cleanup_created_parents(parents)


def _is_normalized_relative_key(key: object) -> bool:
    if not isinstance(key, str) or not key or "\\" in key:
        return False
    path = PurePosixPath(key)
    return (
        not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in path.parts)
        and path.as_posix() == key
    )


def _planned_kind(action: InstallAction) -> str:
    if action.operation == InstallMode.LINK.value:
        return "symlink"
    if action.operation != InstallMode.COPY.value:
        raise ValueError(f"Unsupported install operation: {action.operation}")
    return "directory" if action.source.is_dir() else "file"


def _path_kind(path: Path) -> str | None:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return None


def _path_state(path: Path) -> _PathState:
    kind = _path_kind(path)
    if kind is None:
        if path.exists() or path.is_symlink():
            return _PathState("other", None)
        return _PathState("missing", None)
    return _PathState(kind, _fingerprint(path))


def _snapshot_plan_paths(plan: InstallPlan) -> dict[Path, _PathState]:
    paths = [
        *(action.destination for action in plan.actions),
        *(sorted({action.manifest for action in plan.actions})),
    ]
    return {path: _path_state(path) for path in dict.fromkeys(paths)}


def _state_conflicts(
    expected_states: dict[Path, _PathState], reason: str
) -> tuple[InstallConflict, ...]:
    return tuple(
        InstallConflict(path, reason)
        for path, expected in expected_states.items()
        if _path_state(path) != expected
    )


def _blocked_parent(parent: Path) -> Path | None:
    candidate = parent
    while not candidate.exists() and not candidate.is_symlink():
        if candidate.parent == candidate:
            return None
        candidate = candidate.parent
    if candidate.is_dir():
        return None
    return candidate


def _matches_planned_source(action: InstallAction) -> bool:
    destination = action.destination
    if action.operation == InstallMode.LINK.value:
        return destination.is_symlink() and destination.resolve() == action.source.resolve()
    if destination.is_symlink():
        return False
    if action.source.is_dir():
        return destination.is_dir() and _fingerprint(destination) == _fingerprint(
            action.source, source_assets=True
        )
    return destination.is_file() and _fingerprint(destination) == _fingerprint(action.source)


def _stage_action(
    action: InstallAction,
    trusted_root: Path,
    created_parents: list[Path],
) -> Path:
    _ensure_parent(action.destination.parent, trusted_root, created_parents)
    staged = _reserve_sibling(action.destination, "stage")
    try:
        if action.operation == InstallMode.COPY.value:
            if action.source.is_dir():
                staged.unlink()
                shutil.copytree(
                    action.source, staged, ignore=shutil.ignore_patterns(*_LOCAL_ASSET_PATTERNS)
                )
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
    except BaseException:
        _remove_path(staged)
        raise
    return staged


def _ensure_parent(parent: Path, trusted_root: Path, created_parents: list[Path]) -> None:
    missing = []
    candidate = parent
    stop = _absolute_lexical(trusted_root).parent
    while not candidate.exists() and not candidate.is_symlink() and candidate != stop:
        missing.append(candidate)
        candidate = candidate.parent
    for directory in reversed(missing):
        directory.mkdir()
        created_parents.append(directory)


def _reserve_sibling(destination: Path, purpose: str) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.waterology-{purpose}-",
        dir=destination.parent,
    )
    os.close(descriptor)
    return Path(name)


def _require_no_transaction(root: Path) -> None:
    path = root / _TRANSACTION_NAME
    if path.exists() or path.is_symlink():
        raise InstallConflictError(
            (InstallConflict(path, "interrupted transaction; run install-recover before retrying"),)
        )


def _write_transaction(path: Path, payload: dict) -> None:
    temporary = _reserve_sibling(path, "journal")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _run_transaction(
    prepared: list[_PreparedChange], expected: dict[Path, _PathState], plan: InstallPlan
) -> None:
    """Keep rollback material discoverable if the installing process is killed."""
    root = plan.trusted_root
    journal = root / _TRANSACTION_NAME
    _require_no_transaction(root)
    records = []
    for change in prepared:
        if change.expected.kind != "missing":
            change.backup = _reserve_sibling(change.destination, "backup")
            change.backup.unlink()
        installed = (
            _path_state(change.staged) if change.staged is not None else _PathState("missing", None)
        )
        records.append(
            {
                "destination": change.destination.relative_to(root).as_posix(),
                "staged": change.staged.relative_to(root).as_posix()
                if change.staged is not None
                else None,
                "backup": change.backup.relative_to(root).as_posix()
                if change.backup is not None
                else None,
                "before": {"kind": change.expected.kind, "sha256": change.expected.sha256},
                "after": {"kind": installed.kind, "sha256": installed.sha256},
            }
        )
    payload = {
        "schema": 1,
        "pid": os.getpid(),
        "runtime": plan.runtime.value,
        "state": "pending",
        "changes": records,
    }
    _write_transaction(journal, payload)
    try:
        _commit_prepared_changes(prepared, expected)
    except BaseException:
        # The commit helper rolls back ordinary exceptions. Retain the journal
        # when an external edit prevented complete restoration.
        if not _state_conflicts(expected, "rollback incomplete"):
            journal.unlink(missing_ok=True)
        raise
    payload["state"] = "committed"
    try:
        _write_transaction(journal, payload)
    except BaseException:
        _rollback_changes(prepared)
        if not _state_conflicts(expected, "rollback incomplete"):
            journal.unlink(missing_ok=True)
        raise
    _cleanup_backups(prepared)
    journal.unlink()


def recover_install(plan: InstallPlan, dry_run: bool = False) -> tuple[Path, ...]:
    """Restore an interrupted transaction after its process has exited."""
    if dry_run or not plan.trusted_root.exists():
        return _recover_install(plan, dry_run)
    with _recovery_guard(plan.trusted_root):
        return _recover_install(plan, dry_run)


@contextmanager
def _recovery_guard(root: Path):
    # OS advisory locks release on process death. Keep the coordination file
    # so another process cannot acquire a different inode during unlink.
    path = root / _RECOVERY_LOCK_NAME
    if path.is_symlink():
        raise ValueError("Recovery lock must not be a symlink")
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            if stream.seek(0, os.SEEK_END) == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise ValueError("Installation recovery is in progress") from error
        else:
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise ValueError("Installation recovery is in progress") from error
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _check_recovery_lock(root: Path) -> None:
    path = root / _RECOVERY_LOCK_NAME
    if path.exists() or path.is_symlink():
        with _recovery_guard(root):
            pass


def _require_exited(pid: object) -> None:
    if type(pid) is not int or pid <= 0:
        raise ValueError("Invalid transaction process identifier")
    if sys.platform == "win32":
        if not _windows_process_is_running(pid):
            return
    else:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
    raise ValueError("Transaction process is still running; recovery refused")


def _windows_process_is_running(pid: int) -> bool:
    # os.kill(pid, 0) terminates processes on Windows. Query a synchronization
    # handle instead; access denial remains a refusal to recover.
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:  # ERROR_INVALID_PARAMETER: no such process
            return False
        raise ctypes.WinError(error)
    try:
        state = kernel.WaitForSingleObject(handle, 0)
        if state == 0:  # WAIT_OBJECT_0: process exited
            return False
        if state == 258:  # WAIT_TIMEOUT: still running
            return True
        raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)


def _recover_install(plan: InstallPlan, dry_run: bool) -> tuple[Path, ...]:
    root = plan.trusted_root
    journal = root / _TRANSACTION_NAME
    if journal.is_symlink():
        raise ValueError("Transaction journal must not be a symlink")
    if not journal.exists():
        lock = root / _INSTALL_LOCK_NAME
        if lock.is_symlink():
            raise ValueError("Install lock must not be a symlink")
        if lock.exists():
            text = lock.read_text()
            _require_exited(int(text))
            if not dry_run:
                if lock.read_text() != text:
                    raise ValueError("Install lock changed during recovery")
                lock.unlink()
            return (lock,)
        return ()
    data = json.loads(journal.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("schema") != 1
        or data.get("runtime") != plan.runtime.value
        or data.get("state") not in {"pending", "committed"}
    ):
        raise ValueError("Invalid transaction journal or runtime mismatch")
    pid = data.get("pid")
    _require_exited(pid)
    changes = data.get("changes")
    if not isinstance(changes, list):
        raise TypeError("Invalid transaction changes")
    manifests = {action.manifest for action in plan.actions}
    destinations = {action.destination for action in plan.actions}
    asset_parents = {
        action.destination.parent
        for action in plan.actions
        if len(PurePosixPath(action.source_id).parts) >= 2
    }
    decoded = []
    for record in changes:
        if not isinstance(record, dict):
            raise TypeError("Invalid transaction change")
        key = record.get("destination")
        if not _is_normalized_relative_key(key):
            raise ValueError("Invalid transaction destination")
        destination = root / key
        if destination not in manifests | destinations and destination.parent not in asset_parents:
            raise ValueError("Transaction destination is outside managed assets")
        for parent in destination.relative_to(root).parents:
            if (root / parent).is_symlink():
                raise ValueError("Transaction destination traverses a symlink")
        paths = []
        for name, purpose in (("backup", "backup"), ("staged", "stage")):
            key = record.get(name)
            path = None
            if key is not None:
                if not _is_normalized_relative_key(key):
                    raise ValueError("Invalid transaction auxiliary path")
                path = root / key
                if path.parent != destination.parent or not path.name.startswith(
                    f".{destination.name}.waterology-{purpose}-"
                ):
                    raise ValueError("Invalid transaction auxiliary path")
            paths.append(path)
        states = []
        for name in ("before", "after"):
            value = record.get(name)
            if not isinstance(value, dict) or value.get("kind") not in {
                "missing",
                "file",
                "directory",
                "symlink",
            }:
                raise ValueError("Invalid transaction state")
            digest = value.get("sha256")
            if value["kind"] != "missing" and (
                not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            ):
                raise ValueError("Invalid transaction fingerprint")
            states.append(_PathState(value["kind"], digest))
        backup, staged = paths
        before, after = states
        actual = _path_state(destination)
        saved = _path_state(backup) if backup is not None else _PathState("missing", None)
        if data["state"] == "committed":
            valid = actual == after and saved in (before, _PathState("missing", None))
        else:
            valid = (actual == before and saved.kind == "missing") or (
                actual in (after, _PathState("missing", None)) and saved == before
            )
        if not valid:
            raise ValueError(
                f"Recovery would overwrite changed data; manual cleanup required: {destination}"
            )
        if staged is not None and _path_state(staged) not in (after, _PathState("missing", None)):
            raise ValueError(f"Staged data changed; manual cleanup required: {staged}")
        decoded.append((destination, backup, staged, before, after, actual, saved))
    if dry_run:
        return tuple(item[0] for item in decoded)
    # Refuse a lock acquired by a different process since the interruption.
    lock = root / _INSTALL_LOCK_NAME
    if lock.is_symlink() or (lock.exists() and lock.read_text() != str(pid)):
        raise ValueError("Install lock does not belong to the interrupted transaction")
    for destination, backup, staged, before, after, actual, saved in reversed(decoded):
        for parent in destination.relative_to(root).parents:
            if (root / parent).is_symlink():
                raise ValueError("Recovery path changed to a symlink")
        if _path_state(destination) != actual or (
            backup is not None and _path_state(backup) != saved
        ):
            raise ValueError(
                f"Data changed during recovery; manual cleanup required: {destination}"
            )
        if staged is not None and _path_state(staged) not in (after, _PathState("missing", None)):
            raise ValueError(f"Staged data changed during recovery: {staged}")
        if data["state"] == "pending":
            if backup is not None and (backup.exists() or backup.is_symlink()):
                _remove_path(destination)
                os.replace(backup, destination)
            elif before.kind == "missing":
                _remove_path(destination)
        elif backup is not None:
            _remove_path(backup)
        if staged is not None:
            _remove_path(staged)
    journal.unlink()
    lock.unlink(missing_ok=True)
    return tuple(item[0] for item in decoded)


def _commit_prepared_changes(
    prepared: list[_PreparedChange], expected_states: dict[Path, _PathState]
) -> None:
    commit_log: list[_PreparedChange] = []
    try:
        conflicts = _state_conflicts(expected_states, "path changed after preflight")
        if conflicts:
            raise InstallConflictError(conflicts)
        for change in prepared:
            if _path_state(change.destination) != change.expected:
                raise InstallConflictError(
                    (
                        InstallConflict(
                            change.destination,
                            "path changed after preflight",
                        ),
                    )
                )
            commit_log.append(change)
            if change.destination.exists() or change.destination.is_symlink():
                backup = change.backup
                if backup is None:
                    backup = _reserve_sibling(change.destination, "backup")
                    backup.unlink()
                try:
                    os.replace(change.destination, backup)
                except BaseException:
                    _remove_path(backup)
                    raise
                change.backup = backup
                if _path_state(backup) != change.expected:
                    raise InstallConflictError(
                        (
                            InstallConflict(
                                change.destination,
                                "destination changed while moving to backup",
                            ),
                        )
                    )
            if change.staged is not None:
                change.installed_state = _path_state(change.staged)
                os.replace(change.staged, change.destination)
                change.installed = True
    except BaseException as error:
        rollback_errors = _rollback_changes(commit_log)
        if rollback_errors:
            error.add_note("Rollback errors: " + "; ".join(str(item) for item in rollback_errors))
        raise


def _rollback_changes(commit_log: list[_PreparedChange]) -> list[OSError]:
    errors = []
    for change in reversed(commit_log):
        try:
            if change.installed:
                if (
                    change.installed_state is None
                    or _path_state(change.destination) != change.installed_state
                ):
                    backup_note = (
                        f"; backup retained at {change.backup}" if change.backup is not None else ""
                    )
                    raise OSError(
                        "Cannot remove an externally changed installed destination: "
                        f"{change.destination}{backup_note}"
                    )
                _remove_path(change.destination)
            if change.backup is not None and (change.backup.exists() or change.backup.is_symlink()):
                if change.destination.exists() or change.destination.is_symlink():
                    raise OSError(
                        f"Cannot restore backup {change.backup} over an unexpected destination: "
                        f"{change.destination}"
                    )
                os.replace(change.backup, change.destination)
        except OSError as error:
            errors.append(error)
    return errors


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _stage_install_manifests(
    plan: InstallPlan,
    staged_assets: dict[Path, Path],
    expected_states: dict[Path, _PathState],
    created_parents: list[Path],
) -> list[_PreparedChange]:
    prepared = []
    try:
        for manifest in sorted({action.manifest for action in plan.actions}):
            actions = [action for action in plan.actions if action.manifest == manifest]
            assets = {}
            for action in actions:
                key = action.destination.relative_to(manifest.parent).as_posix()
                installed = staged_assets.get(action.destination, action.destination)
                assets[key] = {
                    "source": action.source_id,
                    "sha256": _fingerprint(installed),
                    "kind": _planned_kind(action),
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
                _ensure_parent(manifest.parent, plan.trusted_root, created_parents)
                staged = _reserve_sibling(manifest, "stage")
                try:
                    staged.write_text(serialized, encoding="utf-8")
                except BaseException:
                    _remove_path(staged)
                    raise
                prepared.append(_PreparedChange(manifest, staged, expected_states[manifest]))
    except BaseException:
        _cleanup_staged_paths(prepared)
        raise
    return prepared


def _cleanup_staged_paths(prepared: list[_PreparedChange]) -> None:
    for change in prepared:
        if change.staged is not None:
            _remove_path(change.staged)


def _cleanup_backups(prepared: list[_PreparedChange]) -> None:
    for change in prepared:
        if change.backup is not None:
            _remove_path(change.backup)


def _cleanup_created_parents(created_parents: list[Path]) -> None:
    for parent in reversed(created_parents):
        try:
            parent.rmdir()
        except OSError:
            pass


def _fingerprint(path: Path, *, source_assets: bool = False) -> str:
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(str(path.resolve()).encode())
    elif path.is_dir():
        for child in sorted(path.rglob("*")):
            relative = child.relative_to(path)
            if source_assets and any(
                fnmatch.fnmatch(part, pattern)
                for part in relative.parts
                for pattern in _LOCAL_ASSET_PATTERNS
            ):
                continue
            if child.is_symlink():
                digest.update(b"SYMLINK\0" + relative.as_posix().encode() + b"\0")
                digest.update(os.readlink(child).encode())
            elif child.is_dir():
                if not any(child.iterdir()):
                    digest.update(b"EMPTY_DIRECTORY\0" + relative.as_posix().encode() + b"\0")
            elif child.is_file():
                digest.update(relative.as_posix().encode())
                digest.update(b"\0")
                digest.update(child.read_bytes())
            else:
                digest.update(b"SPECIAL\0" + relative.as_posix().encode())
    else:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _installation_layout(
    runtime: Runtime,
    scope: InstallScope,
    target: Path,
) -> tuple[dict[str, Path], Path]:
    if scope is InstallScope.PROJECT:
        trusted_root = _absolute_lexical(target)
        return _runtime_directories(runtime, trusted_root), trusted_root

    if runtime is Runtime.OPENCODE:
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            trusted_root = _absolute_lexical(Path(config_home))
            base = trusted_root / "opencode"
            return {"skills": base / "skills", "agents": base / "agents"}, trusted_root

        trusted_root = _absolute_lexical(Path.home())
        base = trusted_root / ".config" / "opencode"
        return (
            {"skills": base / "skills", "agents": base / "agents"},
            trusted_root,
        )
    trusted_root = _absolute_lexical(Path.home())
    if runtime is Runtime.PI:
        base = trusted_root / ".pi" / "agent"
        return {"skills": base / "skills", "agents": base / "agents"}, trusted_root
    return _runtime_directories(runtime, trusted_root), trusted_root


def _runtime_directories(runtime: Runtime, base: Path) -> dict[str, Path]:
    if runtime is Runtime.CLAUDE:
        return {
            "skills": base / ".claude" / "skills",
            "agents": base / ".claude" / "agents",
            "commands": base / ".claude" / "commands",
        }
    if runtime is Runtime.CODEX:
        return {"skills": base / ".agents" / "skills", "agents": base / ".codex" / "agents"}
    if runtime is Runtime.OPENCODE:
        return {"skills": base / ".opencode" / "skills", "agents": base / ".opencode" / "agents"}
    return {"skills": base / ".pi" / "skills", "agents": base / ".pi" / "agents"}


def _agent_directory(runtime: Runtime) -> str | None:
    if runtime is Runtime.CLAUDE:
        return "agents"
    if runtime is Runtime.CODEX:
        return ".codex/agents"
    if runtime is Runtime.OPENCODE:
        return ".opencode/agents"
    if runtime is Runtime.PI:
        return "pi-agents"
    return None


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


def _mcp_configuration_actions(
    catalog: AssetCatalog,
    runtime: Runtime,
    scope: InstallScope,
    trusted_root: Path,
) -> tuple[InstallAction, ...]:
    if scope is not InstallScope.PROJECT or runtime is Runtime.PI:
        return ()
    source_id, relative = {
        Runtime.CLAUDE: (".mcp.json", ".mcp.json"),
        Runtime.CODEX: (".codex/config.toml", ".codex/config.toml"),
        Runtime.OPENCODE: ("opencode.json", "opencode.json"),
    }[runtime]
    source = catalog.path(source_id)
    destination = trusted_root / relative
    manifest = (
        destination.parent / ".waterology-install.json"
        if runtime is Runtime.CODEX
        else trusted_root / f".waterology-{runtime.value}-install.json"
    )
    return (
        InstallAction(
            source=source,
            source_id=source_id,
            destination=destination,
            operation=InstallMode.COPY.value,
            manifest=manifest,
        ),
    )


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
