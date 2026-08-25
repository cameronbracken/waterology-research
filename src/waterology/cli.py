import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from waterology import __version__
from waterology.runtime.assets import AssetCatalog
from waterology.runtime.doctor import run_diagnostics
from waterology.runtime.install import (
    InstallConflict,
    InstallConflictError,
    InstallMode,
    InstallPlan,
    InstallScope,
    Runtime,
    apply_install_plan,
    build_install_plan,
    preflight,
)
from waterology.runtime.render import GeneratedAssetsStaleError, render_assets
from waterology.runtime.validate import ValidationIssue, validate_assets

app = typer.Typer(
    help="Waterology research workflows for Claude Code, Codex, and OpenCode.",
    no_args_is_help=True,
)

_INSTALL_SCOPE_OPTION = typer.Option(InstallScope.PROJECT, "--scope")
_INSTALL_TARGET_OPTION = typer.Option(Path("."), "--target")
_INSTALL_MODE_OPTION = typer.Option(InstallMode.COPY, "--mode")
_DOCTOR_RUNTIME_OPTION = typer.Option(None, "--runtime")


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version,
        is_eager=True,
        help="Show the Waterology version.",
    ),
) -> None:
    """Run Waterology commands."""


def _console() -> Console:
    return Console()


def _emit_json(payload: dict[str, object]) -> None:
    typer.echo(json.dumps(payload, sort_keys=True))


def _show_table(title: str, columns: tuple[str, ...], rows: Iterable[tuple[str, ...]]) -> None:
    table = Table(title=title)
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*row)
    _console().print(table)


def _validation_payload(issues: tuple[ValidationIssue, ...]) -> list[dict[str, str]]:
    return [asdict(issue) for issue in issues]


def _selected_runtimes(value: str) -> tuple[Runtime, ...]:
    if value == "all":
        return tuple(Runtime)
    try:
        return (Runtime(value),)
    except ValueError as error:
        raise typer.BadParameter(
            "must be one of: claude, codex, opencode, all",
            param_hint="runtime",
        ) from error


def _global_plan_conflicts(plans: tuple[InstallPlan, ...]) -> tuple[InstallConflict, ...]:
    owners: dict[Path, set[Runtime]] = {}
    for plan in plans:
        for action in plan.actions:
            owners.setdefault(action.destination, set()).add(plan.runtime)
        for manifest in {action.manifest for action in plan.actions}:
            owners.setdefault(manifest, set()).add(plan.runtime)
    return tuple(
        InstallConflict(path, "destination is planned by multiple runtime installs")
        for path, runtimes in sorted(owners.items(), key=lambda item: str(item[0]))
        if len(runtimes) > 1
    )


def _preflight_plans(
    plans: tuple[InstallPlan, ...],
    force: bool,
) -> tuple[InstallConflict, ...]:
    conflicts = list(_global_plan_conflicts(plans))
    for plan in plans:
        conflicts.extend(preflight(plan, force=force))
    return tuple(
        sorted(conflicts, key=lambda conflict: (str(conflict.destination), conflict.reason))
    )


def _install_payload(
    runtime: str,
    scope: InstallScope,
    mode: InstallMode,
    dry_run: bool,
) -> dict[str, object]:
    return {
        "dry_run": dry_run,
        "mode": mode.value,
        "runtime": runtime,
        "scope": scope.value,
    }


def _show_validation_issues(issues: tuple[ValidationIssue, ...]) -> None:
    _show_table(
        "Asset validation failed",
        ("Path", "Code", "Message"),
        ((issue.path, issue.code, issue.message) for issue in issues),
    )


def _show_install_conflicts(conflicts: tuple[InstallConflict, ...]) -> None:
    _show_table(
        "Install conflicts",
        ("Destination", "Reason"),
        ((str(conflict.destination), conflict.reason) for conflict in conflicts),
    )


def _conflict_payload(conflicts: tuple[InstallConflict, ...]) -> list[dict[str, str]]:
    return [
        {"destination": str(conflict.destination), "reason": conflict.reason}
        for conflict in conflicts
    ]


def _install_failure_payload(
    payload: dict[str, object],
    error: Exception,
    issues: tuple[ValidationIssue, ...] = (),
) -> dict[str, object]:
    conflicts = error.conflicts if isinstance(error, InstallConflictError) else ()
    return {
        **payload,
        "conflicts": _conflict_payload(conflicts),
        "error": {"message": str(error), "type": type(error).__name__},
        "issues": _validation_payload(issues),
        "status": "fail",
    }


