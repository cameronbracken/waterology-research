import shutil
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

from waterology.core.user_settings import UserConfigError, load_user_config
from waterology.runtime.assets import AssetCatalog
from waterology.runtime.validate import validate_assets


@dataclass(frozen=True)
class Diagnostic:
    name: str
    status: Literal["pass", "warn", "fail"]
    message: str


_RUNTIME_COMMANDS: dict[str, str] = {
    "antigravity": "agy",
    "claude": "claude",
    "codex": "codex",
    "opencode": "opencode",
    "pi": "pi",
}


def run_diagnostics(
    catalog: AssetCatalog,
    runtime: str | None = None,
    user_config_file: Path | None = None,
) -> tuple[Diagnostic, ...]:
    issues = validate_assets(catalog)
    diagnostics = [
        Diagnostic(
            "assets",
            "fail" if issues else "pass",
            f"{len(issues)} asset validation issue(s)" if issues else "Assets are valid",
        )
    ]
    for name, command in _RUNTIME_COMMANDS.items():
        path = shutil.which(command)
        required = runtime == name
        diagnostics.append(
            Diagnostic(
                f"runtime:{name}",
                "pass" if path else ("fail" if required else "warn"),
                path or f"{command} command was not found",
            )
        )
    mcp_available = find_spec("mcp") is not None
    diagnostics.append(
        Diagnostic(
            "mcp:sdk",
            "pass" if mcp_available else "warn",
            "MCP Python SDK is installed" if mcp_available else "Install the mcp package extra",
        )
    )
    mcp_server = shutil.which("waterology-mcp")
    diagnostics.append(
        Diagnostic(
            "mcp:server",
            "pass" if mcp_server else "warn",
            mcp_server or "waterology-mcp entry point was not found",
        )
    )
    zotero_available = find_spec("pyzotero") is not None
    diagnostics.append(
        Diagnostic(
            "zotero:sdk",
            "pass" if zotero_available else "warn",
            "Pyzotero is installed" if zotero_available else "Install the zotero package extra",
        )
    )
    try:
        load_user_config(user_config_file)
    except UserConfigError as error:
        diagnostics.append(Diagnostic("user:config", "fail", str(error)))
    else:
        diagnostics.append(Diagnostic("user:config", "pass", "User configuration is valid"))
    return tuple(diagnostics)
