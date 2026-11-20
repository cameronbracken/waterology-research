"""Workspace and local reference state helpers without requiring waterology.toml."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from waterology.core.atomic import exclusive_file_lock, write_text

ZOTERO_SETTINGS_NAME = ".zotero.toml"
STATE_DIR_NAME = ".waterology"


def portable_project_path(raw: str) -> Path:
    cleaned = raw.strip()
    if not cleaned or "\x00" in cleaned or "\\" in cleaned:
        raise ValueError("Path must be a non-empty forward-slash relative path")
    pure = PurePosixPath(cleaned)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("Path must stay within the workspace")
    return Path(*pure.parts)


def find_zotero_root(start: Path) -> Path | None:
    """Find the nearest directory with .zotero.toml, refusing symlinked settings."""
    if start.is_symlink():
        raise ValueError("Workspace path must not be a symlink")
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        settings = candidate / ZOTERO_SETTINGS_NAME
        if settings.is_symlink():
            raise ValueError("Zotero settings must not be a symlink")
        if settings.is_file():
            return candidate
    return None


def find_recorded_literature_root(start: Path) -> Path | None:
    """Return a workspace root when .zotero.toml or .waterology/literature already exists."""
    zotero_root = find_zotero_root(start)
    if zotero_root is not None:
        return zotero_root
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        lit_dir = candidate / STATE_DIR_NAME / "literature"
        if lit_dir.is_symlink():
            raise ValueError("Literature directory must not be a symlink")
        if lit_dir.is_dir():
            return candidate
        if (candidate / ".git").exists():
            break
    return None


def resolve_workspace_root(start: Path) -> Path:
    """Resolve workspace root from .zotero.toml, nearest .git root, or start directory."""
    zotero_root = find_zotero_root(start)
    if zotero_root is not None:
        return zotero_root
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def state_directory(root: Path, subdir: str) -> Path:
    base = root / STATE_DIR_NAME
    if base.is_symlink():
        raise ValueError(f"{STATE_DIR_NAME} must not be a symlink")
    base.mkdir(exist_ok=True)
    target = base / subdir
    if target.is_symlink():
        raise ValueError(f"{subdir} state directory must not be a symlink")
    target.mkdir(exist_ok=True)
    return target


@contextmanager
def workspace_state_lock(root: Path) -> Iterator[None]:
    base = root / STATE_DIR_NAME
    if base.is_symlink():
        raise ValueError(f"{STATE_DIR_NAME} must not be a symlink")
    base.mkdir(exist_ok=True)
    with exclusive_file_lock(base / ".state.lock"):
        yield


def ensure_gitignore_state(root: Path) -> bool:
    """Ensure .waterology/ is ignored when root is a Git repository."""
    if not (root / ".git").exists():
        return False
    gitignore = root / ".gitignore"
    if gitignore.is_symlink():
        raise ValueError(".gitignore must not be a symlink")
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    entries = {line.strip().rstrip("/") for line in existing.splitlines() if line.strip()}
    if STATE_DIR_NAME in entries:
        return False
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    write_text(gitignore, f"{existing}{prefix}{STATE_DIR_NAME}/\n")
    return True
