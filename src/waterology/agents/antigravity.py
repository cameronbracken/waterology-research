from waterology.agents.base import (
    JsonEventAdapter,
    RuntimeCommand,
    RuntimeLaunch,
    nested_string,
)


class AntigravityAdapter(JsonEventAdapter):
    name = "antigravity"
    default_executable = "agy"

    def build_command(self, launch: RuntimeLaunch) -> RuntimeCommand:
        arguments = [
            launch.executable,
            "-p",
            launch.prompt,
            "--output-format",
            "stream-json",
            "--agent",
            launch.role,
        ]
        if launch.native_session_id:
            arguments.extend(["--conversation", launch.native_session_id])
        return RuntimeCommand(tuple(arguments), launch.worktree)

    def native_session_id(self, event: dict[str, object]) -> str | None:
        return nested_string(
            event,
            ("conversation_id",),
            ("conversationId",),
            ("init", "conversation_id"),
            ("step_update", "conversation_id"),
            ("result", "conversation_id"),
            ("session_id",),
        )
