import json
import os
from pathlib import Path

from waterology.agents.supervisor import launch_session, reconcile_session
from waterology.core.archive import (
    ArchiveNotFoundError,
    export_project_archive,
    list_archives,
    load_archive,
    read_archive_logs,
)
from waterology.core.assessments import assess_run, list_assessments
from waterology.core.database import open_database
from waterology.core.errors import WaterologyError
from waterology.core.evidence import (
    list_artifact_references,
    list_evidence,
    register_artifact_reference,
    register_evidence,
)
from waterology.core.execution import start_direct_run
from waterology.core.experiments import (
    add_experiment_note,
    create_experiment,
    list_experiment_notes,
    list_experiments,
    load_experiment,
)
from waterology.core.profiles import load_machine_config, machine_config_path
from waterology.core.project import Project, discover_project, inspect_project
from waterology.core.sessions import (
    add_session_note,
    create_session,
    list_sessions,
    load_session,
    read_session_logs,
)
from waterology.torc.runs import cancel_torc_run, inspect_torc_run, start_torc_run


def project_status(path: Path) -> dict[str, object]:
    status = inspect_project(path)
    return {
        "assessments": status.assessments,
        "database_exists": status.database_exists,
        "experiments": status.experiments,
        "name": status.project.config.name,
        "root": str(status.project.root),
        "runs": status.runs,
    }


def create_experiment_record(
    path: Path,
    *,
    hypothesis: str,
    parent_ref: str = "HEAD",
    parent_experiment_id: str | None = None,
    owner: str | None = None,
    experiment_id: str | None = None,
) -> dict[str, object]:
    return create_experiment(
        path,
        hypothesis=hypothesis,
        parent_ref=parent_ref,
        parent_experiment_id=parent_experiment_id,
        owner=owner,
        experiment_id=experiment_id,
    ).model_dump(mode="json")


def experiment_status(path: Path, experiment_id: str) -> dict[str, object]:
    return load_experiment(path, experiment_id).model_dump(mode="json")


def experiment_tree(path: Path) -> list[dict[str, object]]:
    return [record.model_dump(mode="json") for record in list_experiments(path)]


def record_experiment_note(
    path: Path, experiment_id: str, text: str, author: str | None = None
) -> dict[str, object]:
    return add_experiment_note(path, experiment_id, text, author=author).model_dump(mode="json")


def start_run(
    path: Path,
    experiment_id: str,
    *,
    profile: str = "direct",
    confirm_remote: bool = False,
) -> dict[str, object]:
    if profile == "direct":
        run = start_direct_run(path, experiment_id)
    else:
        run = start_torc_run(
            path,
            experiment_id,
            profile_name=profile,
            machine_config_file=machine_config_path(),
            confirm_remote=confirm_remote,
        )
    return run.model_dump(mode="json")


def run_status(path: Path, run_id: str) -> dict[str, object]:
    try:
        run = load_archive(path, run_id)
    except ArchiveNotFoundError:
        run = inspect_torc_run(path, run_id, machine_config_file=machine_config_path())
    return run.model_dump(mode="json")


def cancel_run(path: Path, run_id: str) -> dict[str, object]:
    return cancel_torc_run(path, run_id, machine_config_file=machine_config_path()).model_dump(
        mode="json"
    )


def assess_run_record(
    path: Path,
    run_id: str,
    *,
    kind: str,
    conclusion: str,
    author: str,
    evidence: tuple[str, ...] = (),
    note: str | None = None,
) -> dict[str, object]:
    return assess_run(
        path,
        run_id,
        kind=kind,
        conclusion=conclusion,
        author=author,
        evidence=evidence,
        note=note,
    ).model_dump(mode="json")


def run_logs(path: Path, run_id: str) -> dict[str, str]:
    return read_archive_logs(path, run_id)