def _show_install_failure(error: Exception, issues: tuple[ValidationIssue, ...] = ()) -> None:
    if issues:
        _show_validation_issues(issues)
    elif isinstance(error, InstallConflictError):
        _show_install_conflicts(error.conflicts)
    else:
        _show_table("Install failed", ("Error",), ((str(error),),))


@app.command()
def render(
    check: bool = typer.Option(False, "--check", help="Check generated assets without writing."),
) -> None:
    """Render generated runtime files."""
    catalog = AssetCatalog.discover()
    try:
        changed = render_assets(catalog, catalog.root, check=check)
    except GeneratedAssetsStaleError as error:
        _show_table(
            "Generated files are stale",
            ("Status", "Path"),
            (("stale", str(path)) for path in error.paths),
        )
        raise typer.Exit(1) from error
    if check:
        _show_table("Generated assets", ("Status",), (("Generated assets are current",),))
        return
    _show_table(
        "Generated assets",
        ("Status", "Files"),
        (("Rendered", str(len(changed))),),
    )


@app.command()
def install(
    ctx: typer.Context,
    runtime: str = typer.Argument(..., metavar="<claude|codex|opencode|all>"),
    scope: InstallScope = _INSTALL_SCOPE_OPTION,
    target: Path = _INSTALL_TARGET_OPTION,
    mode: InstallMode = _INSTALL_MODE_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Install runtime assets."""
    if scope is InstallScope.USER and ctx.get_parameter_source("target").name != "DEFAULT":
        raise typer.BadParameter("cannot be used with --scope user", param_hint="--target")

    runtimes = _selected_runtimes(runtime)
    payload = _install_payload(runtime, scope, mode, dry_run)
    try:
        catalog = AssetCatalog.discover()
        validation_issues = validate_assets(catalog)
        if validation_issues:
            error = ValueError("Waterology assets failed validation")
            if json_output:
                _emit_json(_install_failure_payload(payload, error, validation_issues))
            else:
                _show_install_failure(error, validation_issues)
            raise typer.Exit(1)

        plans = tuple(
            build_install_plan(selected, scope, target, mode, catalog) for selected in runtimes
        )
        conflicts = _preflight_plans(plans, force)
        if conflicts:
            raise InstallConflictError(conflicts)

        if dry_run:
            plans_payload = {
                plan.runtime.value: [str(action.destination) for action in plan.actions]
                for plan in plans
            }
            if json_output:
                _emit_json({**payload, "plans": plans_payload, "status": "pass"})
            else:
                _show_table(
                    "Install dry run",
                    ("Runtime", "Assets"),
                    ((name, str(len(actions))) for name, actions in plans_payload.items()),
                )
            return

        results = {}
        for plan in plans:
            result = apply_install_plan(plan, force=force)
            results[plan.runtime.value] = {
                "changed": [str(path) for path in result.changed],
                "manifests": [str(path) for path in result.manifests],
                "unchanged": [str(path) for path in result.unchanged],
            }
    except (InstallConflictError, OSError, TypeError, ValueError) as error:
        if json_output:
            _emit_json(_install_failure_payload(payload, error))
        else:
            _show_install_failure(error)
        raise typer.Exit(1) from error

    if json_output:
        _emit_json({**payload, "results": results, "status": "pass"})
        return
    _show_table(
        "Install complete",
        ("Runtime", "Changed", "Unchanged"),
        (
            (name, str(len(result["changed"])), str(len(result["unchanged"])))
            for name, result in results.items()
        ),
    )


@app.command()
def doctor(
    runtime: Runtime | None = _DOCTOR_RUNTIME_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Check runtime commands and packaged assets."""
    requested_runtime = runtime.value if runtime is not None else None
    diagnostics = run_diagnostics(AssetCatalog.discover(), requested_runtime)
    assets = next(diagnostic for diagnostic in diagnostics if diagnostic.name == "assets")
    runtimes = {
        diagnostic.name.removeprefix("runtime:"): {
            "message": diagnostic.message,
            "status": diagnostic.status,
        }
        for diagnostic in diagnostics
        if diagnostic.name.startswith("runtime:")
    }
    if json_output:
        _emit_json(
            {
                "assets": {"message": assets.message, "status": assets.status},
                "requested_runtime": requested_runtime,
                "runtimes": runtimes,
            }
        )
    else:
        _show_table(
            "Waterology doctor",
            ("Check", "Status", "Message"),
            (
                (diagnostic.name, diagnostic.status, diagnostic.message)
                for diagnostic in diagnostics
            ),
        )
    if any(diagnostic.status == "fail" for diagnostic in diagnostics):
        raise typer.Exit(1)
