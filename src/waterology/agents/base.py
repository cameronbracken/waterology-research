import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from waterology.core.errors import WaterologyError


class AdapterError(WaterologyError):
    code = "agent_adapter_error"


@dataclass(frozen=True)
class RuntimeLaunch:
    executable: str
    worktree: Path
    prompt: str
    role: str
    native_session_id: str | None = None


@dataclass(frozen=True)
class RuntimeCommand:
    arguments: tuple[str, ...]
    cwd: Path


class RuntimeAdapter(Protocol):
    name: str

    def build_command(self, launch: RuntimeLaunch) -> RuntimeCommand: ...

    def parse_event(self, line: str) -> dict[str, object]: ...

    def native_session_id(self, event: dict[str, object]) -> str | None: ...


class JsonEventAdapter:
    name = "runtime"

    def parse_event(self, line: str) -> dict[str, object]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise AdapterError(f"{self.name} event is not a JSON object") from error
        if not isinstance(event, dict):
            raise AdapterError(f"{self.name} event is not a JSON object")
        return event


def nested_string(event: dict[str, object], *paths: tuple[str, ...]) -> str | None:
    for path in paths:
        value: object = event
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if isinstance(value, str) and value:
            return value
    return None
