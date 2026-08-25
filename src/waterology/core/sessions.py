import json
import re
import shutil
import sqlite3
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from waterology.core.atomic import exclusive_file_lock, write_json
from waterology.core.database import Database, open_database
from waterology.core.errors import WaterologyError
from waterology.core.experiments import ensure_experiment_index, load_experiment
from waterology.core.project import Project, discover_project, project_state_lock
from waterology.core.records import AgentSessionRecord, SessionNoteRecord, SessionState

_SESSION_ID = re.compile(r"^session-[0-9a-f]{16}$")
_TERMINAL_STATES = frozenset({"completed", "failed", "cancelled", "lost"})
_TRANSITIONS: dict[str, frozenset[str]] = {
    "created": frozenset({"running", "failed", "cancelled", "lost"}),
    "running": frozenset({"waiting", "completed", "failed", "cancelled", "lost"}),
    "waiting": frozenset({"running", "completed", "failed", "cancelled", "lost"}),
    "completed": frozenset({"running"}),
    "failed": frozenset({"running"}),
    "cancelled": frozenset({"running"}),
    "lost": frozenset({"running"}),
}


class SessionConflictError(WaterologyError):
    code = "session_conflict"


class SessionNotFoundError(WaterologyError):
    code = "session_not_found"


class SessionStateError(WaterologyError):
    code = "session_state_invalid"