def run_metrics(path: Path, run_id: str) -> dict[str, object]:
    project = discover_project(path)
    load_archive(project.root, run_id)
    value = json.loads((project.paths.runs / run_id / "metrics.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Run metrics are not a JSON object: {run_id}")
    return value


def archives(path: Path) -> list[dict[str, object]]:
    return [record.model_dump(mode="json") for record in list_archives(path)]


def export_archive(path: Path, run_id: str, destination: str) -> dict[str, object]:
    exported = export_project_archive(path, run_id, destination)
    project = discover_project(path)
    return {"destination": exported.relative_to(project.root).as_posix(), "run_id": run_id}


def sessions(path: Path) -> list[dict[str, object]]:
    return [
        reconcile_session(path, record.id).model_dump(mode="json")
        for record in list_sessions(path)
    ]


def session_status(path: Path, session_id: str) -> dict[str, object]:
    load_session(path, session_id)
    return reconcile_session(path, session_id).model_dump(mode="json")


def session_logs(path: Path, session_id: str) -> list[dict[str, object]]:
    return list(read_session_logs(path, session_id))


def record_session_note(
    path: Path, session_id: str, text: str, author: str | None = None
) -> dict[str, object]:
    return add_session_note(path, session_id, text, author=author).model_dump(mode="json")


def register_evidence_record(path: Path, **values: object) -> dict[str, object]:
    return register_evidence(path, **values).model_dump(mode="json")  # type: ignore[arg-type]


def register_artifact_record(path: Path, **values: object) -> dict[str, object]:
    return register_artifact_reference(path, **values).model_dump(mode="json")  # type: ignore[arg-type]


def evidence_records(path: Path, experiment_id: str | None = None) -> list[dict[str, object]]:
    return [
        record.model_dump(mode="json")
        for record in list_evidence(path, experiment_id=experiment_id)
    ]


def artifact_records(path: Path, experiment_id: str | None = None) -> list[dict[str, object]]:
    return [
        record.model_dump(mode="json")
        for record in list_artifact_references(path, experiment_id=experiment_id)
    ]


def start_agent_session(
    path: Path,
    experiment_id: str,
    *,
    task: str,
    runtime: str = "codex",
    role: str = "researcher",
    profile: str = "local",
) -> dict[str, object]:
    session = create_session(
        path,
        experiment_id=experiment_id,
        runtime=runtime,
        role=role,
        task=task,
        compute_profile=profile,
    )
    return launch_session(path, session.id, prompt=task).model_dump(mode="json")


def resume_agent_session(path: Path, session_id: str, *, prompt: str) -> dict[str, object]:
    return launch_session(path, session_id, prompt=prompt).model_dump(mode="json")


def dashboard_snapshot(path: Path) -> dict[str, object]:
    project = discover_project(path)
    experiment_values = list_experiments(project.root)
    session_values = [
        reconcile_session(project.root, record.id) for record in list_sessions(project.root)
    ]
    evidence_values = list_evidence(project.root)
    artifact_values = list_artifact_references(project.root)
    experiment_notes = {
        experiment.id: [
            note.model_dump(mode="json")
            for note in list_experiment_notes(project.root, experiment.id)
        ]
        for experiment in experiment_values
    }
    machine = load_machine_config(machine_config_path())
    profiles = [
        {
            "name": name,
            **machine.profile(name).model_dump(mode="json"),
            "tui_command": f"torc --url {machine.profile(name).api_url} tui",
        }
        for name in sorted(machine.profiles)
    ]
    with open_database(project.paths.database) as database:
        rows = database.connection.execute(
            """
            SELECT id, experiment_id, operational_state, executor, compute_profile, process_id,
                   workflow_id, job_ids_json, api_url, execution_mode, started_at,
                   last_observed_at
            FROM runs
            ORDER BY started_at DESC, id DESC
            """
        ).fetchall()
    managed_runs = [
        {
            "run_id": row["id"],
            "experiment_id": row["experiment_id"],
            "operational_state": row["operational_state"],
            "executor": row["executor"],
            "compute_profile": row["compute_profile"],
            "process_id": row["process_id"],
            "workflow_id": row["workflow_id"],
            "job_ids": json.loads(row["job_ids_json"] or "[]"),
            "api_url": row["api_url"],
            "execution_mode": row["execution_mode"],
            "started_at": row["started_at"],
            "last_observed_at": row["last_observed_at"],
        }
        for row in rows
    ]
    active_states = {"queued", "preparing", "running", "collecting", "unknown"}
    for record in managed_runs:
        if record["operational_state"] not in active_states:
            continue
        if record["executor"] == "direct":
            _reconcile_direct_dashboard_state(project, record)
            continue
        try:
            observed = run_status(project.root, str(record["run_id"]))
        except (OSError, TypeError, ValueError, WaterologyError) as error:
            record["inspection_error"] = str(error)
        else:
            record["operational_state"] = observed.get(
                "terminal_state", observed.get("operational_state")
            )
            record["last_observed_at"] = observed.get(
                "finished_at", observed.get("last_observed_at")
            )
    archive_values = list_archives(project.root)
    archive_metrics = {
        archive.run_id: run_metrics(project.root, archive.run_id) for archive in archive_values
    }
    assessments = [
        record
        for archive in archive_values
        for record in list_assessments(project.root, archive.run_id)
    ]
    return {
        "project": project_status(project.root),
        "counts": {
            "experiments": len(experiment_values),
            "active_agents": sum(
                record.state in {"running", "waiting"} for record in session_values
            ),
            "evidence": len(evidence_values),
            "archives": len(archive_values),
            "active_runs": sum(
                record["operational_state"] in active_states
                for record in managed_runs
            ),
        },
        "experiments": [record.model_dump(mode="json") for record in experiment_values],
        "experiment_notes": experiment_notes,
        "sessions": [record.model_dump(mode="json") for record in session_values],
        "evidence": [record.model_dump(mode="json") for record in evidence_values],
        "artifacts": [record.model_dump(mode="json") for record in artifact_values],
        "archives": [record.model_dump(mode="json") for record in archive_values],
        "archive_metrics": archive_metrics,
        "assessments": [record.model_dump(mode="json") for record in assessments],
        "managed_runs": managed_runs,
        "profiles": profiles,
    }


def _reconcile_direct_dashboard_state(
    project: Project,
    record: dict[str, object],
) -> None:
    root = project.root
    paths = project.paths
    run_id = str(record["run_id"])
    if (paths.runs / run_id / "manifest.json").is_file():
        manifest = load_archive(root, run_id)
        record["operational_state"] = manifest.terminal_state
        record["last_observed_at"] = manifest.finished_at
        return
    metadata_path = paths.staging / run_id / "execution.json"
    if not metadata_path.is_file():
        record["operational_state"] = "unknown"
        record["inspection_error"] = "Direct run has no archive or execution record"
        return
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        record["operational_state"] = "unknown"
        record["inspection_error"] = f"Direct execution record is invalid: {error}"
        return
    state = metadata.get("state")
    process_id = metadata.get("process_id")
    if state == "running" and isinstance(process_id, int) and not _process_alive(process_id):
        record["operational_state"] = "unknown"
        record["inspection_error"] = "Direct process is no longer running; repair the index"
    elif state in {"completed", "failed", "cancelled"}:
        record["operational_state"] = "collecting"
        record["inspection_error"] = "Direct process finished without a sealed archive"
    elif isinstance(state, str):
        record["operational_state"] = state


def _process_alive(process_id: int) -> bool:
    if os.name == "nt":
        from waterology.agents.supervisor import _windows_process_alive

        return _windows_process_alive(process_id)
    try:
        os.kill(process_id, 0)
    except OSError:
        return False
    return True
