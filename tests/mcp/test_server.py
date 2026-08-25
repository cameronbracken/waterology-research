import asyncio
import os
import subprocess
from pathlib import Path

from mcp import Client

import waterology.mcp.server as server_module
from waterology.agents.supervisor import begin_attempt, run_supervised_attempt
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.sessions import create_session, load_session


def make_completed_runtime_session(
    root: Path, runtime: Path, *, session_id: str
) -> str:
    session = create_session(
        root,
        experiment_id="exp-mcp-session",
        runtime="codex",
        role="researcher",
        task="Complete through the MCP service boundary.",
        session_id=session_id,
    )
    running = begin_attempt(
        root,
        session.id,
        prompt="Complete this test attempt.",
        supervisor_pid=os.getpid(),
    )
    run_supervised_attempt(
        root,
        session.id,
        running.attempts[-1].number,
        executable=str(runtime),
    )
    assert load_session(root, session.id).state == "running"
    return session.id


def test_server_exposes_bounded_research_tools_without_shell() -> None:
    async def exercise() -> None:
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            listed = await client.list_tools()
        names = {tool.name for tool in listed.tools}
        assert {
            "project_status",
            "create_experiment",
            "inspect_experiment",
            "experiment_tree",
            "start_run",
            "inspect_run",
            "cancel_run",
            "assess_run",
            "read_run_logs",
            "read_run_metrics",
            "list_archives",
            "list_sessions",
            "inspect_session",
            "read_session_logs",
            "register_evidence",
            "register_artifact",
            "record_session_note",
        } <= names
        assert not any("shell" in name or "command" in name for name in names)

    asyncio.run(exercise())


def test_project_status_tool_calls_shared_service(monkeypatch: object, tmp_path: Path) -> None:
    expected = {"name": "study", "root": str(tmp_path)}
    monkeypatch.setattr(  # type: ignore[attr-defined]
        server_module.services, "project_status", lambda path: expected
    )

    async def exercise() -> None:
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool("project_status", {"project_path": str(tmp_path)})
        assert result.is_error is False
        assert result.structured_content == {"ok": True, "result": expected}

    asyncio.run(exercise())


def test_tool_errors_return_stable_structured_codes(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool(
                "inspect_session",
                {"session_id": "not-a-session", "project_path": str(tmp_path)},
            )
        assert result.is_error is False
        assert result.structured_content == {
            "ok": False,
            "error": {
                "code": "invalid_input",
                "details": {},
                "message": "session identifier must match session-<16 lowercase hex characters>",
            },
        }

    asyncio.run(exercise())


def test_session_tools_reconcile_completed_runtime_before_reading(tmp_path: Path) -> None:
    root = tmp_path / "study"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.org"], check=True
    )
    initialize_project(root)
    (root / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(root), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "commit", "--quiet", "-m", "base"], check=True)
    create_experiment(
        root,
        hypothesis="MCP reads reconcile finished runtime attempts.",
        experiment_id="exp-mcp-session",
    )
    runtime = tmp_path / "fake-runtime"
    runtime.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' '{\"type\":\"thread.started\",\"thread_id\":\"thread-mcp\"}'\n"
        "printf '%s\\n' '{\"type\":\"turn.completed\"}'\n",
        encoding="utf-8",
    )
    runtime.chmod(0o755)
    listed_session_id = make_completed_runtime_session(
        root, runtime, session_id="session-1111111111111111"
    )

    async def list_completed() -> None:
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool("list_sessions", {"project_path": str(root)})
        assert result.is_error is False
        sessions = result.structured_content["result"]
        listed = next(record for record in sessions if record["id"] == listed_session_id)
        assert listed["state"] == "completed"

    asyncio.run(list_completed())
    inspected_session_id = make_completed_runtime_session(
        root, runtime, session_id="session-2222222222222222"
    )

    async def inspect_completed() -> None:
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool(
                "inspect_session",
                {"session_id": inspected_session_id, "project_path": str(root)},
            )
        assert result.is_error is False
        assert result.structured_content["result"]["state"] == "completed"

    asyncio.run(inspect_completed())
