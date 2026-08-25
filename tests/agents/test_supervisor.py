import json
import os
import subprocess
from pathlib import Path

import pytest

import waterology.agents.supervisor as supervisor_module
from waterology.agents.supervisor import (
    begin_attempt,
    build_task_brief,
    interrupt_session,
    launch_session,
    reconcile_session,
    run_supervised_attempt,
)
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.sessions import (
    SessionConflictError,
    SessionStateError,
    create_session,
    load_session,
)


def make_session(tmp_path: Path, runtime: str = "codex") -> tuple[Path, str]:
    root = tmp_path / "study"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.org"], check=True)
    initialize_project(root)
    (root / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(root), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "commit", "--quiet", "-m", "base"], check=True)
    experiment = create_experiment(
        root,
        hypothesis="A supervised agent completes a task.",
        experiment_id="exp-supervisor",
    )
    session = create_session(
        root,
        experiment_id=experiment.id,
        runtime=runtime,
        role="researcher",
        task="Inspect the baseline.",
        session_id="session-aaaaaaaaaaaaaaaa",
    )
    return root, session.id


def fake_runtime(path: Path, *, exit_code: int = 0) -> Path:
    script = path / "fake-runtime"
    script.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' \'{"type":"thread.started","thread_id":"thread-test"}\'\n'
        "printf '%s\\n' '{\"type\":\"turn.completed\"}'\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


@pytest.mark.parametrize(
    ("wait_result", "expected"),
    ((0, False), (0x00000102, True), (0xFFFFFFFF, True)),
)
def test_windows_process_probe_waits_without_terminating(
    wait_result: int, expected: bool
) -> None:
    class Kernel:
        def __init__(self) -> None:
            self.opened: list[tuple[int, bool, int]] = []
            self.closed: list[int] = []

        def OpenProcess(self, access: int, inherit: bool, pid: int) -> int:
            self.opened.append((access, inherit, pid))
            return 5151

        def WaitForSingleObject(self, handle: int, timeout: int) -> int:
            assert (handle, timeout) == (5151, 0)
            return wait_result

        def CloseHandle(self, handle: int) -> None:
            self.closed.append(handle)

    kernel = Kernel()

    assert supervisor_module._windows_process_alive(
        4242, kernel32=kernel, get_last_error=lambda: 0
    ) is expected
    assert kernel.opened == [(0x00100000, False, 4242)]
    assert kernel.closed == [5151]


@pytest.mark.parametrize(("error", "expected"), ((5, True), (87, False)))
def test_windows_process_probe_handles_open_failure_conservatively(
    error: int, expected: bool
) -> None:
    class Kernel:
        def OpenProcess(self, _access: int, _inherit: bool, _pid: int) -> int:
            return 0

    assert supervisor_module._windows_process_alive(
        4242,
        kernel32=Kernel(),
        get_last_error=lambda: error,
    ) is expected


