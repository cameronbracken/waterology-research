"""Fill missing research API keys from a private dotenv file. Never return or log values.

MCP clients often start servers outside the user's shell, so direnv never runs for them.
Reading the same dotenv file that direnv loads gives every process the same keys.
"""

import os
import stat
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path

PROVIDER_VARIABLES = {
    "zotero": "ZOTERO_API_KEY",
    "openalex": "OPENALEX_API_KEY",
    "semantic-scholar": "SEMANTIC_SCHOLAR_API_KEY",
}


@dataclass(frozen=True)
class CredentialLoad:
    path: Path | None
    loaded: tuple[str, ...] = ()
    problem: str | None = None

    def summary(self) -> dict:
        return {
            "path": str(self.path) if self.path else None,
            "loaded": list(self.loaded),
            "problem": self.problem,
        }


_last_load: CredentialLoad | None = None


def last_credential_load() -> CredentialLoad | None:
    return _last_load


def credentials_file_path() -> Path | None:
    from waterology.core.profiles import load_machine_config, machine_config_path

    config_path = machine_config_path()
    value = load_machine_config(config_path).credentials.file
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else config_path.parent / path


def load_credentials(
    path: Path | None = None, environment: MutableMapping[str, str] | None = None
) -> CredentialLoad:
    """Set provider variables that are missing from the environment. Existing values win."""
    global _last_load
    from waterology.core.profiles import MachineConfigError

    target = os.environ if environment is None else environment
    try:
        source = path or credentials_file_path()
    except MachineConfigError as error:
        result = CredentialLoad(None, problem=str(error))
    else:
        result = _load(source, target)
    _last_load = result
    return result


def _load(path: Path | None, environment: MutableMapping[str, str]) -> CredentialLoad:
    if path is None:
        return CredentialLoad(None)
    missing = [name for name in PROVIDER_VARIABLES.values() if not environment.get(name)]
    if not missing:
        return CredentialLoad(path)
    try:
        info = path.stat()
    except FileNotFoundError:
        return CredentialLoad(path, problem="file not found")
    except OSError as error:
        return CredentialLoad(path, problem=f"cannot read file ({error.strerror})")
    if not stat.S_ISREG(info.st_mode):
        return CredentialLoad(path, problem="not a regular file")
    if os.name != "nt" and info.st_mode & 0o077:
        return CredentialLoad(path, problem="readable by other users; run chmod 600 on it")

    from dotenv import dotenv_values

    try:
        values = dotenv_values(path, interpolate=False)
    except (OSError, UnicodeDecodeError, ValueError):
        return CredentialLoad(path, problem="could not parse file as dotenv")
    loaded = []
    for name in missing:
        if value := values.get(name):
            environment[name] = value
            loaded.append(name)
    return CredentialLoad(path, tuple(loaded))
