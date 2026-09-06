"""CLI entry points for project registration and reproducibility."""

from functools import wraps
from pathlib import Path

import typer

from waterology.core.config import DeliverableConfig, WorkflowConfig
from waterology.core.errors import WaterologyError
from waterology.core.formats import load_document
from waterology.core.project import discover_project
from waterology.core.registry import refresh_configuration, register_workflow
from waterology.core.workflows import run_workflow, watch_workflow
from waterology.workflow_cli import emit

_PATH = typer.Option(Path("."), "--path")
config_app = typer.Typer(help="Discover, refresh and inspect project configuration.")
workflow_app = typer.Typer(help="Register and execute named workflows through TORC.")
deliverable_app = typer.Typer(help="Select and export reproducible deliverables.")


def _handled(operation):
    @wraps(operation)
    def guarded(*args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except (ValueError, OSError, WaterologyError) as error:
            emit({"error": str(error)})
            raise typer.Exit(1) from error

    return guarded


@config_app.command("refresh")
@_handled
def refresh(path: Path = _PATH, check: bool = False):
    result = refresh_configuration(path, check=check)
    emit(result)
    if check and (result["changed"] or result["drift"]):
        raise typer.Exit(1)


@config_app.command("show")
@_handled
def show(path: Path = _PATH):
    emit(discover_project(path).config)


@config_app.command("schema")
@_handled
def schema():
    from waterology.core.config import ProjectConfig

    emit(ProjectConfig.model_json_schema())


@workflow_app.command("list")
@_handled
def list_workflows(path: Path = _PATH):
    emit(
        {
            name: value.model_dump(mode="json")
            for name, value in discover_project(path).config.workflows.items()
        }
    )


@workflow_app.command("register")
@_handled
def register(
    name: str,
    definition: Path | None = None,
    torc: str | None = None,
    task: str | None = None,
    path: Path = _PATH,
):
    if sum(value is not None for value in (definition, torc, task)) != 1:
        raise typer.BadParameter("Choose --definition, --torc or --task")
    if definition:
        workflow = WorkflowConfig.model_validate(load_document(definition))
    elif torc:
        workflow = WorkflowConfig(torc_file=torc)
    else:
        from waterology.core.registry import discover_configuration

        detected = discover_configuration(discover_project(path).root)
        if task not in detected["workflows"]:
            raise typer.BadParameter("Task was not discovered; use an explicit definition")
        workflow = WorkflowConfig.model_validate(detected["workflows"][task])
    emit(register_workflow(path, name, workflow))


@workflow_app.command("run")
@_handled
def run(
    name: str,
    profile: str | None = None,
    path: Path = _PATH,
    detach: bool = False,
    confirm_remote: bool = False,
):
    result = run_workflow(path, name, profile=profile, confirm_remote=confirm_remote)
    emit(result)
    if not detach:
        result = watch_workflow(path, result.run_id, progress=emit)
        if getattr(result, "terminal_state", None) != "completed":
            raise typer.Exit(1)


@workflow_app.command("watch")
@_handled
def watch(run_id: str, path: Path = _PATH):
    result = watch_workflow(path, run_id, progress=emit)
    if getattr(result, "terminal_state", None) != "completed":
        raise typer.Exit(1)


@deliverable_app.command("register")
@_handled
def register_deliverable(name: str, definition: Path, path: Path = _PATH):
    from waterology.core.reproduction import register_deliverable as register_service

    emit(register_service(path, name, DeliverableConfig.model_validate(load_document(definition))))


@deliverable_app.command("export")
@_handled
def export(name: str, destination: Path, path: Path = _PATH):
    from waterology.core.reproduction import export_deliverable

    emit(export_deliverable(path, name, destination))


def register_execution_commands(app: typer.Typer):
    app.add_typer(config_app, name="config")
    app.add_typer(workflow_app, name="workflow")
    app.add_typer(deliverable_app, name="deliverable")

    @app.command("reproduce")
    @_handled
    def reproduce(
        name: str,
        destination: Path,
        path: Path = _PATH,
        profile: str | None = None,
        bundle: bool = False,
        resume: bool = False,
        inputs: Path | None = None,
        confirm_remote: bool = False,
    ):
        from waterology.core.reproduction import reproduce_deliverable

        result = reproduce_deliverable(
            path,
            name,
            destination,
            profile=profile,
            bundle=bundle,
            resume=resume,
            inputs=inputs,
            progress=emit,
            confirm_remote=confirm_remote,
        )
        emit(result)
        if result["state"] != "passed":
            raise typer.Exit(1)
