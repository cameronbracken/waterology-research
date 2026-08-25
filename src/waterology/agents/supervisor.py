import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from waterology.agents import get_adapter
from waterology.agents.base import AdapterError, RuntimeLaunch
from waterology.core.atomic import write_json, write_text
from waterology.core.database import open_database
from waterology.core.project import discover_project, project_state_lock
from waterology.core.records import (
    AgentAttemptRecord,
    AgentProcessRecord,
    AgentResultRecord,
    AgentSessionRecord,
    AgentStartingRecord,
)
from waterology.core.sessions import (
    SessionStateError,
    load_session,
    persist_session_locked,
    resolve_optional_session_file,
    resolve_session_file,
    session_lock,
)


def build_task_brief(start: Path, session: AgentSessionRecord, task: str) -> str:
    project = discover_project(start)
    return (
        "# Waterology agent task\n\n"
        f"Project: {project.config.name}\n"
        f"Experiment: {session.experiment_id}\n"
        f"Worktree: {session.worktree}\n"
        f"Role: {session.role}\n"
        f"Compute profile: {session.compute_profile}\n"
        f"Session: {session.id}\n\n"
        "## Task\n\n"
        f"{task.strip()}\n\n"
        "## Boundaries\n\n"
        "Use the project guidance and installed Waterology skills. Use `waterology-mcp` for "
        "research records when the runtime exposes it. Keep edits in the assigned worktree. "
        "Do not push, publish, or delete remote data. Record evidence and resulting commits.\n"
    )


