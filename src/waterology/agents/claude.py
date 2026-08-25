from waterology.agents.base import (
    JsonEventAdapter,
    RuntimeCommand,
    RuntimeLaunch,
    nested_string,
)


class ClaudeAdapter(JsonEventAdapter):
    name = "claude"

    def build_command(self, launch: RuntimeLaunch) -> RuntimeCommand:
        arguments = [
            launch.executable,
            "-p",
            launch.prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--agent",
            launch.role,
        ]
        if launch.native_session_id:
            arguments.extend(("--resume", launch.native_session_id))
        return RuntimeCommand(tuple(arguments), launch.worktree)

    def native_session_id(self, event: dict[str, object]) -> str | None:
        return nested_string(event, ("session_id",), ("sessionId",))
