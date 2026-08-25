from waterology.agents.base import (
    JsonEventAdapter,
    RuntimeCommand,
    RuntimeLaunch,
    nested_string,
)


class CodexAdapter(JsonEventAdapter):
    name = "codex"

    def build_command(self, launch: RuntimeLaunch) -> RuntimeCommand:
        if launch.native_session_id:
            arguments = (
                launch.executable,
                "exec",
                "resume",
                "--json",
                launch.native_session_id,
                launch.prompt,
            )
        else:
            arguments = (
                launch.executable,
                "exec",
                "--json",
                "--cd",
                str(launch.worktree),
                launch.prompt,
            )
        return RuntimeCommand(arguments, launch.worktree)

    def native_session_id(self, event: dict[str, object]) -> str | None:
        return nested_string(
            event,
            ("thread_id",),
            ("threadId",),
            ("session_id",),
            ("sessionId",),
        )
