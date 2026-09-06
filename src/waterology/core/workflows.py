"""Named execution through the existing experiment, TORC and archive services."""

import time
from pathlib import Path

from waterology.core.experiments import create_experiment
from waterology.core.git import is_clean
from waterology.core.profiles import machine_config_path
from waterology.core.project import discover_project
from waterology.core.registry import resolve_workflow
from waterology.torc.runs import inspect_torc_run, start_torc_run


def run_workflow(
    start: Path,
    name: str,
    *,
    profile: str | None = None,
    revision: str = "HEAD",
    confirm_remote: bool = False,
    gateway=None,
):
    project = discover_project(start)
    if not is_clean(project.root):
        raise ValueError("Commit the project and workflow registration before execution")
    config = resolve_workflow(project.root, name)
    selected = profile or config.default_compute_profile
    if selected == "direct":
        raise ValueError(
            "Named workflows require a TORC profile; select --profile or configure a default"
        )
    experiment = create_experiment(
        project.root,
        hypothesis=f"Execute registered workflow {name}",
        parent_ref=revision,
        workflow=name,
    )
    from waterology.core.experiments import load_worktree
    from waterology.core.registry import materialize_inputs

    worktree = Path(load_worktree(project.root, experiment.id).path)
    materialize_inputs(project.root, worktree, config.workflows[name].input_files)
    return start_torc_run(
        project.root,
        experiment.id,
        profile_name=selected,
        machine_config_file=machine_config_path(),
        confirm_remote=confirm_remote,
        gateway=gateway,
    )


def watch_workflow(start: Path, run_id: str, *, interval: float = 2, gateway=None, progress=None):
    while True:
        record = inspect_torc_run(
            start, run_id, machine_config_file=machine_config_path(), gateway=gateway
        )
        payload = record.model_dump(mode="json")
        if progress:
            progress(payload)
        if payload.get("terminal_state") or payload.get("operational_state") in {
            "unknown",
            "failed",
            "lost",
        }:
            return record
        time.sleep(interval)


def create_registered_study(
    start: Path, contract_path: Path, *, authorized_by: str, profile: str | None = None
):
    """Register a saved contract and create its baseline through shared services."""
    from waterology.core.formats import load_document
    from waterology.core.registry import project_file, register_entry
    from waterology.core.studies import StudyContract, create_study

    if not authorized_by.strip():
        raise ValueError("Record the existing authorization before creating a study")
    project = discover_project(start)
    relative = contract_path.resolve().relative_to(project.root).as_posix()
    project_file(project.root, relative)
    data = load_document(contract_path)
    create_baseline = not data.get("baseline_experiment") and data.get("workflow")
    # Validate the whole contract before creating a Git worktree.
    validated = StudyContract.model_validate(
        {**data, **({"baseline_experiment": "exp-pending"} if create_baseline else {})}
    )
    register_entry(start, "study_contracts", contract_path.stem, relative)
    if create_baseline:
        baseline = create_experiment(
            start, hypothesis=validated.objective, workflow=validated.workflow
        )
        validated = validated.model_copy(update={"baseline_experiment": baseline.id})
    return create_study(start, validated, profile=profile, authorized_by=authorized_by)