def begin_attempt(
    start: Path,
    session_id: str,
    *,
    prompt: str,
    supervisor_pid: int | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    with project_state_lock(project.root), session_lock(project.root, session_id):
        return _begin_attempt_locked(
            project.root,
            session_id,
            prompt=prompt,
            supervisor_pid=supervisor_pid,
        )


def _begin_attempt_locked(
    start: Path,
    session_id: str,
    *,
    prompt: str,
    supervisor_pid: int | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    current = load_session(project.root, session_id)
    if current.state == "running":
        raise SessionStateError(f"Session is already active: {session_id}")
    if current.attempts and not current.native_session_id:
        raise SessionStateError(f"Session has no native identifier to resume: {session_id}")
    stripped = prompt.strip()
    if not stripped:
        raise ValueError("attempt prompt must not be blank")
    number = len(current.attempts) + 1
    relative = Path(".waterology") / "sessions" / current.id / f"attempt-{number:03d}"
    directory = project.root / relative
    directory.mkdir()
    prompt_path = relative / "prompt.md"
    events_path = relative / "events.jsonl"
    stderr_path = relative / "stderr.log"
    (project.root / prompt_path).write_text(
        build_task_brief(project.root, current, stripped), encoding="utf-8"
    )
    (project.root / events_path).touch()
    (project.root / stderr_path).touch()
    now = _utc_now()
    attempt = AgentAttemptRecord(
        number=number,
        state="running",
        prompt_path=prompt_path.as_posix(),
        events_path=events_path.as_posix(),
        stderr_path=stderr_path.as_posix(),
        started_at=now,
        supervisor_pid=supervisor_pid,
        initial_commit=_git_commit(project.root / current.worktree),
    )
    updated = current.model_copy(
        update={
            "state": "running",
            "supervisor_pid": supervisor_pid,
            "process_pid": None,
            "finished_at": None,
            "exit_code": None,
            "updated_at": now,
            "attempts": (*current.attempts, attempt),
        }
    )
    try:
        return persist_session_locked(
            project.root,
            updated,
            expected_updated_at=current.updated_at,
        )
    except Exception:
        shutil.rmtree(directory)
        raise


def launch_session(start: Path, session_id: str, *, prompt: str) -> AgentSessionRecord:
    project = discover_project(start)
    with project_state_lock(project.root), session_lock(project.root, session_id):
        prepared = _begin_attempt_locked(project.root, session_id, prompt=prompt)
        attempt = prepared.attempts[-1]
        gate = _attempt_directory(project.root, prepared, attempt) / "launch.ready"
        arguments = (
            sys.executable,
            "-m",
            "waterology.agents.worker",
            str(project.root),
            prepared.id,
            str(attempt.number),
            str(gate),
        )
        kwargs: dict[str, object] = {
            "cwd": str(project.root),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        try:
            process = subprocess.Popen(arguments, **kwargs)
        except OSError:
            _record_failed_launch(project.root, prepared, exit_code=127)
            raise
        launched_attempt = attempt.model_copy(update={"supervisor_pid": process.pid})
        launched = prepared.model_copy(
            update={
                "supervisor_pid": process.pid,
                "updated_at": _utc_now(),
                "attempts": (*prepared.attempts[:-1], launched_attempt),
            }
        )
        try:
            persist_session_locked(
                project.root,
                launched,
                expected_updated_at=prepared.updated_at,
            )
            write_text(gate, "ready\n")
        except BaseException:
            _stop_unlaunched_worker(process)
            current = load_session(project.root, session_id)
            if current.state == "running":
                _record_failed_launch(project.root, current, exit_code=127)
            raise
        return launched


def _stop_unlaunched_worker(process: subprocess.Popen[object]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _record_failed_launch(
    start: Path,
    current: AgentSessionRecord,
    *,
    exit_code: int,
) -> AgentSessionRecord:
    finished = _utc_now()
    attempt = current.attempts[-1]
    failed_attempt = attempt.model_copy(
        update={"state": "failed", "finished_at": finished, "exit_code": exit_code}
    )
    return persist_session_locked(
        start,
        current.model_copy(
            update={
                "state": "failed",
                "updated_at": finished,
                "finished_at": finished,
                "exit_code": exit_code,
                "attempts": (*current.attempts[:-1], failed_attempt),
            }
        ),
        expected_updated_at=current.updated_at,
    )


def run_supervised_attempt(
    start: Path,
    session_id: str,
    attempt_number: int,
    *,
    executable: str | None = None,
) -> int:
    project = discover_project(start)
    session = load_session(project.root, session_id)
    attempt = _attempt(session, attempt_number)
    prompt = resolve_session_file(project.root, session.id, attempt.prompt_path).read_text(
        encoding="utf-8"
    )
    adapter = get_adapter(session.runtime)
    command = adapter.build_command(
        RuntimeLaunch(
            executable=executable or session.runtime,
            worktree=project.root / session.worktree,
            prompt=prompt,
            role=session.role,
            native_session_id=session.native_session_id if attempt.number > 1 else None,
        )
    )
    directory = _attempt_directory(project.root, session, attempt)
    starting_path = directory / "runtime-starting.json"
    process_path = directory / "process.json"
    result_path = directory / "result.json"
    native_id = session.native_session_id
    process_pid = None
    stderr_path = resolve_session_file(project.root, session.id, attempt.stderr_path)
    events_path = resolve_session_file(project.root, session.id, attempt.events_path)
    try:
        if os.name == "nt":
            _ensure_windows_job()
    except OSError as error:
        with stderr_path.open("a", encoding="utf-8") as stderr:
            stderr.write(f"waterology: runtime containment could not start: {error}\n")
        exit_code = 127
    else:
        with stderr_path.open("a", encoding="utf-8") as stderr:
            containment = "windows_job" if os.name == "nt" else "process_group"
            _write_json(
                starting_path,
                {"containment": containment, "started_at": _utc_now()},
            )
            try:
                process = subprocess.Popen(
                    command.arguments,
                    cwd=command.cwd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=stderr,
                    text=True,
                    bufsize=1,
                )
            except OSError as error:
                starting_path.unlink(missing_ok=True)
                stderr.write(f"waterology: runtime command could not start: {error}\n")
                exit_code = 127
            else:
                process_pid = process.pid
                _write_json(
                    process_path,
                    {
                        "pid": process.pid,
                        "started_at": _utc_now(),
                        "native_session_id": native_id,
                    },
                )
                starting_path.unlink()
                assert process.stdout is not None
                with events_path.open("a", encoding="utf-8") as events:
                    for line in process.stdout:
                        events.write(line)
                        events.flush()
                        try:
                            event = adapter.parse_event(line)
                        except AdapterError as error:
                            stderr.write(f"waterology: {error}\n")
                            stderr.flush()
                            continue
                        native_id = adapter.native_session_id(event) or native_id
                        _write_json(
                            process_path,
                            {
                                "pid": process.pid,
                                "started_at": attempt.started_at,
                                "native_session_id": native_id,
                            },
                        )
                exit_code = process.wait()
    resulting_commit = _git_commit(project.root / session.worktree)
    _write_json(
        result_path,
        {
            "exit_code": exit_code,
            "finished_at": _utc_now(),
            "native_session_id": native_id,
            "process_pid": process_pid,
            "resulting_commit": resulting_commit,
            "state": "completed" if exit_code == 0 else "failed",
        },
    )
    return exit_code


def reconcile_session(
    start: Path,
    session_id: str,
    *,
    process_alive: Callable[[int], bool] | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    with project_state_lock(project.root), session_lock(project.root, session_id):
        return _reconcile_session_locked(
            project.root,
            session_id,
            process_alive=process_alive,
        )


def _reconcile_session_locked(
    start: Path,
    session_id: str,
    *,
    process_alive: Callable[[int], bool] | None = None,
) -> AgentSessionRecord:
    project = discover_project(start)
    current = load_session(project.root, session_id)
    if current.state not in {"running", "waiting"} or not current.attempts:
        return current
    alive = process_alive or _process_alive
    attempt = current.attempts[-1]
    directory = _attempt_directory(project.root, current, attempt)
    attempt_relative = directory.relative_to(project.root)
    result_path = resolve_optional_session_file(
        project.root,
        current.id,
        (attempt_relative / "result.json").as_posix(),
    )
    process_path = resolve_optional_session_file(
        project.root,
        current.id,
        (attempt_relative / "process.json").as_posix(),
    )
    _, starting_containment = _runtime_process_state(
        project.root,
        current.id,
        directory,
        fallback_pid=current.process_pid,
    )
    if result_path is not None:
        result = AgentResultRecord.model_validate_json(result_path.read_text(encoding="utf-8"))
        native_id = result.native_session_id or current.native_session_id
        completed_attempt = attempt.model_copy(
            update={
                "state": result.state,
                "finished_at": result.finished_at,
                "native_session_id": native_id,
                "process_pid": result.process_pid,
                "exit_code": result.exit_code,
                "resulting_commit": result.resulting_commit,
            }
        )
        commits = current.resulting_commits
        if result.resulting_commit != attempt.initial_commit and result.resulting_commit not in commits:
            commits = (*commits, result.resulting_commit)
        updated = current.model_copy(
            update={
                "state": result.state,
                "native_session_id": native_id,
                "process_pid": result.process_pid,
                "updated_at": result.finished_at,
                "finished_at": result.finished_at,
                "exit_code": result.exit_code,
                "resulting_commits": commits,
                "attempts": (*current.attempts[:-1], completed_attempt),
            }
        )
        return persist_session_locked(
            project.root,
            updated,
            expected_updated_at=current.updated_at,
        )
    if process_path is not None:
        process = AgentProcessRecord.model_validate_json(process_path.read_text(encoding="utf-8"))
        native_id = process.native_session_id or current.native_session_id
        if process.pid:
            previous_updated_at = current.updated_at
            updated_attempt = attempt.model_copy(
                update={"process_pid": process.pid, "native_session_id": native_id}
            )
            current = current.model_copy(
                update={
                    "process_pid": process.pid,
                    "native_session_id": native_id,
                    "updated_at": _utc_now(),
                    "attempts": (*current.attempts[:-1], updated_attempt),
                }
            )
            persist_session_locked(
                project.root,
                current,
                expected_updated_at=previous_updated_at,
            )
    if current.supervisor_pid:
        if process_alive is None and _owned_processes_alive(
            current.supervisor_pid, current.process_pid
        ):
            return current
        if process_alive is not None and alive(current.supervisor_pid):
            return current
    if (
        process_alive is not None
        and starting_containment is not None
        and current.process_pid is None
    ):
        return current
    finished = _utc_now()
    lost_attempt = current.attempts[-1].model_copy(
        update={"state": "lost", "finished_at": finished}
    )
    lost = current.model_copy(
        update={
            "state": "lost",
            "updated_at": finished,
            "finished_at": finished,
            "attempts": (*current.attempts[:-1], lost_attempt),
        }
    )
    return persist_session_locked(
        project.root,
        lost,
        expected_updated_at=current.updated_at,
    )


def interrupt_session(
    start: Path,
    session_id: str,
    *,
    verify_process: Callable[[int, str], bool] | None = None,
    terminate: Callable[[int], None] | None = None,
    process_alive: Callable[[int], bool] | None = None,
    owned_processes_alive: Callable[[int, int | None], bool] | None = None,
    wait_timeout: float = 5.0,
) -> AgentSessionRecord:
    project = discover_project(start)
    with project_state_lock(project.root), session_lock(project.root, session_id):
        current = load_session(project.root, session_id)
        if current.state in {"completed", "failed", "cancelled", "lost"}:
            return current
        if current.state not in {"running", "waiting"} or current.supervisor_pid is None:
            raise SessionStateError(f"Session has no active supervisor: {session_id}")
        verifier = verify_process or _owns_supervisor
        if not verifier(current.supervisor_pid, current.id):
            raise SessionStateError(
                f"Session supervisor could not be verified: {current.supervisor_pid}"
            )
        attempt_directory = _attempt_directory(project.root, current, current.attempts[-1])
        runtime_pid, starting_containment = _runtime_process_state(
            project.root,
            current.id,
            attempt_directory,
            fallback_pid=current.process_pid,
        )
        with open_database(project.paths.database) as database:
            intent = database.append_intent(
                kind="session.cancel",
                entity_type="session",
                entity_id=session_id,
                payload={"supervisor_pid": current.supervisor_pid},
            )
        try:
            (terminate or _terminate_supervisor)(current.supervisor_pid)
        except BaseException as error:
            with open_database(project.paths.database) as database:
                database.append_observation(
                    intent.id,
                    payload={"error": type(error).__name__, "outcome": "failed"},
                )
            raise
        if owned_processes_alive is not None:
            alive = owned_processes_alive
        elif process_alive is not None:
            alive = lambda supervisor_pid, _runtime_pid: process_alive(supervisor_pid)
        else:
            alive = _owned_processes_alive

        def ownership_is_active() -> bool:
            nonlocal runtime_pid, starting_containment
            runtime_pid, starting_containment = _runtime_process_state(
                project.root,
                current.id,
                attempt_directory,
                fallback_pid=runtime_pid,
            )
            if alive(current.supervisor_pid, runtime_pid):
                return True
            return (
                process_alive is not None
                and owned_processes_alive is None
                and starting_containment is not None
                and runtime_pid is None
            )

        deadline = time.monotonic() + wait_timeout
        while ownership_is_active() and time.monotonic() < deadline:
            time.sleep(0.05)
        if ownership_is_active():
            with open_database(project.paths.database) as database:
                database.append_observation(
                    intent.id,
                    payload={"outcome": "still_running"},
                )
            raise SessionStateError(
                f"Session supervisor did not stop: {current.supervisor_pid}",
                details={"ownership_released": False},
            )
        result_path = resolve_optional_session_file(
            project.root,
            current.id,
            (attempt_directory.relative_to(project.root) / "result.json").as_posix(),
        )
        if result_path is not None:
            result = _reconcile_session_locked(project.root, session_id)
            with open_database(project.paths.database) as database:
                database.append_observation(
                    intent.id,
                    payload={"outcome": result.state},
                )
            return result
        finished = _utc_now()
        attempt = current.attempts[-1]
        resulting_commit = _git_commit(project.root / current.worktree)
        cancelled_attempt = attempt.model_copy(
            update={
                "state": "cancelled",
                "finished_at": finished,
                "resulting_commit": resulting_commit,
            }
        )
        commits = current.resulting_commits
        if resulting_commit != attempt.initial_commit and resulting_commit not in commits:
            commits = (*commits, resulting_commit)
        cancelled = current.model_copy(
            update={
                "state": "cancelled",
                "updated_at": finished,
                "finished_at": finished,
                "exit_code": None,
                "resulting_commits": commits,
                "attempts": (*current.attempts[:-1], cancelled_attempt),
            }
        )
        result = persist_session_locked(
            project.root,
            cancelled,
            expected_updated_at=current.updated_at,
        )
        with open_database(project.paths.database) as database:
            database.append_observation(intent.id, payload={"outcome": "cancelled"})
        return result


def _attempt(session: AgentSessionRecord, number: int) -> AgentAttemptRecord:
    for attempt in session.attempts:
        if attempt.number == number:
            return attempt
    raise SessionStateError(f"Session attempt does not exist: {session.id} attempt {number}")


def _attempt_directory(
    root: Path, session: AgentSessionRecord, attempt: AgentAttemptRecord
) -> Path:
    return resolve_session_file(root, session.id, attempt.events_path).parent


def _runtime_process_state(
    root: Path,
    session_id: str,
    attempt_directory: Path,
    *,
    fallback_pid: int | None,
) -> tuple[int | None, str | None]:
    attempt_relative = attempt_directory.relative_to(root)
    process_path = resolve_optional_session_file(
        root,
        session_id,
        (attempt_relative / "process.json").as_posix(),
    )
    starting_path = resolve_optional_session_file(
        root,
        session_id,
        (attempt_relative / "runtime-starting.json").as_posix(),
    )
    runtime_pid = fallback_pid
    if process_path is not None:
        process_record = AgentProcessRecord.model_validate_json(
            process_path.read_text(encoding="utf-8")
        )
        runtime_pid = process_record.pid
    starting_containment = None
    if starting_path is not None:
        starting = AgentStartingRecord.model_validate_json(
            starting_path.read_text(encoding="utf-8")
        )
        starting_containment = starting.containment
    return runtime_pid, starting_containment


def _process_alive(pid: int) -> bool:
    if os.name == "nt":
        return _windows_process_alive(pid)
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _windows_process_alive(
    pid: int,
    *,
    kernel32: object | None = None,
    get_last_error: Callable[[], int] | None = None,
) -> bool:
    import ctypes
    from ctypes import wintypes

    api = kernel32
    if api is None:
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.restype = wintypes.HANDLE
        api.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        api.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        api.WaitForSingleObject.restype = wintypes.DWORD
        api.CloseHandle.argtypes = (wintypes.HANDLE,)
    read_error = get_last_error or ctypes.get_last_error
    handle = api.OpenProcess(0x00100000, False, pid)
    if not handle:
        return read_error() != 87
    try:
        wait_result = api.WaitForSingleObject(handle, 0)
    finally:
        api.CloseHandle(handle)
    return wait_result != 0


def _owned_processes_alive(supervisor_pid: int, runtime_pid: int | None) -> bool:
    if os.name != "nt":
        try:
            os.killpg(supervisor_pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    return _process_alive(supervisor_pid) or (
        runtime_pid is not None and _process_alive(runtime_pid)
    )


def _owns_supervisor(pid: int, session_id: str) -> bool:
    if os.name == "nt":
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    else:
        completed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            check=False,
            capture_output=True,
            text=True,
        )
    command = completed.stdout
    return (
        completed.returncode == 0
        and "waterology.agents.worker" in command
        and session_id in command
    )


def _terminate_supervisor(pid: int) -> None:
    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0 and _process_alive(pid):
                raise OSError(completed.stderr.strip() or f"taskkill failed for process {pid}")
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except ProcessLookupError:
        return


def _git_commit(worktree: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


_WINDOWS_JOB_HANDLE: object | None = None


def _ensure_windows_job() -> None:
    global _WINDOWS_JOB_HANDLE
    if os.name != "nt" or _WINDOWS_JOB_HANDLE is not None:
        return
    import ctypes
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [
            ("read_operation_count", ctypes.c_uint64),
            ("write_operation_count", ctypes.c_uint64),
            ("other_operation_count", ctypes.c_uint64),
            ("read_transfer_count", ctypes.c_uint64),
            ("write_transfer_count", ctypes.c_uint64),
            ("other_transfer_count", ctypes.c_uint64),
        ]

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("per_process_user_time_limit", ctypes.c_int64),
            ("per_job_user_time_limit", ctypes.c_int64),
            ("limit_flags", wintypes.DWORD),
            ("minimum_working_set_size", ctypes.c_size_t),
            ("maximum_working_set_size", ctypes.c_size_t),
            ("active_process_limit", wintypes.DWORD),
            ("affinity", ctypes.c_size_t),
            ("priority_class", wintypes.DWORD),
            ("scheduling_class", wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("basic_limit_information", BasicLimitInformation),
            ("io_info", IoCounters),
            ("process_memory_limit", ctypes.c_size_t),
            ("job_memory_limit", ctypes.c_size_t),
            ("peak_process_memory_used", ctypes.c_size_t),
            ("peak_job_memory_used", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    information = ExtendedLimitInformation()
    information.basic_limit_information.limit_flags = 0x00002000
    if not kernel32.SetInformationJobObject(
        handle,
        9,
        ctypes.byref(information),
        ctypes.sizeof(information),
    ) or not kernel32.AssignProcessToJobObject(handle, kernel32.GetCurrentProcess()):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(handle)
        raise ctypes.WinError(error)
    _WINDOWS_JOB_HANDLE = handle


def _write_json(path: Path, payload: dict[str, object]) -> None:
    write_json(path, payload)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
