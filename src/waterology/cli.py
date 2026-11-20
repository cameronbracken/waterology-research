import json
import shlex
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
    apply_uninstall_plan,
    build_install_plan,
    build_uninstall_plan,
    preflight,
    recover_install,
    uninstall_paths,
    uninstall_preflight,
)
from waterology.runtime.mcp import registration_command, runtime_mcp_config
from waterology.runtime.render import GeneratedAssetsStaleError, render_assets
from waterology.runtime.validate import ValidationIssue, validate_assets
from waterology.user_config_cli import register_user_config_commands
from waterology.workflow_cli import OUTPUT_FORMAT, register_reference_commands

app = typer.Typer(
    help="Waterology research skills, deliverable verifiers, and reference tools.",
    no_args_is_help=True,
)
mcp_app = typer.Typer(help="Inspect local MCP server registration.")
config_app = typer.Typer(help="Inspect or initialize private user configuration.")
app.add_typer(mcp_app, name="mcp")
app.add_typer(config_app, name="config")
register_reference_commands(app)
register_user_config_commands(config_app)

_INSTALL_SCOPE_OPTION = typer.Option(InstallScope.PROJECT, "--scope")
_INSTALL_TARGET_OPTION = typer.Option(Path("."), "--target")
_INSTALL_MODE_OPTION = typer.Option(InstallMode.COPY, "--mode")
_DOCTOR_RUNTIME_OPTION = typer.Option(None, "--runtime")
_MCP_RUNTIME_ARGUMENT = typer.Argument(...)


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    output_format: str = typer.Option(
        "yaml", "--output-format", help="Reference and dataset output format: yaml or json."
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version,
        is_eager=True,
        help="Show the Waterology version.",
    ),
) -> None:
    """Run Waterology commands."""
    if output_format not in {"yaml", "json"}:
        raise typer.BadParameter("Use yaml or json")
    from waterology.core.credentials import load_credentials

    load_credentials()
    OUTPUT_FORMAT.set(output_format)


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
            "must be one of: antigravity, claude, codex, opencode, pi, all",
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
def validate(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Validate canonical skills, agents, manifests, and generated runtime files."""
    issues = validate_assets(AssetCatalog.discover())
    if json_output:
        _emit_json(
            {
                "issues": _validation_payload(issues),
                "status": "fail" if issues else "pass",
            }
        )
    elif issues:
        _show_validation_issues(issues)
    else:
        _show_table("Asset validation", ("Status",), (("Assets are valid",),))
    if issues:
        raise typer.Exit(1)


@mcp_app.command("config")
def mcp_config_command(
    runtime: Runtime = _MCP_RUNTIME_ARGUMENT,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Print a machine neutral MCP registration snippet for one runtime."""
    try:
        config = runtime_mcp_config(runtime)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="runtime") from error
    command = registration_command(runtime)
    if json_output:
        _emit_json(
            {
                "command": list(command) if command else None,
                "config": config,
                "runtime": runtime.value,
                "status": "pass",
            }
        )
        return
    if command:
        typer.echo(shlex.join(command))
    typer.echo(json.dumps(config, indent=2, sort_keys=True))


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
    runtime: str = typer.Argument(..., metavar="<antigravity|claude|codex|opencode|pi|all>"),
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


@app.command("install-recover")
def install_recover(
    ctx: typer.Context,
    runtime: Runtime,
    scope: InstallScope = _INSTALL_SCOPE_OPTION,
    target: Path = _INSTALL_TARGET_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Recover an interrupted CLI install or uninstall after its process exits."""
    if scope is InstallScope.USER and ctx.get_parameter_source("target").name != "DEFAULT":
        raise typer.BadParameter("cannot be used with --scope user", param_hint="--target")
    payload = {"runtime": runtime.value, "scope": scope.value, "dry_run": dry_run}
    try:
        plan = build_install_plan(runtime, scope, target, InstallMode.COPY, AssetCatalog.discover())
        recovered = recover_install(plan, dry_run)
    except (InstallConflictError, OSError, TypeError, ValueError) as error:
        if json_output:
            _emit_json(_install_failure_payload(payload, error))
        else:
            _show_install_failure(error)
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({**payload, "status": "pass", "paths": [str(path) for path in recovered]})
    else:
        _show_table(
            "Recovery dry run" if dry_run else "Recovery complete",
            ("Paths",),
            ((str(len(recovered)),),),
        )


@app.command()
def uninstall(
    ctx: typer.Context,
    runtime: str = typer.Argument(..., metavar="<antigravity|claude|codex|opencode|pi|all>"),
    scope: InstallScope = _INSTALL_SCOPE_OPTION,
    target: Path = _INSTALL_TARGET_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Remove unchanged Waterology assets recorded by the CLI installer."""
    if scope is InstallScope.USER and ctx.get_parameter_source("target").name != "DEFAULT":
        raise typer.BadParameter("cannot be used with --scope user", param_hint="--target")
    runtimes = _selected_runtimes(runtime)
    payload = {"runtime": runtime, "scope": scope.value, "dry_run": dry_run}
    manual = [
        "Native marketplace plugins, external MCP registrations, and the Python package use their own uninstall commands."
    ]
    try:
        catalog = AssetCatalog.discover()
        plans = tuple(
            build_uninstall_plan(selected, scope, target, catalog) for selected in runtimes
        )
        conflicts = tuple(conflict for plan in plans for conflict in uninstall_preflight(plan))
        if conflicts:
            raise InstallConflictError(conflicts)
        results = {}
        for plan in plans:
            paths = uninstall_paths(plan) if dry_run else apply_uninstall_plan(plan).changed
            results[plan.runtime.value] = [str(path) for path in paths]
    except (InstallConflictError, OSError, TypeError, ValueError) as error:
        if json_output:
            _emit_json({**_install_failure_payload(payload, error), "manual_cleanup": manual})
        else:
            _show_install_failure(error)
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({**payload, "status": "pass", "results": results, "manual_cleanup": manual})
    else:
        _show_table(
            "Uninstall dry run" if dry_run else "Uninstall complete",
            ("Runtime", "Assets"),
            ((name, str(len(paths))) for name, paths in results.items()),
        )
        Console().print(manual[0])


@app.command()
def doctor(
    runtime: Runtime | None = _DOCTOR_RUNTIME_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Check runtime commands, MCP/Zotero extras, user settings, and packaged assets."""
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
    mcp = {
        diagnostic.name.removeprefix("mcp:"): {
            "message": diagnostic.message,
            "status": diagnostic.status,
        }
        for diagnostic in diagnostics
        if diagnostic.name.startswith("mcp:")
    }
    zotero = {
        diagnostic.name.removeprefix("zotero:"): {
            "message": diagnostic.message,
            "status": diagnostic.status,
        }
        for diagnostic in diagnostics
        if diagnostic.name.startswith("zotero:")
    }
    user = {
        diagnostic.name.removeprefix("user:"): {
            "message": diagnostic.message,
            "status": diagnostic.status,
        }
        for diagnostic in diagnostics
        if diagnostic.name.startswith("user:")
    }
    if json_output:
        _emit_json(
            {
                "assets": {"message": assets.message, "status": assets.status},
                "mcp": mcp,
                "requested_runtime": requested_runtime,
                "runtimes": runtimes,
                "user": user,
                "zotero": zotero,
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
