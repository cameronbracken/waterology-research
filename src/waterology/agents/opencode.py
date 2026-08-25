from waterology.agents.base import (
    JsonEventAdapter,
    RuntimeCommand,
    RuntimeLaunch,
    nested_string,
)


class OpenCodeAdapter(JsonEventAdapter):
    name = "opencode"

    def build_command(self, launch: RuntimeLaunch) -> RuntimeCommand:
        arguments = [
            launch.executable,
            "run",
            "--format",
            "json",
            "--dir",
            str(launch.worktree),
            "--agent",
            launch.role,
        ]
        if launch.native_session_id:
            arguments.extend(("--session", launch.native_session_id))
        arguments.append(launch.prompt)
        return RuntimeCommand(tuple(arguments), launch.worktree)

    def native_session_id(self, event: dict[str, object]) -> str | None:
        return nested_string(
            event,
            ("sessionID",),
            ("session_id",),
            ("properties", "sessionID"),
            ("properties", "session_id"),
        )
