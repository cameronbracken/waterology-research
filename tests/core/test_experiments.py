import json
import subprocess
from pathlib import Path

import pytest

from waterology.core.database import open_database
from waterology.core.experiments import (
    ExperimentConflictError,
    add_experiment_note,
    create_experiment,
    list_experiment_notes,
    list_experiments,
    load_experiment,
)
from waterology.core.project import initialize_project


def make_committed_project(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Researcher"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    (path / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(path), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "Add baseline"], check=True)
    return path


def git(path: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_create_experiment_adds_worktree_durable_record_and_index(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    base_commit = git(root, "rev-parse", "HEAD")

    experiment = create_experiment(
        root,
        hypothesis="A longer calibration window reduces RMSE.",
        owner="cam",
        experiment_id="exp-calibration",
    )

    assert experiment.id == "exp-calibration"
    assert experiment.base_commit == base_commit
    assert experiment.branch == "waterology/exp-calibration"
    assert experiment.status == "provisional"
    worktree = root / experiment.worktree
    assert worktree.is_dir()
    assert git(worktree, "branch", "--show-current") == experiment.branch
    record_path = root / ".waterology" / "experiments" / experiment.id / "experiment.json"
    assert json.loads(record_path.read_text(encoding="utf-8"))["hypothesis"] == (
        "A longer calibration window reduces RMSE."
    )

    with open_database(root / ".waterology" / "state.sqlite") as database:
        indexed = database.connection.execute(
            "SELECT id, base_commit, owner FROM experiments WHERE id = ?",
            (experiment.id,),
        ).fetchone()
        events = database.list_events()

    assert tuple(indexed) == (experiment.id, base_commit, "cam")
    assert [event.phase for event in events] == ["intent", "observation"]
    assert events[-1].payload == {"outcome": "created"}


def test_list_and_load_experiments_use_durable_records(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    created = create_experiment(
        root,
        hypothesis="Test the first variant.",
        experiment_id="exp-first",
    )
    (root / ".waterology" / "state.sqlite").unlink()

    listed = list_experiments(root)
    loaded = load_experiment(root, created.id)

    assert listed == (created,)
    assert loaded == created


def test_create_experiment_refuses_branch_collision_without_changing_it(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    git(root, "branch", "waterology/exp-existing")
    before = git(root, "rev-parse", "waterology/exp-existing")

    with pytest.raises(ExperimentConflictError, match="branch already exists"):
        create_experiment(
            root,
            hypothesis="Do not overwrite this branch.",
            experiment_id="exp-existing",
        )

    assert git(root, "rev-parse", "waterology/exp-existing") == before
    assert not (root / ".waterology" / "worktrees" / "exp-existing").exists()


def test_create_experiment_rejects_invalid_identifier(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")

    with pytest.raises(ValueError, match="experiment identifier"):
        create_experiment(root, hypothesis="Invalid ID.", experiment_id="../escape")


def test_create_experiment_requires_committed_project_configuration(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    (root / "waterology.toml").write_text(
        (root / "waterology.toml").read_text(encoding="utf-8") + "# changed\n",
        encoding="utf-8",
    )
    git(root, "rm", "--cached", "waterology.toml")
    git(root, "commit", "--quiet", "-m", "Stop tracking project configuration")

    with pytest.raises(ExperimentConflictError, match="must contain waterology.toml"):
        create_experiment(
            root,
            hypothesis="This worktree would not be configured.",
            experiment_id="exp-unconfigured",
        )


def test_experiment_notes_are_append_only_durable_records(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    experiment = create_experiment(
        root,
        hypothesis="Test a documented observation.",
        experiment_id="exp-notes",
    )

    first = add_experiment_note(root, experiment.id, "First observation.", author="cam")
    second = add_experiment_note(root, experiment.id, "Second observation.", author="cam")

    notes = list_experiment_notes(root, experiment.id)
    assert notes == (first, second)
    assert first.id != second.id
    assert first.text == "First observation."
    note_files = list(
        (root / ".waterology" / "experiments" / experiment.id / "notes").glob("*.json")
    )
    assert len(note_files) == 2


def test_child_experiment_requires_an_existing_frozen_parent(tmp_path: Path) -> None:
    root = make_committed_project(tmp_path / "study")
    parent = create_experiment(
        root,
        hypothesis="Parent remains provisional.",
        experiment_id="exp-parent",
    )

    with pytest.raises(ExperimentConflictError, match="must be frozen"):
        create_experiment(
            root,
            hypothesis="Do not branch from provisional work.",
            parent_experiment_id=parent.id,
            experiment_id="exp-child",
        )

    assert not (root / ".waterology" / "worktrees" / "exp-child").exists()
