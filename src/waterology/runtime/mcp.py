from waterology.runtime.install import Runtime


def runtime_mcp_config(runtime: Runtime) -> dict[str, object]:
    if runtime is Runtime.CLAUDE:
        return {"mcpServers": {"waterology": {"command": "waterology-mcp"}}}
    if runtime is Runtime.CODEX:
        return {"mcp_servers": {"waterology": {"command": "waterology-mcp"}}}
    if runtime is Runtime.PI:
        raise ValueError("Pi has no built-in MCP registration; use the Waterology skills and CLI")
    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {
            "waterology": {
                "type": "local",
                "command": ["waterology-mcp"],
                "cwd": ".",
                "enabled": True,
            }
        },
    }


def registration_command(runtime: Runtime) -> tuple[str, ...] | None:
    if runtime is Runtime.CLAUDE:
        return (
            "claude",
            "mcp",
            "add",
            "--transport",
            "stdio",
            "--scope",
            "project",
            "waterology",
            "--",
            "waterology-mcp",
        )
    return None
