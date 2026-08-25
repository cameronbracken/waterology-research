import subprocess
from pathlib import Path

import pytest

from waterology.core.project import (
    ProjectNotFoundError,
    discover_project,
    initialize_project,
    inspect_project,
)


def make_git_repository(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    return path


def test_initialize_project_writes_portable_layout(tmp_path: Path) -> None:
    root = make_git_repository(tmp_path / "river-study")

    result = initialize_project(root)

    assert result.created_config is True
    assert result.updated_gitignore is True
    assert (
        (root / "waterology.toml")
        .read_text(encoding="utf-8")
        .startswith('schema_version = 1\nname = "river-study"\n')
    )
    assert (root / ".gitignore").read_text(encoding="utf-8") == ".waterology/\n"
    assert (root / "artifacts").is_dir()
    assert (root / ".waterology" / "experiments").is_dir()
    assert (root / ".waterology" / "runs").is_dir()
    assert (root / ".waterology" / "assessments").is_dir()
    assert (root / ".waterology" / "staging").is_dir()
    assert (root / ".waterology" / "worktrees").is_dir()


def test_initialize_project_is_idempotent_and_preserves_gitignore(tmp_path: Path) -> None:
    root = make_git_repository(tmp_path / "study")
    gitignore = root / ".gitignore"
    gitignore.write_text("*.log", encoding="utf-8")

    first = initialize_project(root, name="named-study")
    config_before = (root / "waterology.toml").read_bytes()
    second = initialize_project(root, name="ignored-on-repeat")

    assert first.created_config is True
    assert second.created_config is False
    assert second.updated_gitignore is False
    assert (root / "waterology.toml").read_bytes() == config_before
    assert gitignore.read_text(encoding="utf-8") == "*.log\n.waterology/\n"


def test_initialize_from_subdirectory_uses_git_root(tmp_path: Path) -> None:
    root = make_git_repository(tmp_path / "study")
    nested = root / "analysis" / "scripts"
    nested.mkdir(parents=True)

    result = initialize_project(nested)

    assert result.project.root == root.resolve()
    assert not (nested / "waterology.toml").exists()


def test_discover_project_walks_from_a_nested_path(tmp_path: Path) -> None:
    root = make_git_repository(tmp_path / "study")
    initialize_project(root)
    nested = root / "analysis" / "scripts"
    nested.mkdir(parents=True)

    project = discover_project(nested)

    assert project.root == root.resolve()
    assert project.config.name == "study"


def test_discover_project_reports_missing_configuration(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError, match="waterology.toml"):
        discover_project(tmp_path)


def test_project_status_counts_assessment_records_not_run_directories(tmp_path: Path) -> None:
    root = make_git_repository(tmp_path / "study")
    initialize_project(root)
    assessments = root / ".waterology" / "assessments" / "run-one"
    assessments.mkdir()
    (assessments / "assessment-one.json").write_text("{}\n", encoding="utf-8")
    (assessments / "assessment-two.json").write_text("{}\n", encoding="utf-8")

    status = inspect_project(root)

    assert status.assessments == 2
