import json
from pathlib import Path

from waterology.agents.supervisor import reconcile_session
from waterology.core.archive import (
    ArchiveNotFoundError,
    list_archives,
    load_archive,
    read_archive_logs,
)
from waterology.core.assessments import assess_run
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
    list_experiments,
    load_experiment,
)
from waterology.core.profiles import machine_config_path
from waterology.core.project import discover_project, inspect_project
from waterology.core.sessions import (
    add_session_note,
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
