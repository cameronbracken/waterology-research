"""Resolve authorized run/session logs for bounded service reads."""

from pathlib import Path

from waterology.core.archive import load_archive
from waterology.core.log_pages import read_log_page
from waterology.core.project import discover_project
from waterology.core.sessions import load_session, resolve_session_file


def run_log_page(
    start: Path,
    run_id: str,
    *,
    stream: str = "stdout",
    offset: int = 0,
    max_bytes: int = 8192,
    query: str | None = None,
    snapshot: str | None = None,
) -> dict[str, object]:
    if stream not in {"stdout", "stderr"}:
        raise ValueError("stream must be stdout or stderr")
    project = discover_project(start)
    load_archive(project.root, run_id)
    path = project.paths.runs / run_id / f"{stream}.log"
    for parent in (path, *path.parents):
        if parent == project.root:
            break
        if parent.is_symlink():
            raise ValueError("Log path must not traverse a symlink")
    return {
        **read_log_page(path, offset=offset, max_bytes=max_bytes, query=query, snapshot=snapshot),
        "run_id": run_id,
        "stream": stream,
        "path": path.relative_to(project.root).as_posix(),
    }


def session_log_page(
    start: Path,
    session_id: str,
    *,
    stream: str = "events",
    attempt: int | None = None,
    offset: int = 0,
    max_bytes: int = 8192,
    query: str | None = None,
    snapshot: str | None = None,
) -> dict[str, object]:
    if stream not in {"events", "stderr"}:
        raise ValueError("stream must be events or stderr")
    project = discover_project(start)
    session = load_session(project.root, session_id)
    if not session.attempts:
        raise ValueError("Session has no log attempts yet")
    number = session.attempts[-1].number if attempt is None else attempt
    selected = next((item for item in session.attempts if item.number == number), None)
    if selected is None:
        raise ValueError("Unknown session attempt")
    relative = selected.events_path if stream == "events" else selected.stderr_path
    path = resolve_session_file(project.root, session.id, relative)
    return {
        **read_log_page(path, offset=offset, max_bytes=max_bytes, query=query, snapshot=snapshot),
        "session_id": session_id,
        "attempt": number,
        "stream": stream,
        "path": relative,
    }
