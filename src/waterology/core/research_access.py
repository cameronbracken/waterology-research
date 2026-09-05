"""Credential presence only. Never return or retain credential values."""

import os


def research_access() -> dict:
    providers = {"zotero": "ZOTERO_API_KEY", "openalex": "OPENALEX_API_KEY"}
    return {
        "providers": {
            name: {
                "environment_variable": variable,
                "credential_available": bool(os.environ.get(variable)),
            }
            for name, variable in providers.items()
        },
        "warnings": [
            f"{variable} is not available to this process; authenticated {name} access is unavailable"
            for name, variable in providers.items()
            if not os.environ.get(variable)
        ],
        "validation": "Presence only; credentials and library permissions are not verified",
    }