def test_task_brief_contains_owned_context_and_limits(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    session = load_session(root, session_id)

    brief = build_task_brief(root, session, "Inspect the baseline.")

    assert session.experiment_id in brief
    assert session.worktree in brief
    assert "researcher" in brief
    assert "local" in brief
    assert "waterology-mcp" in brief
    assert "Do not push" in brief


def test_supervised_attempt_streams_events_and_reconciles_completion(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    session = begin_attempt(
        root, session_id, prompt="Inspect the baseline.", supervisor_pid=os.getpid()
    )

    exit_code = run_supervised_attempt(
        root,
        session_id,
        session.attempts[-1].number,
        executable=str(fake_runtime(tmp_path)),
    )
    completed = reconcile_session(root, session_id)

    assert exit_code == 0
    assert completed.state == "completed"
    assert completed.native_session_id == "thread-test"
    assert completed.process_pid is not None
    assert completed.exit_code == 0
    assert completed.attempts[-1].state == "completed"
    assert completed.attempts[-1].process_pid == completed.process_pid
    events = root / completed.attempts[-1].events_path
    assert "thread.started" in events.read_text(encoding="utf-8")


def test_supervised_attempt_preserves_failure_logs(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    session = begin_attempt(root, session_id, prompt="Fail safely.", supervisor_pid=os.getpid())

    run_supervised_attempt(
        root,
        session_id,
        session.attempts[-1].number,
        executable=str(fake_runtime(tmp_path, exit_code=7)),
    )
    failed = reconcile_session(root, session_id)

    assert failed.state == "failed"
    assert failed.exit_code == 7
    assert failed.native_session_id == "thread-test"
    assert (root / failed.attempts[-1].stderr_path).is_file()


def test_reconcile_marks_missing_supervisor_lost(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    begin_attempt(root, session_id, prompt="Disappear.", supervisor_pid=999999)

    lost = reconcile_session(root, session_id, process_alive=lambda _pid: False)

    assert lost.state == "lost"
    assert lost.attempts[-1].state == "lost"
    assert (root / lost.attempts[-1].events_path).is_file()


def test_begin_attempt_removes_files_when_ownership_persistence_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id = make_session(tmp_path)

    def reject_persistence(*_args: object, **_kwargs: object) -> None:
        raise SessionStateError("ownership changed")

    monkeypatch.setattr("waterology.agents.supervisor.persist_session_locked", reject_persistence)

    with pytest.raises(SessionStateError, match="ownership changed"):
        begin_attempt(root, session_id, prompt="Do not leave an orphan attempt.")

    assert not (root / ".waterology/sessions" / session_id / "attempt-001").exists()


def test_launch_failure_releases_active_session_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id = make_session(tmp_path)
    real_popen = subprocess.Popen

    def fail_to_launch(arguments: object, **kwargs: object) -> subprocess.Popen[str]:
        if isinstance(arguments, tuple) and "waterology.agents.worker" in arguments:
            raise OSError("worker launch failed")
        return real_popen(arguments, **kwargs)

    monkeypatch.setattr("waterology.agents.supervisor.subprocess.Popen", fail_to_launch)

    with pytest.raises(OSError, match="worker launch failed"):
        launch_session(root, session_id, prompt="Fail before the worker starts.")

    failed = load_session(root, session_id)
    assert failed.state == "failed"
    assert failed.exit_code == 127
    assert failed.attempts[-1].state == "failed"


def test_post_spawn_registration_failure_stops_worker_and_seals_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id = make_session(tmp_path)
    real_popen = subprocess.Popen

    class WorkerProcess:
        pid = 5151
        terminated = False
        waited = False

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float) -> int:
            assert timeout == 5
            self.waited = True
            return 0

    worker = WorkerProcess()

    def intercept_launch(arguments: object, **kwargs: object) -> object:
        if isinstance(arguments, tuple) and "waterology.agents.worker" in arguments:
            return worker
        return real_popen(arguments, **kwargs)

    def fail_gate(*_args: object, **_kwargs: object) -> None:
        raise OSError("gate write failed")

    monkeypatch.setattr("waterology.agents.supervisor.subprocess.Popen", intercept_launch)
    monkeypatch.setattr("waterology.agents.supervisor.write_text", fail_gate)

    with pytest.raises(OSError, match="gate write failed"):
        launch_session(root, session_id, prompt="Fail after spawning the worker.")

    failed = load_session(root, session_id)
    assert worker.terminated is True
    assert worker.waited is True
    assert failed.state == "failed"
    assert failed.supervisor_pid == 5151
    assert failed.attempts[-1].state == "failed"


def test_post_spawn_cleanup_kills_a_stubborn_gated_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id = make_session(tmp_path)
    real_popen = subprocess.Popen

    class WorkerProcess:
        pid = 6161
        killed = False
        waits = 0

        def terminate(self) -> None:
            return None

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: float) -> int:
            assert timeout == 5
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired("worker", timeout)
            return 0

    worker = WorkerProcess()

    def intercept_launch(arguments: object, **kwargs: object) -> object:
        if isinstance(arguments, tuple) and "waterology.agents.worker" in arguments:
            return worker
        return real_popen(arguments, **kwargs)

    def fail_gate(*_args: object, **_kwargs: object) -> None:
        raise OSError("gate write failed")

    monkeypatch.setattr("waterology.agents.supervisor.subprocess.Popen", intercept_launch)
    monkeypatch.setattr("waterology.agents.supervisor.write_text", fail_gate)

    with pytest.raises(OSError, match="gate write failed"):
        launch_session(root, session_id, prompt="Stop a stubborn gated worker.")

    assert worker.killed is True
    assert worker.waits == 2
    assert load_session(root, session_id).state == "failed"


def test_completed_session_can_begin_native_resume_attempt(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    session = begin_attempt(root, session_id, prompt="First turn.", supervisor_pid=os.getpid())
    run_supervised_attempt(
        root,
        session_id,
        session.attempts[-1].number,
        executable=str(fake_runtime(tmp_path)),
    )
    completed = reconcile_session(root, session_id)

    resumed = begin_attempt(
        root,
        session_id,
        prompt="Continue with a second comparison.",
        supervisor_pid=os.getpid(),
    )

    assert completed.native_session_id == "thread-test"
    assert resumed.state == "running"
    assert len(resumed.attempts) == 2
    assert resumed.attempts[-1].number == 2


def test_interrupt_verifies_and_stops_owned_supervisor(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    begin_attempt(root, session_id, prompt="Stop this attempt.", supervisor_pid=4242)
    terminated: list[int] = []

    cancelled = interrupt_session(
        root,
        session_id,
        verify_process=lambda pid, identifier: pid == 4242 and identifier == session_id,
        terminate=lambda pid: terminated.append(pid),
    )

    assert terminated == [4242]
    assert cancelled.state == "cancelled"
    assert cancelled.attempts[-1].state == "cancelled"
    assert cancelled.exit_code is None


def test_interrupt_refuses_unverified_process_identifier(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    begin_attempt(root, session_id, prompt="Do not signal the wrong process.", supervisor_pid=4242)

    with pytest.raises(SessionStateError, match="could not be verified"):
        interrupt_session(
            root,
            session_id,
            verify_process=lambda _pid, _identifier: False,
            terminate=lambda _pid: None,
        )

    assert load_session(root, session_id).state == "running"


def test_interrupt_keeps_ownership_until_supervisor_is_observed_stopped(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    current = begin_attempt(root, session_id, prompt="Keep ownership.", supervisor_pid=4242)

    with pytest.raises(SessionStateError, match="did not stop") as raised:
        interrupt_session(
            root,
            session_id,
            verify_process=lambda _pid, _identifier: True,
            terminate=lambda _pid: None,
            process_alive=lambda _pid: True,
            wait_timeout=0,
        )

    assert raised.value.details == {"ownership_released": False}
    assert load_session(root, session_id).state == "running"
    with pytest.raises(SessionConflictError, match="already owned"):
        create_session(
            root,
            experiment_id=current.experiment_id,
            runtime="codex",
            role="researcher",
            task="This must wait for the prior writer.",
            session_id="session-bbbbbbbbbbbbbbbb",
        )


def test_interrupt_waits_for_runtime_child_after_supervisor_exits(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    current = begin_attempt(root, session_id, prompt="Wait for the child.", supervisor_pid=4242)
    attempt_directory = (root / current.attempts[-1].events_path).parent
    (attempt_directory / "process.json").write_text(
        json.dumps(
            {
                "pid": 4343,
                "started_at": current.attempts[-1].started_at,
                "native_session_id": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    observed: list[tuple[int, int | None]] = []

    def child_is_alive(supervisor_pid: int, runtime_pid: int | None) -> bool:
        observed.append((supervisor_pid, runtime_pid))
        return runtime_pid == 4343

    with pytest.raises(SessionStateError, match="did not stop"):
        interrupt_session(
            root,
            session_id,
            verify_process=lambda _pid, _identifier: True,
            terminate=lambda _pid: None,
            owned_processes_alive=child_is_alive,
            wait_timeout=0,
        )

    assert observed == [(4242, 4343), (4242, 4343)]
    assert load_session(root, session_id).state == "running"


def test_interrupt_releases_contained_runtime_after_process_tree_stops(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    current = begin_attempt(root, session_id, prompt="Publish the child PID.", supervisor_pid=4242)
    attempt_directory = (root / current.attempts[-1].events_path).parent
    (attempt_directory / "runtime-starting.json").write_text(
        json.dumps(
            {
                "containment": "process_group",
                "started_at": current.attempts[-1].started_at,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    cancelled = interrupt_session(
        root,
        session_id,
        verify_process=lambda _pid, _identifier: True,
        terminate=lambda _pid: None,
        owned_processes_alive=lambda _supervisor_pid, _runtime_pid: False,
        wait_timeout=0,
    )

    assert cancelled.state == "cancelled"


def test_reconcile_marks_stale_contained_starting_marker_lost(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    current = begin_attempt(
        root, session_id, prompt="Publish the child PID.", supervisor_pid=999999
    )
    attempt_directory = (root / current.attempts[-1].events_path).parent
    (attempt_directory / "runtime-starting.json").write_text(
        json.dumps(
            {
                "containment": "process_group",
                "started_at": current.attempts[-1].started_at,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    lost = reconcile_session(root, session_id)

    assert lost.state == "lost"


def test_runtime_creation_permission_failure_seals_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id = make_session(tmp_path)
    current = begin_attempt(
        root, session_id, prompt="Handle a denied runtime launch.", supervisor_pid=os.getpid()
    )
    runtime = fake_runtime(tmp_path)
    real_popen = subprocess.Popen

    def deny_runtime(arguments: object, **kwargs: object) -> object:
        if isinstance(arguments, tuple) and arguments[0] == str(runtime):
            raise PermissionError("runtime denied")
        return real_popen(arguments, **kwargs)

    monkeypatch.setattr("waterology.agents.supervisor.subprocess.Popen", deny_runtime)
    exit_code = run_supervised_attempt(
        root,
        session_id,
        current.attempts[-1].number,
        executable=str(runtime),
    )
    failed = reconcile_session(root, session_id)

    assert exit_code == 127
    assert failed.state == "failed"
    assert not ((root / failed.attempts[-1].events_path).parent / "runtime-starting.json").exists()


def test_reconcile_rejects_symlinked_terminal_result(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    current = begin_attempt(root, session_id, prompt="Reject a linked result.", supervisor_pid=4242)
    attempt_directory = (root / current.attempts[-1].events_path).parent
    outside = tmp_path / "result.json"
    outside.write_text(
        json.dumps(
            {
                "exit_code": 0,
                "finished_at": "2026-08-25T01:00:00Z",
                "native_session_id": "thread-forged",
                "process_pid": 4343,
                "resulting_commit": current.initial_commit,
                "state": "completed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (attempt_directory / "result.json").symlink_to(outside)

    with pytest.raises(SessionConflictError, match="symlinked session file"):
        reconcile_session(root, session_id)

    assert load_session(root, session_id).state == "running"


def test_interrupt_preserves_terminal_result_written_before_stop(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    session = begin_attempt(root, session_id, prompt="Finish before stop.", supervisor_pid=4242)
    run_supervised_attempt(
        root,
        session_id,
        session.attempts[-1].number,
        executable=str(fake_runtime(tmp_path)),
    )

    completed = interrupt_session(
        root,
        session_id,
        verify_process=lambda _pid, _identifier: True,
        terminate=lambda _pid: None,
        process_alive=lambda _pid: False,
    )

    assert completed.state == "completed"
    assert completed.exit_code == 0


def test_interrupt_failure_does_not_release_worktree_ownership(tmp_path: Path) -> None:
    root, session_id = make_session(tmp_path)
    begin_attempt(root, session_id, prompt="Retain ownership on signal failure.", supervisor_pid=4242)

    def reject_signal(_pid: int) -> None:
        raise PermissionError("signal denied")

    with pytest.raises(PermissionError, match="signal denied"):
        interrupt_session(
            root,
            session_id,
            verify_process=lambda _pid, _identifier: True,
            terminate=reject_signal,
        )

    assert load_session(root, session_id).state == "running"
