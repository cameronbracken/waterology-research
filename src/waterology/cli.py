import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from waterology import __version__
from waterology.core.archive import (
    list_archives,
    load_archive,
    read_archive_logs,
    verify_project_archive,
)
from waterology.core.assessments import assess_run
from waterology.core.errors import InvalidInputError, WaterologyError
from waterology.core.execution import start_direct_run
from waterology.core.experiments import (
    add_experiment_note,
    create_experiment,
    list_experiment_notes,
    list_experiments,
    list_worktrees,
    load_experiment,
    load_worktree,
)
from waterology.core.project import initialize_project, inspect_project
from waterology.core.repair import repair_index
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
experiment_app = typer.Typer(help="Create and inspect research experiments.")
worktree_app = typer.Typer(help="Inspect experiment worktrees.")
archive_app = typer.Typer(help="Inspect and verify sealed run archives.")
run_app = typer.Typer(help="Run committed experiment variants.")
app.add_typer(experiment_app, name="experiment")
app.add_typer(worktree_app, name="worktree")
app.add_typer(archive_app, name="archive")
app.add_typer(run_app, name="run")

_INSTALL_SCOPE_OPTION = typer.Option(InstallScope.PROJECT, "--scope")
_INSTALL_TARGET_OPTION = typer.Option(Path("."), "--target")
_INSTALL_MODE_OPTION = typer.Option(InstallMode.COPY, "--mode")
_DOCTOR_RUNTIME_OPTION = typer.Option(None, "--runtime")
_PROJECT_PATH_OPTION = typer.Option(Path("."), "--path")
_EVIDENCE_OPTION = typer.Option(None, "--evidence")


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


def _core_failure_payload(error: WaterologyError) -> dict[str, object]:
    return {"error": error.payload(), "status": "fail"}


def _normalized_core_error(error: WaterologyError | ValueError) -> WaterologyError:
    if isinstance(error, WaterologyError):
        return error
    return InvalidInputError(str(error))


def _record_payload(record: BaseModel) -> dict[str, object]:
    return record.model_dump(mode="json")


def _show_core_failure(
    error: WaterologyError | ValueError,
    *,
    json_output: bool,
    title: str,
) -> None:
    normalized = _normalized_core_error(error)
    if json_output:
        _emit_json(_core_failure_payload(normalized))
    else:
        _show_table(title, ("Error",), ((str(normalized),),))


