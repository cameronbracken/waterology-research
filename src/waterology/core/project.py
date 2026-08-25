import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from waterology.core.atomic import exclusive_file_lock
from waterology.core.config import (
    ProjectConfig,
    default_project_config,
    load_project_config,
    project_config_toml,
)
from waterology.core.errors import WaterologyError

_STATE_DIRECTORIES = (
    "assessments",
    "evidence",
    "experiments",
    "runs",
    "sessions",
    "staging",
    "worktrees",
)
_SLICE_FIVE_DIRECTORIES = ("evidence", "sessions")


class ProjectNotFoundError(WaterologyError):
    """Raised when a path is not inside an initialized Waterology project."""

    code = "project_not_found"


class ProjectInitializationError(WaterologyError):
    """Raised when a project cannot be initialized safely."""

    code = "project_initialization_failed"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    config_file: Path
    state: Path
    database: Path
    assessments: Path
    evidence: Path
    experiments: Path
    runs: Path
    sessions: Path
    staging: Path
    worktrees: Path


@dataclass(frozen=True)
class Project:
    root: Path
    config: ProjectConfig
    paths: ProjectPaths


@dataclass(frozen=True)
class InitializationResult:
    project: Project
    created_config: bool
    updated_gitignore: bool


@dataclass(frozen=True)
class ProjectStatus:
    project: Project
    database_exists: bool
    experiments: int
    runs: int
    assessments: int


def project_paths(root: Path) -> ProjectPaths:
    root = root.resolve()
    state = root / ".waterology"
    return ProjectPaths(
        root=root,
        config_file=root / "waterology.toml",
        state=state,
        database=state / "state.sqlite",
        assessments=state / "assessments",
        evidence=state / "evidence",
        experiments=state / "experiments",
        runs=state / "runs",
        sessions=state / "sessions",
        staging=state / "staging",
        worktrees=state / "worktrees",
    )


def initialize_project(start: Path, name: str | None = None) -> InitializationResult:
    root = _git_root(start)
    paths = project_paths(root)
    created_config = not paths.config_file.exists()
    if created_config:
        config = default_project_config(name or root.name)
        paths.config_file.write_text(project_config_toml(config), encoding="utf-8")
    else:
        config = load_project_config(paths.config_file)

    _ensure_state_directory(paths.state, paths.root)
    for directory in _STATE_DIRECTORIES:
        _ensure_state_directory(paths.state / directory, paths.root)
    for artifact_root in config.artifact_roots:
        _ensure_project_directory(root / artifact_root, root)

    updated_gitignore = _ensure_state_is_ignored(root / ".gitignore")
    return InitializationResult(
        project=Project(root, config, paths),
        created_config=created_config,
        updated_gitignore=updated_gitignore,
    )


def discover_project(start: Path) -> Project:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    configured_path = None
    for candidate in (current, *current.parents):
        paths = project_paths(candidate)
        if paths.config_file.is_file():
            configured_path = configured_path or candidate
            if paths.state.is_dir():
                project = Project(candidate, load_project_config(paths.config_file), paths)
                _validate_state_directory(paths.state, project.root)
                for directory in _SLICE_FIVE_DIRECTORIES:
                    added = paths.state / directory
                    if added.exists() or added.is_symlink():
                        _validate_state_directory(added, project.root)
                    else:
                        _ensure_state_directory(added, project.root)
                validate_project_state(project)
                return project
    if configured_path is not None:
        raise ProjectInitializationError(
            f"Waterology local state is not initialized: {configured_path}"
        )
    raise ProjectNotFoundError(f"No waterology.toml found from {start}")


def validate_project_state(project: Project) -> None:
    _validate_state_directory(project.paths.state, project.root)
    for directory in _STATE_DIRECTORIES:
        _validate_state_directory(project.paths.state / directory, project.root)


@contextmanager
def project_state_lock(start: Path) -> Iterator[None]:
    project = discover_project(start)
    lock_path = project.paths.state / ".project.lock"
    if lock_path.is_symlink():
        raise ProjectInitializationError(f"Local state lock must not be a symlink: {lock_path}")
    with exclusive_file_lock(lock_path):
        yield


def inspect_project(start: Path) -> ProjectStatus:
    project = discover_project(start)
    return ProjectStatus(
        project=project,
        database_exists=project.paths.database.is_file(),
        experiments=_record_count(project.paths.experiments),
        runs=_record_count(project.paths.runs),
        assessments=_assessment_count(project.paths.assessments),
    )


def _git_root(start: Path) -> Path:
    candidate = start.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    completed = subprocess.run(
        ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or "path is not inside a Git repository"
        raise ProjectInitializationError(message)
    return Path(completed.stdout.strip()).resolve()


def _ensure_state_is_ignored(path: Path) -> bool:
    entry = ".waterology/"
    if path.exists():
        original = path.read_text(encoding="utf-8")
        if any(line.strip() == entry for line in original.splitlines()):
            return False
        prefix = original if not original or original.endswith("\n") else original + "\n"
    else:
        prefix = ""
    path.write_text(prefix + entry + "\n", encoding="utf-8")
    return True


def _ensure_state_directory(path: Path, root: Path) -> None:
    if path.is_symlink():
        raise ProjectInitializationError(f"Local state path must not be a symlink: {path}")
    path.mkdir(exist_ok=True)
    _validate_state_directory(path, root)


def _ensure_project_directory(path: Path, root: Path) -> None:
    if path.is_symlink():
        raise ProjectInitializationError(f"Project directory must not be a symlink: {path}")
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ProjectInitializationError(
            f"Project directory escapes the project: {path}"
        ) from error


def _validate_state_directory(path: Path, root: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ProjectInitializationError(f"Invalid local state directory: {path}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ProjectInitializationError(f"Local state escapes the project: {path}") from error


def _record_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for child in path.iterdir() if child.name != ".DS_Store")


def _assessment_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for child in path.glob("run-*/assessment-*.json") if child.is_file())