def create_session(
    start: Path,
    *,
    experiment_id: str,
    runtime: str,
    role: str,
    task: str,
    compute_profile: str = "local",
    session_id: str | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    with project_state_lock(project.root):
        return _create_session_locked(
            project.root,
            experiment_id=experiment_id,
            runtime=runtime,
            role=role,
            task=task,
            compute_profile=compute_profile,
            session_id=session_id,
        )


def _create_session_locked(
    start: Path,
    *,
    experiment_id: str,
    runtime: str,
    role: str,
    task: str,
    compute_profile: str = "local",
    session_id: str | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    identifier = session_id or f"session-{uuid4().hex[:16]}"
    _validate_session_id(identifier)
    task = task.strip()
    if not task:
        raise ValueError("task must not be blank")
    worktree = _resolve_worktree(project, experiment.worktree)
    if not worktree.is_dir() or worktree.is_symlink():
        raise SessionConflictError(f"Experiment worktree is unavailable: {experiment.id}")
    now = _utc_now()
    record = AgentSessionRecord(
        id=identifier,
        project_id=project.config.name,
        experiment_id=experiment.id,
        runtime=runtime,
        role=role,
        compute_profile=compute_profile,
        worktree=experiment.worktree,
        task_path=f".waterology/sessions/{identifier}/task.md",
        initial_commit=_git_commit(worktree),
        created_at=now,
        updated_at=now,
    )
    directory = project.paths.sessions / identifier
    if directory.exists() or directory.is_symlink():
        raise SessionConflictError(f"Session path already exists: {identifier}")

    with open_database(project.paths.database) as database:
        ensure_experiment_index(database, project, experiment)
        intent = database.append_intent(
            kind="session.create",
            entity_type="session",
            entity_id=identifier,
            payload={"experiment_id": experiment.id, "runtime": record.runtime},
        )
        try:
            _insert_session(database, record)
            directory.mkdir()
            (directory / "task.md").write_text(task + "\n", encoding="utf-8")
            _write_session(directory / "session.json", record)
        except sqlite3.IntegrityError as error:
            owner = _active_owner(database, experiment.worktree)
            database.append_observation(
                intent.id,
                payload={"error": type(error).__name__, "outcome": "failed"},
            )
            raise SessionConflictError(
                f"Worktree is already owned by active session {owner or 'unknown'}",
                details={"owner_session_id": owner, "worktree": experiment.worktree},
            ) from error
        except BaseException as error:
            if directory.is_dir() and not directory.is_symlink():
                shutil.rmtree(directory)
            with database.connection:
                database.connection.execute("DELETE FROM sessions WHERE id = ?", (identifier,))
            database.append_observation(
                intent.id,
                payload={"error": type(error).__name__, "outcome": "failed"},
            )
            raise
        database.append_observation(intent.id, payload={"outcome": "created"})
    return record


def load_session(start: Path, session_id: str) -> AgentSessionRecord:
    _validate_session_id(session_id)
    project = discover_project(start)
    path = project.paths.sessions / session_id / "session.json"
    if path.parent.is_symlink() or path.is_symlink() or not path.is_file():
        raise SessionNotFoundError(f"Session does not exist: {session_id}")
    try:
        record = AgentSessionRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise ValueError(f"Invalid session record: {path}") from error
    _validate_loaded_session(project, record, expected_id=session_id)
    return record


def list_sessions(start: Path) -> tuple[AgentSessionRecord, ...]:
    project = discover_project(start)
    records = []
    for path in project.paths.sessions.glob("session-*/session.json"):
        if path.parent.is_symlink() or path.is_symlink():
            raise ValueError(f"Invalid session record path: {path}")
        try:
            record = AgentSessionRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            raise ValueError(f"Invalid session record: {path}") from error
        _validate_loaded_session(project, record, expected_id=path.parent.name)
        records.append(record)
    return tuple(sorted(records, key=lambda record: (record.created_at, record.id)))


def transition_session(
    start: Path,
    session_id: str,
    *,
    state: SessionState,
    native_session_id: str | None = None,
    supervisor_pid: int | None = None,
    process_pid: int | None = None,
    exit_code: int | None = None,
    resulting_commits: tuple[str, ...] | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    with project_state_lock(project.root), session_lock(project.root, session_id):
        return _transition_session_locked(
            project.root,
            session_id,
            state=state,
            native_session_id=native_session_id,
            supervisor_pid=supervisor_pid,
            process_pid=process_pid,
            exit_code=exit_code,
            resulting_commits=resulting_commits,
        )


def _transition_session_locked(
    start: Path,
    session_id: str,
    *,
    state: SessionState,
    native_session_id: str | None = None,
    supervisor_pid: int | None = None,
    process_pid: int | None = None,
    exit_code: int | None = None,
    resulting_commits: tuple[str, ...] | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    current = load_session(project.root, session_id)
    if state != current.state and state not in _TRANSITIONS[current.state]:
        raise SessionStateError(f"Cannot change session from {current.state} to {state}")
    now = _utc_now()
    updated = AgentSessionRecord.model_validate(
        current.model_copy(
            update={
                "state": state,
                "native_session_id": native_session_id or current.native_session_id,
                "supervisor_pid": supervisor_pid,
                "process_pid": process_pid,
                "exit_code": exit_code,
                "resulting_commits": (
                    resulting_commits
                    if resulting_commits is not None
                    else current.resulting_commits
                ),
                "updated_at": now,
                "finished_at": now if state in _TERMINAL_STATES else None,
            }
        ).model_dump()
    )
    with open_database(project.paths.database) as database:
        intent = database.append_intent(
            kind="session.transition",
            entity_type="session",
            entity_id=session_id,
            payload={"from": current.state, "to": state},
        )
    try:
        result = persist_session_locked(
            project.root,
            updated,
            expected_updated_at=current.updated_at,
        )
    except BaseException as error:
        with open_database(project.paths.database) as database:
            database.append_observation(
                intent.id,
                payload={"error": type(error).__name__, "outcome": "failed"},
            )
        raise
    with open_database(project.paths.database) as database:
        database.append_observation(intent.id, payload={"outcome": "updated", "state": state})
    return result


def add_session_note(
    start: Path,
    session_id: str,
    text: str,
    *,
    author: str | None = None,
) -> SessionNoteRecord:
    project = discover_project(start)
    with project_state_lock(project.root):
        return _add_session_note_locked(project.root, session_id, text, author=author)


def _add_session_note_locked(
    start: Path,
    session_id: str,
    text: str,
    *,
    author: str | None = None,
) -> SessionNoteRecord:
    project = discover_project(start)
    load_session(project.root, session_id)
    stripped = text.strip()
    if not stripped:
        raise ValueError("session note must not be blank")
    note = SessionNoteRecord(
        id=f"note-{uuid4().hex[:16]}",
        session_id=session_id,
        text=stripped,
        author=author.strip() if author else None,
        created_at=_utc_now(),
    )
    directory = project.paths.sessions / session_id / "notes"
    if directory.is_symlink():
        raise SessionConflictError(f"Invalid symlinked session notes directory: {session_id}")
    directory.mkdir(exist_ok=True)
    destination = directory / f"{note.id}.json"
    _write_json(destination, note.model_dump(mode="json"))
    try:
        with open_database(project.paths.database) as database, database.connection:
            database.connection.execute(
                """
                INSERT INTO session_notes (id, session_id, text, author, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (note.id, note.session_id, note.text, note.author, note.created_at),
            )
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return note


def list_session_notes(start: Path, session_id: str) -> tuple[SessionNoteRecord, ...]:
    project = discover_project(start)
    load_session(project.root, session_id)
    directory = project.paths.sessions / session_id / "notes"
    if directory.is_symlink():
        raise SessionConflictError(f"Invalid symlinked session notes directory: {session_id}")
    if not directory.is_dir():
        return ()
    notes = []
    for path in directory.glob("note-*.json"):
        if path.is_symlink():
            raise SessionConflictError(f"Invalid symlinked session note: {path.name}")
        try:
            notes.append(SessionNoteRecord.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValidationError) as error:
            raise ValueError(f"Invalid session note record: {path}") from error
    return tuple(sorted(notes, key=lambda note: (note.created_at, note.id)))


def read_session_logs(start: Path, session_id: str) -> tuple[dict[str, object], ...]:
    project = discover_project(start)
    session = load_session(project.root, session_id)
    logs = []
    for attempt in session.attempts:
        events_path = resolve_session_file(project.root, session.id, attempt.events_path)
        stderr_path = resolve_session_file(project.root, session.id, attempt.stderr_path)
        logs.append(
            {
                "attempt": attempt.number,
                "events": events_path.read_text(encoding="utf-8"),
                "stderr": stderr_path.read_text(encoding="utf-8"),
            }
        )
    return tuple(logs)


def resolve_session_file(start: Path, session_id: str, relative: str) -> Path:
    project = discover_project(start)
    _validate_session_id(session_id)
    candidate = project.root / relative
    directory = project.paths.sessions / session_id
    try:
        candidate.relative_to(directory)
    except ValueError as error:
        raise SessionConflictError(f"Invalid session file path: {relative}") from error
    current = project.root
    for part in candidate.relative_to(project.root).parts:
        current /= part
        if current.is_symlink():
            raise SessionConflictError(f"Invalid symlinked session file: {relative}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(directory.resolve())
    except ValueError as error:
        raise SessionConflictError(f"Invalid session file path: {relative}") from error
    if not resolved.is_file():
        raise SessionConflictError(f"Missing session file: {relative}")
    return resolved


def resolve_optional_session_file(start: Path, session_id: str, relative: str) -> Path | None:
    project = discover_project(start)
    candidate = project.root / relative
    if not candidate.exists() and not candidate.is_symlink():
        return None
    return resolve_session_file(project.root, session_id, relative)


def _validate_loaded_session(
    project: Project,
    record: AgentSessionRecord,
    *,
    expected_id: str,
) -> None:
    if record.id != expected_id:
        raise SessionConflictError(f"Session record identifier does not match path: {expected_id}")
    if record.project_id != project.config.name:
        raise SessionConflictError(f"Session project does not match configuration: {record.id}")
    experiment = load_experiment(project.root, record.experiment_id)
    if record.worktree != experiment.worktree:
        raise SessionConflictError(f"Session worktree does not match experiment: {record.id}")
    prefix = f".waterology/sessions/{record.id}"
    if record.task_path != f"{prefix}/task.md":
        raise SessionConflictError(f"Session task path does not match layout: {record.id}")
    resolve_session_file(project.root, record.id, record.task_path)
    for expected_number, attempt in enumerate(record.attempts, start=1):
        attempt_prefix = f"{prefix}/attempt-{expected_number:03d}"
        if attempt.number != expected_number or (
            attempt.prompt_path,
            attempt.events_path,
            attempt.stderr_path,
        ) != (
            f"{attempt_prefix}/prompt.md",
            f"{attempt_prefix}/events.jsonl",
            f"{attempt_prefix}/stderr.log",
        ):
            raise SessionConflictError(f"Session attempt path does not match layout: {record.id}")
        resolve_session_file(project.root, record.id, attempt.prompt_path)
        resolve_session_file(project.root, record.id, attempt.events_path)
        resolve_session_file(project.root, record.id, attempt.stderr_path)


def ensure_session_index(database: Database, session: AgentSessionRecord) -> None:
    _insert_session(database, session, replace=True)


def persist_session(
    start: Path,
    record: AgentSessionRecord,
    *,
    expected_updated_at: str | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    with project_state_lock(project.root), session_lock(project.root, record.id):
        return persist_session_locked(
            project.root,
            record,
            expected_updated_at=expected_updated_at,
        )


def persist_session_locked(
    start: Path,
    record: AgentSessionRecord,
    *,
    expected_updated_at: str | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    current = load_session(project.root, record.id)
    if expected_updated_at is not None and current.updated_at != expected_updated_at:
        raise SessionConflictError(
            f"Session changed while the operation was in progress: {record.id}"
        )
    if current.experiment_id != record.experiment_id or current.worktree != record.worktree:
        raise SessionConflictError("Session identity fields cannot be changed")
    destination = project.paths.sessions / record.id / "session.json"
    try:
        with open_database(project.paths.database) as database:
            owner = _active_owner(database, record.worktree)
            if record.state not in _TERMINAL_STATES and owner not in {None, record.id}:
                raise SessionConflictError(
                    f"Worktree is already owned by active session {owner}",
                    details={"owner_session_id": owner, "worktree": record.worktree},
                )
            _write_session(destination, record)
            try:
                _insert_session(database, record, replace=True)
            except BaseException:
                _write_session(destination, current)
                raise
    except sqlite3.IntegrityError as error:
        with open_database(project.paths.database) as database:
            owner = _active_owner(database, record.worktree)
        raise SessionConflictError(
            f"Worktree is already owned by active session {owner or 'unknown'}",
            details={"owner_session_id": owner, "worktree": record.worktree},
        ) from error
    return record


@contextmanager
def session_lock(start: Path, session_id: str) -> Iterator[None]:
    project = discover_project(start)
    _validate_session_id(session_id)
    directory = project.paths.sessions / session_id
    if directory.is_symlink() or not directory.is_dir():
        raise SessionNotFoundError(f"Session does not exist: {session_id}")
    lock_path = directory / ".lock"
    if lock_path.is_symlink():
        raise SessionConflictError(f"Invalid symlinked session lock: {session_id}")
    with exclusive_file_lock(lock_path):
        yield


def _insert_session(
    database: Database,
    record: AgentSessionRecord,
    *,
    replace: bool = False,
) -> None:
    conflict = (
        """
        ON CONFLICT(id) DO UPDATE SET
            runtime = excluded.runtime,
            role = excluded.role,
            compute_profile = excluded.compute_profile,
            task_path = excluded.task_path,
            state = excluded.state,
            native_session_id = excluded.native_session_id,
            supervisor_pid = excluded.supervisor_pid,
            process_id = excluded.process_id,
            updated_at = excluded.updated_at,
            finished_at = excluded.finished_at,
            exit_code = excluded.exit_code,
            resulting_commits_json = excluded.resulting_commits_json
    """
        if replace
        else ""
    )
    with database.connection:
        database.connection.execute(
            f"""
            INSERT INTO sessions (
                id, experiment_id, runtime, role, compute_profile, worktree, task_path,
                state, native_session_id, supervisor_pid, process_id, created_at,
                updated_at, finished_at, exit_code, initial_commit, resulting_commits_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            {conflict}
            """,
            (
                record.id,
                record.experiment_id,
                record.runtime,
                record.role,
                record.compute_profile,
                record.worktree,
                record.task_path,
                record.state,
                record.native_session_id,
                record.supervisor_pid,
                record.process_pid,
                record.created_at,
                record.updated_at,
                record.finished_at,
                record.exit_code,
                record.initial_commit,
                json.dumps(record.resulting_commits),
            ),
        )
        for attempt in record.attempts:
            database.connection.execute(
                """
                INSERT INTO session_attempts (
                    session_id, number, state, prompt_path, events_path, stderr_path,
                    started_at, finished_at, supervisor_pid, process_id, native_session_id,
                    exit_code, initial_commit, resulting_commit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, number) DO UPDATE SET
                    state = excluded.state,
                    prompt_path = excluded.prompt_path,
                    events_path = excluded.events_path,
                    stderr_path = excluded.stderr_path,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    supervisor_pid = excluded.supervisor_pid,
                    process_id = excluded.process_id,
                    native_session_id = excluded.native_session_id,
                    exit_code = excluded.exit_code,
                    resulting_commit = excluded.resulting_commit
                """,
                (
                    record.id,
                    attempt.number,
                    attempt.state,
                    attempt.prompt_path,
                    attempt.events_path,
                    attempt.stderr_path,
                    attempt.started_at,
                    attempt.finished_at,
                    attempt.supervisor_pid,
                    attempt.process_pid,
                    attempt.native_session_id,
                    attempt.exit_code,
                    attempt.initial_commit,
                    attempt.resulting_commit,
                ),
            )


def _active_owner(database: Database, worktree: str) -> str | None:
    row = database.connection.execute(
        """
        SELECT id FROM sessions
        WHERE worktree = ? AND state IN ('created', 'running', 'waiting')
        ORDER BY created_at LIMIT 1
        """,
        (worktree,),
    ).fetchone()
    return row["id"] if row else None


def _resolve_worktree(project: Project, relative: str) -> Path:
    lexical = project.root / relative
    if lexical.is_symlink():
        raise SessionConflictError(f"Experiment worktree is unavailable: {relative}")
    path = lexical.resolve()
    try:
        path.relative_to(project.paths.worktrees.resolve())
    except ValueError as error:
        raise SessionConflictError(
            f"Experiment worktree escapes project state: {relative}"
        ) from error
    return path


def _git_commit(worktree: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SessionConflictError(completed.stderr.strip() or "Cannot resolve worktree commit")
    return completed.stdout.strip()


def _write_session(path: Path, record: AgentSessionRecord) -> None:
    _write_json(path, record.model_dump(mode="json"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    write_json(path, payload)


def _validate_session_id(session_id: str) -> None:
    if _SESSION_ID.fullmatch(session_id) is None:
        raise ValueError("session identifier must match session-<16 lowercase hex characters>")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
