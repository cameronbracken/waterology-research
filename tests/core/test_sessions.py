import json
import subprocess
from pathlib import Path

import pytest

from waterology.core.database import open_database
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.sessions import (
    SessionConflictError,
    add_session_note,
    create_session,
    list_session_notes,
    list_sessions,
    load_session,
    persist_session,
    read_session_logs,
    transition_session,
)


def make_experiment(path: Path, experiment_id: str = "exp-agent") -> tuple[Path, str]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    (path / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(path), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "base"], check=True)
    experiment = create_experiment(
        path,
        hypothesis="An agent can test this variant.",
        experiment_id=experiment_id,
    )
    return path, experiment.id


def test_create_session_writes_durable_record_and_acquires_worktree(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")

    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="researcher",
        task="Measure the baseline and record the result.",
        compute_profile="local",
        session_id="session-0123456789abcdef",
    )

    assert session.state == "created"
    assert session.runtime == "codex"
    assert session.attempts == ()
    session_directory = root / ".waterology" / "sessions" / session.id
    assert (session_directory / "task.md").read_text(encoding="utf-8").endswith("result.\n")
    assert json.loads((session_directory / "session.json").read_text(encoding="utf-8"))["id"] == (
        session.id
    )
    assert load_session(root, session.id) == session
    assert list_sessions(root) == (session,)

    with open_database(root / ".waterology" / "state.sqlite") as database:
        indexed = database.connection.execute(
            "SELECT id, state, worktree FROM sessions WHERE id = ?", (session.id,)
        ).fetchone()
    assert tuple(indexed) == (session.id, "created", session.worktree)


def test_only_one_active_session_can_own_a_worktree(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    owner = create_session(
        root,
        experiment_id=experiment_id,
        runtime="claude",
        role="researcher",
        task="Own this worktree.",
        session_id="session-1111111111111111",
    )

    with pytest.raises(SessionConflictError, match=owner.id):
        create_session(
            root,
            experiment_id=experiment_id,
            runtime="opencode",
            role="writer",
            task="Try to share this worktree.",
            session_id="session-2222222222222222",
        )

    assert not (root / ".waterology" / "sessions" / "session-2222222222222222").exists()


def test_terminal_session_releases_worktree_ownership(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    first = create_session(
        root,
        experiment_id=experiment_id,
        runtime="claude",
        role="researcher",
        task="Finish this task.",
        session_id="session-3333333333333333",
    )
    transition_session(root, first.id, state="failed", exit_code=1)

    second = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="reviewer",
        task="Continue after the failure.",
        session_id="session-4444444444444444",
    )

    assert second.state == "created"


def test_persist_session_rejects_a_stale_compare_and_swap(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    initial = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="researcher",
        task="Guard concurrent updates.",
        session_id="session-aaaaaaaaaaaaaaaa",
    )
    first = initial.model_copy(update={"state": "running", "updated_at": "2026-08-25T01:00:00Z"})
    stale = initial.model_copy(update={"state": "failed", "updated_at": "2026-08-25T01:00:01Z"})

    persist_session(root, first, expected_updated_at=initial.updated_at)

    with pytest.raises(SessionConflictError, match="changed"):
        persist_session(root, stale, expected_updated_at=initial.updated_at)

    assert load_session(root, initial.id) == first


def test_session_write_does_not_follow_a_precreated_staging_symlink(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="researcher",
        task="Use unique staging files.",
        session_id="session-bbbbbbbbbbbbbbbb",
    )
    outside = tmp_path / "outside.json"
    outside.write_text("private\n", encoding="utf-8")
    legacy_staging = root / ".waterology" / "sessions" / session.id / ".session.json.tmp"
    legacy_staging.symlink_to(outside)

    transition_session(root, session.id, state="failed", exit_code=1)

    assert outside.read_text(encoding="utf-8") == "private\n"
    assert legacy_staging.is_symlink()


def test_load_session_rejects_record_identifier_that_does_not_match_directory(
    tmp_path: Path,
) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="researcher",
        task="Validate live identity.",
        session_id="session-cccccccccccccccc",
    )
    record = root / ".waterology" / "sessions" / session.id / "session.json"
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload["id"] = "session-dddddddddddddddd"
    record.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(SessionConflictError, match="identifier does not match"):
        load_session(root, session.id)


def test_session_notes_are_append_only_durable_records(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="opencode",
        role="researcher",
        task="Keep notes.",
        session_id="session-5555555555555555",
    )

    first = add_session_note(root, session.id, "Found a useful comparison.", author="cam")
    second = add_session_note(root, session.id, "Need one more run.", author="cam")

    assert list_session_notes(root, session.id) == (first, second)
    assert first.id != second.id


@pytest.mark.parametrize("runtime", ["shell", "", "Claude"])
def test_create_session_rejects_unknown_runtime(tmp_path: Path, runtime: str) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")

    with pytest.raises(ValueError):
        create_session(
            root,
            experiment_id=experiment_id,
            runtime=runtime,
            role="researcher",
            task="Reject this runtime.",
        )


def test_create_session_rejects_blank_task_before_creating_state(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")

    with pytest.raises(ValueError, match="task must not be blank"):
        create_session(
            root,
            experiment_id=experiment_id,
            runtime="codex",
            role="researcher",
            task="  ",
        )

    assert list((root / ".waterology" / "sessions").iterdir()) == []


def test_create_session_rejects_symlinked_experiment_worktree(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    outside = tmp_path / "outside-worktree"
    worktree.rename(outside)
    worktree.symlink_to(outside, target_is_directory=True)

    with pytest.raises(SessionConflictError, match="unavailable"):
        create_session(
            root,
            experiment_id=experiment_id,
            runtime="codex",
            role="researcher",
            task="Reject the linked worktree.",
        )


def test_read_session_logs_rejects_symlinked_log_file(tmp_path: Path) -> None:
    from waterology.agents.supervisor import begin_attempt

    root, experiment_id = make_experiment(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="researcher",
        task="Keep the log local.",
        session_id="session-6666666666666666",
    )
    session = begin_attempt(root, session.id, prompt="Start logging.")
    events = root / session.attempts[-1].events_path
    outside = tmp_path / "outside.log"
    outside.write_text("private\n", encoding="utf-8")
    events.unlink()
    events.symlink_to(outside)

    with pytest.raises(SessionConflictError, match="session file"):
        read_session_logs(root, session.id)

    assert outside.read_text(encoding="utf-8") == "private\n"


def test_add_session_note_rejects_symlinked_notes_directory(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="researcher",
        task="Keep notes local.",
        session_id="session-7777777777777777",
    )
    outside = tmp_path / "outside-notes"
    outside.mkdir()
    notes = root / ".waterology" / "sessions" / session.id / "notes"
    notes.symlink_to(outside, target_is_directory=True)

    with pytest.raises(SessionConflictError, match="notes directory"):
        add_session_note(root, session.id, "Do not write this outside.")

    assert list(outside.iterdir()) == []
