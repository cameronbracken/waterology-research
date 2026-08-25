import subprocess
from dataclasses import dataclass
from pathlib import Path

from waterology.core.config import (
    ProjectConfig,
    default_project_config,
    load_project_config,
    project_config_toml,
)
from waterology.core.errors import WaterologyError

_STATE_DIRECTORIES = ("assessments", "experiments", "runs", "staging", "worktrees")


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
    experiments: Path
    runs: Path
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
        experiments=state / "experiments",
        runs=state / "runs",
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

    paths.state.mkdir(exist_ok=True)
    for directory in _STATE_DIRECTORIES:
        (paths.state / directory).mkdir(exist_ok=True)
    for artifact_root in config.artifact_roots:
        (root / artifact_root).mkdir(parents=True, exist_ok=True)

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
    for candidate in (current, *current.parents):
        paths = project_paths(candidate)
        if paths.config_file.is_file():
            return Project(candidate, load_project_config(paths.config_file), paths)
    raise ProjectNotFoundError(f"No waterology.toml found from {start}")


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


def _record_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for child in path.iterdir() if child.name != ".DS_Store")


def _assessment_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for child in path.glob("run-*/assessment-*.json") if child.is_file())
