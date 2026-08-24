import shutil
from dataclasses import dataclass
from typing import Literal

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.validate import validate_assets


@dataclass(frozen=True)
class Diagnostic:
    name: str
    status: Literal["pass", "warn", "fail"]
    message: str


def run_diagnostics(
    catalog: AssetCatalog,
    runtime: str | None = None,
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
    return tuple(diagnostics)
