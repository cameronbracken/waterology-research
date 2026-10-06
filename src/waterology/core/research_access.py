"""Credential presence only. Never return or retain credential values."""

import os

from waterology.core.credentials import PROVIDER_VARIABLES, last_credential_load


def research_access() -> dict:
    load = last_credential_load()
    missing = [
        name for name, variable in PROVIDER_VARIABLES.items() if not os.environ.get(variable)
    ]
    warnings = [
        f"{PROVIDER_VARIABLES[name]} is not available to this process; "
        f"authenticated {name} access is unavailable"
        for name in missing
    ]
    if load and load.problem:
        warnings.append(f"Credentials file {load.path or ''} was not used: {load.problem}")
    if missing:
        target = load.path if load and load.path else "the [credentials] file in config.toml"
        warnings.append(
            "MCP clients started outside your shell do not inherit direnv. "
            f"Add the missing keys to {target}, then restart the MCP server"
        )
    return {
        "providers": {
            name: {
                "environment_variable": variable,
                "credential_available": bool(os.environ.get(variable)),
            }
            for name, variable in PROVIDER_VARIABLES.items()
        },
        "credentials_file": load.summary() if load else None,
        "warnings": warnings,
        "validation": "Presence only; credentials and library permissions are not verified",
    }
