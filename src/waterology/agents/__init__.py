from waterology.agents.base import AdapterError, RuntimeAdapter
from waterology.agents.claude import ClaudeAdapter
from waterology.agents.codex import CodexAdapter
from waterology.agents.opencode import OpenCodeAdapter

_ADAPTERS: dict[str, RuntimeAdapter] = {
    "claude": ClaudeAdapter(),
    "codex": CodexAdapter(),
    "opencode": OpenCodeAdapter(),
}


def get_adapter(runtime: str) -> RuntimeAdapter:
    try:
        return _ADAPTERS[runtime]
    except KeyError as error:
        raise AdapterError(f"Unsupported agent runtime: {runtime}") from error


__all__ = ["get_adapter"]
