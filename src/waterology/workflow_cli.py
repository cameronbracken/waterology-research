"""CLI adapters for durable study and evidence services."""

import json
import time
from contextvars import ContextVar
from pathlib import Path

import typer

from waterology.core.formats import readable
from waterology.core.studies import (
    advance_study,
    enqueue_candidate,
    list_studies,
    load_study,
    stop_study,
)

_PATH_OPTION = typer.Option(Path("."))
WORKFLOW_OUTPUT_FORMAT = ContextVar("workflow_output_format", default="nestedtext")

study_app = typer.Typer(help="Bounded autonomous research and engineering through TORC.")


def emit(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    output_format = WORKFLOW_OUTPUT_FORMAT.get()
    typer.echo(
        json.dumps(value, indent=2, allow_nan=False)
        if output_format == "json"
        else readable(value),
        nl=output_format == "json",
    )


@study_app.command("create")
def create(
    contract: Path,
    authorized_by: str = typer.Option(..., "--authorized-by"),
    profile: str | None = typer.Option(None),
    path: Path = _PATH_OPTION,
):
    """Record already-given authorization and pin the TORC execution contract."""
    from waterology.core.workflows import create_registered_study
    emit(create_registered_study(path, contract, profile=profile, authorized_by=authorized_by))



@study_app.command("list")
def list_command(path: Path = _PATH_OPTION):
    emit([r.model_dump(mode="json") for r in list_studies(path)])


@study_app.command("show")
def show(identifier: str, path: Path = _PATH_OPTION):
    emit(load_study(path, identifier))


@study_app.command("enqueue")
def enqueue(identifier: str, experiment: str, path: Path = _PATH_OPTION):
    emit(enqueue_candidate(path, identifier, experiment))


@study_app.command("advance")
def advance(identifier: str, path: Path = _PATH_OPTION):
    emit(advance_study(path, identifier))


@study_app.command("retry-submission")
def retry_submission(identifier: str, run_id: str, path: Path = _PATH_OPTION):
    """Recover a definitive create authorization rejection using live TORC inventory."""
    from waterology.core.studies import retry_submission as recover

    emit(recover(path, identifier, run_id))


@study_app.command("stop")
def stop(identifier: str, path: Path = _PATH_OPTION):
    emit(stop_study(path, identifier))


@study_app.command("watch")
def watch(
    identifier: str, path: Path = _PATH_OPTION, interval: float = typer.Option(10, min=1, max=60)
):
    """Drive queued evaluations until stopped, blocked, exhausted or complete."""
    previous = None
    try:
        while True:
            record = advance_study(path, identifier)
            status = (record.state, len(record.attempts), len(record.queue), record.reason)
            if status != previous:
                emit(
                    {
                        "study_id": record.id,
                        "state": record.state,
                        "attempts": len(record.attempts),
                        "queued": len(record.queue),
                        "reason": record.reason,
                    }
                )
                previous = status
            if record.state in {"complete", "stopped", "exhausted", "blocked"}:
                return
            time.sleep(interval)
    except KeyboardInterrupt:
        emit(stop_study(path, identifier))


@study_app.command("conclude")
def conclude(
    identifier: str,
    evidence: list[str],
    conclusion: str = typer.Option(...),
    author: str = typer.Option(...),
    path: Path = _PATH_OPTION,
):
    from waterology.core.studies import conclude_study

    emit(conclude_study(path, identifier, conclusion=conclusion, evidence=evidence, author=author))


@study_app.command("driver")
def driver(
    identifier: str,
    runtime: str = typer.Option(...),
    max_proposals: int = typer.Option(..., min=1),
    path: Path = _PATH_OPTION,
):
    """Authorize bounded candidate generation using an existing agent runtime."""
    from waterology.core.study_driver import configure_driver

    emit(configure_driver(path, identifier, runtime=runtime, max_proposals=max_proposals))


@study_app.command("run")
def run_driver(
    identifier: str, path: Path = _PATH_OPTION, interval: float = typer.Option(10, min=1, max=60)
):
    """Resume the configured candidate driver and TORC controller without new authorization."""
    from waterology.core.study_driver import drive_study

    previous = None
    try:
        while True:
            result = drive_study(path, identifier)
            status = (
                result["study"]["state"],
                len(result["study"]["attempts"]),
                result["driver"]["reason"],
            )
            if status != previous:
                emit(result)
                previous = status
            if not result["driver"].get("draining") and (
                status[0] in {"complete", "stopped", "exhausted", "blocked"} or status[2]
            ):
                return
            time.sleep(interval)
    except KeyboardInterrupt:
        stop_study(path, identifier)
        emit(drive_study(path, identifier))


def register_workflow_commands(app: typer.Typer):
    app.add_typer(study_app, name="study")
    from waterology.engineering_cli import register_engineering_commands

    register_engineering_commands(app)

    @app.command("compare-runs")
    def compare(run_ids: list[str], baseline: str = typer.Option(...), path: Path = _PATH_OPTION):
        from waterology.core.comparison import compare_runs

        emit(compare_runs(path, run_ids, baseline=baseline))

    @app.command("claim")
    def claim(
        text: str,
        run_id: str,
        selector: str = typer.Option(""),
        member: str = typer.Option("metrics.json"),
        kind: str = typer.Option("observation"),
        relation: str = typer.Option("supports"),
        related_claim: str | None = typer.Option(None),
        path: Path = _PATH_OPTION,
    ):
        from waterology.core.claims import register_claim

        emit(
            register_claim(
                path,
                claim=text,
                run_id=run_id,
                selector=selector,
                member=member,
                kind=kind,
                relation=relation,
                related_claim=related_claim,
            )
        )

    @app.command("claim-assess")
    def claim_assess(claim_id: str, status: str, author: str, note: str, path: Path = _PATH_OPTION):
        from waterology.core.claims import assess_claim

        emit(assess_claim(path, claim_id, status=status, author=author, note=note))

    @app.command("claims")
    def claims(path: Path = _PATH_OPTION):
        from waterology.core.claims import list_claims, verify_claim

        emit([verify_claim(path, c) for c in list_claims(path)])

    @app.command("discover")
    def discover(
        query: str,
        after: str | None = typer.Option(None),
        before: str | None = typer.Option(None),
        limit: int = typer.Option(20, min=1, max=100),
        path: Path = _PATH_OPTION,
    ):
        from waterology.core.literature import search_literature

        emit(search_literature(path, query, after=after, before=before, limit=limit))

    @app.command("source-decision")
    def decision(
        search_id: str, source_id: str, decision: str, note: str, path: Path = _PATH_OPTION
    ):
        from waterology.core.literature import record_source_decision

        emit(record_source_decision(path, search_id, source_id, decision=decision, note=note))

    @app.command("source-add")
    def source_add(title: str, locator: str, note: str = "", path: Path = _PATH_OPTION):
        from waterology.core.literature import register_local_source

        emit(register_local_source(path, title=title, locator=locator, note=note))

    @app.command("report")
    def report(
        run_ids: list[str],
        baseline: str = typer.Option(...),
        destination: str = typer.Option(...),
        path: Path = _PATH_OPTION,
    ):
        from waterology.core.reports import export_report

        emit(export_report(path, run_ids, baseline=baseline, destination=destination))
