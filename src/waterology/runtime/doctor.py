import shutil
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

from waterology.core.profiles import MachineConfigError, load_machine_config
from waterology.runtime.assets import AssetCatalog
from waterology.runtime.validate import validate_assets
from waterology.torc.gateway import TorcCliGateway, TorcError


@dataclass(frozen=True)
class Diagnostic:
    name: str
    status: Literal["pass", "warn", "fail"]
    message: str


def run_diagnostics(
    catalog: AssetCatalog,
    runtime: str | None = None,
    machine_config_file: Path | None = None,
    torc_profile: str | None = None,
) -> tuple[Diagnostic, ...]:
    issues = validate_assets(catalog)
    diagnostics = [
        Diagnostic(
            "assets",
            "fail" if issues else "pass",
            f"{len(issues)} asset validation issue(s)" if issues else "Assets are valid",
        )
    ]
    for name in ("claude", "codex", "opencode"):
        path = shutil.which(name)
        required = runtime == name
        diagnostics.append(
            Diagnostic(
                f"runtime:{name}",
                "pass" if path else ("fail" if required else "warn"),
                path or f"{name} command was not found",
            )
        )
    torc_path = shutil.which("torc")
    diagnostics.append(
        Diagnostic(
            "torc:binary",
            "pass" if torc_path else "warn",
            torc_path or "torc command was not found; direct execution remains available",
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
    dashboard_dependencies = all(
        find_spec(module) is not None for module in ("jinja2", "starlette", "uvicorn")
    )
    diagnostics.append(
        Diagnostic(
            "dashboard:dependencies",
            "pass" if dashboard_dependencies else "warn",
            (
                "Dashboard dependencies are installed"
                if dashboard_dependencies
                else "Install the dashboard package extra"
            ),
        )
    )
    try:
        machine = load_machine_config(machine_config_file)
    except MachineConfigError as error:
        diagnostics.append(Diagnostic("torc:profiles", "fail", str(error)))
    else:
        diagnostics.append(
            Diagnostic(
                "torc:profiles",
                "pass" if machine.profiles else "warn",
                (
                    f"{len(machine.profiles)} compute profile(s) are valid"
                    if machine.profiles
                    else "No TORC compute profiles are configured"
                ),
            )
        )
        if torc_profile:
            try:
                profile = machine.profile(torc_profile)
            except MachineConfigError as error:
                diagnostics.append(Diagnostic("torc:requested_profile", "fail", str(error)))
            else:
                diagnostics.append(
                    Diagnostic(
                        "torc:requested_profile",
                        "pass",
                        f"Compute profile is valid: {torc_profile}",
                    )
                )
                if torc_path:
                    gateway = TorcCliGateway(profile.api_url, executable=torc_path)
                    try:
                        version = gateway.version(cwd=catalog.root)
                        gateway.health(cwd=catalog.root)
                    except TorcError as error:
                        diagnostics.append(Diagnostic("torc:connectivity", "fail", str(error)))
                    else:
                        diagnostics.append(
                            Diagnostic(
                                "torc:connectivity",
                                "pass",
                                f"{version}; API is reachable",
                            )
                        )
                else:
                    diagnostics.append(
                        Diagnostic(
                            "torc:connectivity",
                            "fail",
                            "TORC connectivity requires the torc command",
                        )
                    )
    return tuple(diagnostics)