@app.command("init")
def init_project_command(
    path: Path = _PROJECT_PATH_OPTION,
    name: str | None = typer.Option(None, "--name"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Initialize a Waterology project at a Git repository root."""
    try:
        result = initialize_project(path, name=name)
    except WaterologyError as error:
        if json_output:
            _emit_json(_core_failure_payload(error))
        else:
            _show_table("Initialization failed", ("Error",), ((str(error),),))
        raise typer.Exit(1) from error

    payload = {
        "created_config": result.created_config,
        "project": {
            "name": result.project.config.name,
            "root": str(result.project.root),
        },
        "status": "pass",
        "updated_gitignore": result.updated_gitignore,
    }
    if json_output:
        _emit_json(payload)
        return
    _show_table(
        "Waterology project",
        ("Project", "Root", "Configuration"),
        (
            (
                result.project.config.name,
                str(result.project.root),
                "created" if result.created_config else "existing",
            ),
        ),
    )


@app.command("status")
def project_status_command(
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show local Waterology project state."""
    try:
        result = inspect_project(path)
    except WaterologyError as error:
        if json_output:
            _emit_json(_core_failure_payload(error))
        else:
            _show_table("Project status failed", ("Error",), ((str(error),),))
        raise typer.Exit(1) from error

    payload = {
        "project": {
            "name": result.project.config.name,
            "root": str(result.project.root),
            "schema_version": result.project.config.schema_version,
        },
        "state": {
            "assessments": result.assessments,
            "database_exists": result.database_exists,
            "experiments": result.experiments,
            "runs": result.runs,
        },
        "status": "pass",
    }
    if json_output:
        _emit_json(payload)
        return
    _show_table(
        "Waterology project status",
        ("Project", "Experiments", "Runs", "Assessments", "Index"),
        (
            (
                result.project.config.name,
                str(result.experiments),
                str(result.runs),
                str(result.assessments),
                "present" if result.database_exists else "not created",
            ),
        ),
    )


@app.command("repair-index")
def repair_index_command(
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Rebuild the SQLite index from durable project records."""
    if not json_output:
        _console().print("Rebuilding the Waterology index...")
    try:
        result = repair_index(path)
    except (WaterologyError, ValueError, OSError) as error:
        normalized = (
            error
            if isinstance(error, (WaterologyError, ValueError))
            else InvalidInputError(str(error))
        )
        _show_core_failure(normalized, json_output=json_output, title="Index repair failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({"result": _record_payload(result), "status": "pass"})
        return
    _show_table(
        "Index repaired",
        ("Projects", "Experiments", "Runs", "Assessments", "Artifacts"),
        (
            (
                str(result.projects),
                str(result.experiments),
                str(result.runs),
                str(result.assessments),
                str(result.artifacts),
            ),
        ),
    )


@experiment_app.command("create")
def experiment_create_command(
    hypothesis: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    experiment_id: str | None = typer.Option(None, "--id"),
    parent_ref: str = typer.Option("HEAD", "--parent"),
    parent_experiment_id: str | None = typer.Option(None, "--parent-experiment"),
    owner: str | None = typer.Option(None, "--owner"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Create a hypothesis branch and isolated worktree."""
    try:
        experiment = create_experiment(
            path,
            hypothesis=hypothesis,
            parent_ref=parent_ref,
            parent_experiment_id=parent_experiment_id,
            owner=owner,
            experiment_id=experiment_id,
        )
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Experiment creation failed")
        raise typer.Exit(1) from error
    payload = {"experiment": _record_payload(experiment), "status": "pass"}
    if json_output:
        _emit_json(payload)
        return
    _show_table(
        "Experiment created",
        ("ID", "Branch", "Worktree"),
        ((experiment.id, experiment.branch, experiment.worktree),),
    )


@experiment_app.command("list")
def experiment_list_command(
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List experiments from durable records."""
    try:
        experiments = list_experiments(path)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Experiment listing failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json(
            {
                "experiments": [_record_payload(experiment) for experiment in experiments],
                "status": "pass",
            }
        )
        return
    _show_table(
        "Experiments",
        ("ID", "Status", "Branch", "Hypothesis"),
        (
            (experiment.id, experiment.status, experiment.branch, experiment.hypothesis)
            for experiment in experiments
        ),
    )


@experiment_app.command("show")
def experiment_show_command(
    experiment_id: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show an experiment and its notes."""
    try:
        experiment = load_experiment(path, experiment_id)
        notes = list_experiment_notes(path, experiment_id)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Experiment lookup failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json(
            {
                "experiment": _record_payload(experiment),
                "notes": [_record_payload(note) for note in notes],
                "status": "pass",
            }
        )
        return
    _show_table(
        "Experiment",
        ("ID", "Status", "Branch", "Hypothesis", "Notes"),
        (
            (
                experiment.id,
                experiment.status,
                experiment.branch,
                experiment.hypothesis,
                str(len(notes)),
            ),
        ),
    )


@experiment_app.command("note")
def experiment_note_command(
    experiment_id: str = typer.Argument(...),
    text: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    author: str | None = typer.Option(None, "--author"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Append a note to an experiment."""
    try:
        note = add_experiment_note(path, experiment_id, text, author=author)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Experiment note failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({"note": _record_payload(note), "status": "pass"})
        return
    _show_table("Experiment note", ("Experiment", "Note"), ((experiment_id, note.id),))


@worktree_app.command("list")
def worktree_list_command(
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List experiment worktrees."""
    try:
        worktrees = list_worktrees(path)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Worktree listing failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json(
            {
                "status": "pass",
                "worktrees": [_record_payload(worktree) for worktree in worktrees],
            }
        )
        return
    _show_table(
        "Experiment worktrees",
        ("Experiment", "Branch", "Path", "Status"),
        (
            (
                worktree.experiment_id,
                worktree.branch,
                worktree.path,
                "present" if worktree.exists else "missing",
            )
            for worktree in worktrees
        ),
    )


@worktree_app.command("open")
def worktree_open_command(
    experiment_id: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Resolve an experiment worktree path."""
    try:
        worktree = load_worktree(path, experiment_id)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Worktree lookup failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({"status": "pass", "worktree": _record_payload(worktree)})
        return
    typer.echo(worktree.path)


@archive_app.command("list")
def archive_list_command(
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List sealed run archives."""
    try:
        archives = list_archives(path)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Archive listing failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json(
            {
                "archives": [_record_payload(archive) for archive in archives],
                "status": "pass",
            }
        )
        return
    _show_table(
        "Run archives",
        ("Run", "Experiment", "State", "Commit"),
        (
            (
                archive.run_id,
                archive.experiment_id,
                archive.terminal_state,
                archive.commit_sha[:12],
            )
            for archive in archives
        ),
    )


@archive_app.command("show")
def archive_show_command(
    run_id: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show a sealed run archive manifest."""
    try:
        archive = load_archive(path, run_id)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Archive lookup failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({"archive": _record_payload(archive), "status": "pass"})
        return
    _show_table(
        "Run archive",
        ("Run", "Experiment", "State", "Commit", "Artifacts"),
        (
            (
                archive.run_id,
                archive.experiment_id,
                archive.terminal_state,
                archive.commit_sha,
                str(len(archive.collected_artifacts)),
            ),
        ),
    )


@archive_app.command("verify")
def archive_verify_command(
    run_id: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Verify every sealed archive payload against its checksum."""
    try:
        verification = verify_project_archive(path, run_id)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Archive verification failed")
        raise typer.Exit(1) from error
    status = "pass" if verification.valid else "fail"
    if json_output:
        _emit_json({"status": status, "verification": _record_payload(verification)})
    else:
        _show_table(
            "Archive verification",
            ("Run", "Status", "Missing", "Changed", "Unexpected"),
            (
                (
                    verification.run_id,
                    status,
                    str(len(verification.missing)),
                    str(len(verification.changed)),
                    str(len(verification.unexpected)),
                ),
            ),
        )
    if not verification.valid:
        raise typer.Exit(1)


@run_app.command("start")
def run_start_command(
    experiment_id: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    run_id: str | None = typer.Option(None, "--id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run a clean committed variant with the direct provider."""
    if not json_output:
        _console().print(f"Starting direct run for {experiment_id}...")
    try:
        run = start_direct_run(path, experiment_id, run_id=run_id)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Run failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({"run": _record_payload(run), "status": "pass"})
        return
    _show_table(
        "Run complete",
        ("Run", "Experiment", "State", "Exit code"),
        ((run.run_id, run.experiment_id, run.terminal_state, str(run.exit_code)),),
    )


@run_app.command("list")
def run_list_command(
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List terminal runs."""
    try:
        runs = list_archives(path)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Run listing failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({"runs": [_record_payload(run) for run in runs], "status": "pass"})
        return
    _show_table(
        "Runs",
        ("Run", "Experiment", "State", "Started"),
        ((run.run_id, run.experiment_id, run.terminal_state, run.started_at) for run in runs),
    )


@run_app.command("status")
def run_status_command(
    run_id: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show terminal run state."""
    try:
        run = load_archive(path, run_id)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Run lookup failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({"run": _record_payload(run), "status": "pass"})
        return
    _show_table(
        "Run status",
        ("Run", "Experiment", "State", "Exit code"),
        ((run.run_id, run.experiment_id, run.terminal_state, str(run.exit_code)),),
    )


@run_app.command("logs")
def run_logs_command(
    run_id: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Read terminal run logs."""
    try:
        logs = read_archive_logs(path, run_id)
    except (WaterologyError, ValueError, OSError) as error:
        normalized = (
            error
            if isinstance(error, (WaterologyError, ValueError))
            else InvalidInputError(str(error))
        )
        _show_core_failure(normalized, json_output=json_output, title="Run log lookup failed")
        raise typer.Exit(1) from error
    if json_output:
        _emit_json({"logs": logs, "run_id": run_id, "status": "pass"})
        return
    typer.echo(logs["stdout"], nl=not logs["stdout"].endswith("\n"))
    if logs["stderr"]:
        _console().print("stderr:")
        typer.echo(logs["stderr"], nl=not logs["stderr"].endswith("\n"))


@run_app.command("assess")
def run_assess_command(
    run_id: str = typer.Argument(...),
    kind: str = typer.Argument(..., metavar="<invalid|no_answer|answer>"),
    conclusion: str = typer.Argument(...),
    path: Path = _PROJECT_PATH_OPTION,
    author: str = typer.Option(..., "--author"),
    evidence: list[str] | None = _EVIDENCE_OPTION,
    note: str | None = typer.Option(None, "--note"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Append a scientific assessment to a terminal run."""
    try:
        assessment = assess_run(
            path,
            run_id,
            kind=kind,
            conclusion=conclusion,
            author=author,
            evidence=tuple(evidence or ()),
            note=note,
        )
        experiment = load_experiment(path, assessment.experiment_id)
    except (WaterologyError, ValueError) as error:
        _show_core_failure(error, json_output=json_output, title="Run assessment failed")
        raise typer.Exit(1) from error
    payload = {
        "assessment": _record_payload(assessment),
        "experiment": _record_payload(experiment),
        "status": "pass",
    }
    if json_output:
        _emit_json(payload)
        return
    _show_table(
        "Run assessment",
        ("Run", "Assessment", "Experiment status"),
        ((run_id, assessment.kind, experiment.status),),
    )


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
