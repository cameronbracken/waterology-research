"""Engineering is an explicit view of the shared study lifecycle, not another engine."""

from functools import wraps
from pathlib import Path

import typer

from waterology.core.engineering import (
    create_engineering_study,
    engineering_status,
    require_engineering,
    scaffold_contract,
)
from waterology.core.errors import WaterologyError
from waterology.workflow_cli import emit

engineering_app = typer.Typer(help="Build to a specification or optimize under fixed constraints.")
_PATH = typer.Option(Path("."), "--path")
_ALLOW_PATH = typer.Option(..., "--allow-path")


def _handled(operation):
    @wraps(operation)
    def call(*args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except (ValueError, OSError, WaterologyError) as error:
            emit({"error": str(error)})
            raise typer.Exit(1) from error

    return call


@engineering_app.command("init")
@_handled
def initialize(
    destination: Path,
    objective: str = typer.Option(...),
    workflow: str = typer.Option(...),
    allow_path: list[str] = _ALLOW_PATH,
    max_iterations: int = typer.Option(..., min=1),
    max_seconds: int = typer.Option(..., min=1),
    target_seconds: float | None = typer.Option(None),
):
    """Write a draft acceptance contract without creating or running a study."""
    emit(
        scaffold_contract(
            destination,
            objective=objective,
            workflow=workflow,
            allowed_paths=allow_path,
            max_iterations=max_iterations,
            max_seconds=max_seconds,
            target_seconds=target_seconds,
        )
    )


@engineering_app.command("create")
@_handled
def create(
    contract: Path,
    authorized_by: str = typer.Option(..., "--authorized-by"),
    profile: str | None = None,
    path: Path = _PATH,
):
    """Record existing authority for an engineering contract and queue its baseline."""
    emit(create_engineering_study(path, contract, authorized_by=authorized_by, profile=profile))


@engineering_app.command("show")
@_handled
def show(identifier: str, path: Path = _PATH):
    """Show requirement results and verified acceptance evidence."""
    emit(engineering_status(path, identifier))


@engineering_app.command("list")
@_handled
def list_command(path: Path = _PATH):
    from waterology.core.studies import list_studies

    emit(
        [r.model_dump(mode="json") for r in list_studies(path) if r.contract.mode == "engineering"]
    )


def register_engineering_commands(app):
    from waterology import workflow_cli

    # Preserve signatures and behavior, adding only an engineering-mode guard.
    for name, operation in (
        ("enqueue", workflow_cli.enqueue),
        ("advance", workflow_cli.advance),
        ("watch", workflow_cli.watch),
        ("driver", workflow_cli.driver),
        ("run", workflow_cli.run_driver),
        ("stop", workflow_cli.stop),
        ("retry-submission", workflow_cli.retry_submission),
    ):

        def guarded(operation):
            @wraps(operation)
            def call(*args, **kwargs):
                require_engineering(kwargs["path"], kwargs["identifier"])
                return operation(*args, **kwargs)

            return _handled(call)

        engineering_app.command(name)(guarded(operation))
    app.add_typer(engineering_app, name="engineering")
