import json
from pathlib import Path

import pytest

from waterology.agents import get_adapter
from waterology.agents.base import AdapterError, RuntimeLaunch


def launch(tmp_path: Path, runtime: str, native_id: str | None = None) -> RuntimeLaunch:
    return RuntimeLaunch(
        executable=runtime,
        worktree=tmp_path,
        prompt="Inspect the experiment and record evidence.",
        role="researcher",
        native_session_id=native_id,
    )


def test_claude_builds_structured_launch_and_native_resume(tmp_path: Path) -> None:
    adapter = get_adapter("claude")

    initial = adapter.build_command(launch(tmp_path, "claude"))
    resumed = adapter.build_command(launch(tmp_path, "claude", "claude-session"))

    assert initial.cwd == tmp_path
    assert initial.arguments == (
        "claude",
        "-p",
        "Inspect the experiment and record evidence.",
        "--output-format",
        "stream-json",
        "--verbose",
        "--agent",
        "researcher",
    )
    assert resumed.arguments[0:2] == ("claude", "-p")
    assert resumed.arguments[-2:] == ("--resume", "claude-session")


def test_codex_builds_structured_launch_and_native_resume(tmp_path: Path) -> None:
    adapter = get_adapter("codex")

    initial = adapter.build_command(launch(tmp_path, "codex"))
    resumed = adapter.build_command(launch(tmp_path, "codex", "thread-123"))

    assert initial.arguments == (
        "codex",
        "exec",
        "--json",
        "--cd",
        str(tmp_path),
        "Inspect the experiment and record evidence.",
    )
    assert resumed.arguments == (
        "codex",
        "exec",
        "resume",
        "--json",
        "thread-123",
        "Inspect the experiment and record evidence.",
    )
    assert resumed.cwd == tmp_path


def test_opencode_builds_structured_launch_and_native_resume(tmp_path: Path) -> None:
    adapter = get_adapter("opencode")

    initial = adapter.build_command(launch(tmp_path, "opencode"))
    resumed = adapter.build_command(launch(tmp_path, "opencode", "ses_123"))

    assert initial.arguments == (
        "opencode",
        "run",
        "--format",
        "json",
        "--dir",
        str(tmp_path),
        "--agent",
        "researcher",
        "Inspect the experiment and record evidence.",
    )
    assert resumed.arguments[-3:] == (
        "--session",
        "ses_123",
        "Inspect the experiment and record evidence.",
    )


@pytest.mark.parametrize(
    ("runtime", "event", "expected"),
    [
        ("claude", {"type": "system", "subtype": "init", "session_id": "abc"}, "abc"),
        ("claude", {"type": "result", "session_id": "abc"}, "abc"),
        ("codex", {"type": "thread.started", "thread_id": "019c"}, "019c"),
        ("opencode", {"type": "session.created", "properties": {"sessionID": "ses_x"}}, "ses_x"),
        ("opencode", {"type": "step_start", "sessionID": "ses_x"}, "ses_x"),
    ],
)
def test_adapters_extract_native_session_ids(
    runtime: str, event: dict[str, object], expected: str
) -> None:
    assert get_adapter(runtime).native_session_id(event) == expected


@pytest.mark.parametrize(
    ("runtime", "line"),
    [
        ("claude", "not-json"),
        ("codex", "[]"),
        ("opencode", json.dumps("text")),
    ],
)
def test_adapters_reject_malformed_event_lines(runtime: str, line: str) -> None:
    with pytest.raises(AdapterError, match="JSON object"):
        get_adapter(runtime).parse_event(line)


def test_get_adapter_rejects_unknown_runtime() -> None:
    with pytest.raises(AdapterError, match="Unsupported agent runtime"):
        get_adapter("shell")
