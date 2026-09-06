"""Bounded candidate generation using existing supervised runtime sessions."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from waterology.core.atomic import exclusive_file_lock, write_json
from waterology.core.errors import WaterologyError
from waterology.core.experiments import create_experiment, load_experiment
from waterology.core.project import project_state_lock
from waterology.core.studies import (
    StudyError,
    _directory,
    _path,
    _save,
    _stop_path,
    advance_study,
    enqueue_candidate,
    load_study,
)


def _driver_path(start: Path, study_id: str) -> Path:
    _path(start, study_id)
    return _directory(start) / f"{study_id}.driver"


def _save_driver(start: Path, study_id: str, state: dict) -> None:
    write_json(_driver_path(start, study_id), state)


def configure_driver(start: Path, study_id: str, *, runtime: str, max_proposals: int) -> dict:
    """Record a separately explicit bounded candidate-generation authorization."""
    if runtime not in {"codex", "claude", "opencode"} or max_proposals < 1:
        raise ValueError("Select a supported runtime and positive proposal cap")
    with project_state_lock(start):
        study = load_study(start, study_id)
        path = _driver_path(start, study_id)
        if path.exists():
            raise StudyError("Driver already configured; resume the existing driver")
        if study.stop_requested or study.state in {"complete", "stopped", "exhausted"}:
            raise StudyError("Study has stopped")
        state = {
            "schema_version": 1,
            "study_id": study_id,
            "runtime": runtime,
            "max_proposals": max_proposals,
            "proposals": [],
            "reason": None,
        }
        _save_driver(start, study_id, state)
        return state


def drive_study(start: Path, study_id: str) -> dict:
    with exclusive_file_lock(_driver_path(start, study_id).with_suffix(".driver.lock")):
        return _drive_study(start, study_id)


def _drive_study(start: Path, study_id: str) -> dict:
    """Advance TORC first, then at most one candidate-generation transition."""
    from waterology.agents.supervisor import launch_session, reconcile_session
    from waterology.core.sessions import create_session, load_session

    study = advance_study(start, study_id)
    path = _driver_path(start, study_id)
    if path.is_symlink():
        raise StudyError("Driver record must not be a symlink")
    driver = json.loads(path.read_text())
    if driver["study_id"] != study_id:
        raise StudyError("Driver identity mismatch")
    if study.state in {"complete", "stopped", "exhausted", "blocked", "stopping"}:
        from waterology.agents.supervisor import interrupt_session

        driver["draining"] = False
        for proposal in driver["proposals"]:
            if proposal["state"] in {"running", "launching", "blocked", "reserved"}:
                try:
                    session = reconcile_session(start, proposal["session_id"])
                except WaterologyError as error:
                    raise StudyError(
                        "Candidate session ownership is unresolved during stop"
                    ) from error
                if session.state in {"running", "waiting"}:
                    if study.contract.stop_behavior == "cancel":
                        interrupt_session(start, session.id)
                        proposal["state"] = "blocked"
                    else:
                        driver["reason"] = "Study stopped; authorized candidate session is draining"
                        driver["draining"] = True
                else:
                    proposal["state"] = "blocked"
        if driver["draining"]:
            with project_state_lock(start):
                study = _save(
                    start,
                    load_study(start, study_id).model_copy(
                        update={
                            "state": "stopping",
                            "reason": driver["reason"],
                        }
                    ),
                )
        _save_driver(start, study_id, driver)
        return {"study": study.model_dump(mode="json"), "driver": driver}
    active = next((p for p in driver["proposals"] if p["state"] != "evaluating"), None)
    if active:
        if active["state"] in {"reserved", "launching", "blocked"}:
            try:
                recovered = load_session(start, active["session_id"])
            except WaterologyError:
                driver["reason"] = (
                    "Candidate launch is unresolved; inspect its saved experiment/session ID"
                )
                _save_driver(start, study_id, driver)
                return {"study": study.model_dump(mode="json"), "driver": driver}
            if not recovered.attempts:
                driver["reason"] = (
                    "Candidate has no recorded runtime attempt; inspect before resuming"
                )
                _save_driver(start, study_id, driver)
                return {"study": study.model_dump(mode="json"), "driver": driver}
            active["state"] = "running"
            driver["reason"] = None
            _save_driver(start, study_id, driver)
        session = reconcile_session(start, active["session_id"])
        if session.state in {"created", "running", "waiting"}:
            return {"study": study.model_dump(mode="json"), "driver": driver}
        if session.state != "completed":
            active["state"] = "blocked"
            driver["reason"] = f"Candidate session ended {session.state}; evidence retained"
            _save_driver(start, study_id, driver)
            return {"study": study.model_dump(mode="json"), "driver": driver}
        if (
            not any(a.experiment_id == active["experiment_id"] for a in study.attempts)
            and active["experiment_id"] not in study.queue
        ):
            enqueue_candidate(start, study_id, active["experiment_id"])
        active["state"] = "evaluating"
        _save_driver(start, study_id, driver)
        return {"study": load_study(start, study_id).model_dump(mode="json"), "driver": driver}
    if study.queue or any(a.state in {"submitting", "running"} for a in study.attempts):
        return {"study": study.model_dump(mode="json"), "driver": driver}
    if len(driver["proposals"]) >= driver["max_proposals"]:
        driver["reason"] = "Proposal budget exhausted"
        _save_driver(start, study_id, driver)
        return {"study": study.model_dump(mode="json"), "driver": driver}
    with project_state_lock(start):
        # Reserve names before repository and process mutations outside the lock.
        current = json.loads(path.read_text())
        if current != driver:
            raise StudyError("Another driver advanced this study; reload")
        if _stop_path(start, study_id).exists():
            return {"study": study.model_dump(mode="json"), "driver": driver}
        if (
            datetime.now(UTC) - datetime.fromisoformat(study.authorized_at)
        ).total_seconds() >= study.contract.max_seconds:
            return {"study": study.model_dump(mode="json"), "driver": driver}
        proposal = {
            "experiment_id": f"exp-{uuid4().hex[:12]}",
            "session_id": f"session-{uuid4().hex[:16]}",
            "state": "reserved",
        }
        driver["proposals"].append(proposal)
        _save_driver(start, study_id, driver)
    try:
        parent = next((a for a in study.attempts if a.run_id == study.best_run), None)
        parent_experiment = parent.experiment_id if parent else study.contract.baseline_experiment
        parent_record = load_experiment(start, parent_experiment)
        parent_commit = parent.commit_sha if parent else study.baseline_commit
        experiment = create_experiment(
            start,
            workflow=study.contract.workflow,
            hypothesis=f"{study.contract.mode}: {study.contract.objective}",
            parent_ref=parent_commit,
            experiment_id=proposal["experiment_id"],
        )
        task = (
            f"Continue authorized {study.contract.mode} study {study.id}. Prepare one committed candidate only. "
            f"Objective: {study.contract.objective}. Allowed paths: {study.contract.allowed_paths}. "
            f"Parent experiment: {parent_record.id}, commit {parent_commit}. "
            f"Acceptance contract: {study.contract.model_dump_json()}. "
            f"Prior evidence: {json.dumps([a.model_dump(mode='json') for a in study.attempts])}. "
            "Do not launch evaluations or remote commands. The controller owns all TORC compute. "
            "Use only declared lightweight local checks. Preserve protected files and commit your candidate "
            "using the project signing policy. Do not ask for iteration approval within this scope. "
            "If runtime permissions or missing information prevent progress, record the blocker and stop. "
            "Do not modify the controller, study records, acceptance rules or archived evidence."
        )
        from waterology.core.formats import readable
        from waterology.core.learning import learning_warning, lesson_context

        try:
            lessons = lesson_context(start, study.contract.objective)
        except (OSError, ValueError, TypeError, KeyError) as error:
            learning_warning(start, error)
            lessons = []
        if lessons:
            task += "\nRelevant verified project lessons (subordinate to this study contract):\n" + readable(lessons)
        create_session(
            start,
            experiment_id=experiment.id,
            runtime=driver["runtime"],
            role="researcher",
            task=task,
            compute_profile=study.profile,
            session_id=proposal["session_id"],
        )
        proposal["state"] = "launching"
        _save_driver(start, study_id, driver)
        latest = load_study(start, study_id)
        if (
            _stop_path(start, study_id).exists()
            or latest.stop_requested
            or latest.state in {"complete", "stopped", "exhausted", "blocked", "stopping"}
            or (datetime.now(UTC) - datetime.fromisoformat(latest.authorized_at)).total_seconds()
            >= latest.contract.max_seconds
        ):
            raise StudyError("Study stopped before candidate launch")
        launch_session(start, load_session(start, proposal["session_id"]).id, prompt=task)
        proposal["state"] = "running"
        driver["reason"] = None
        _save_driver(start, study_id, driver)
    except (ValueError, OSError, RuntimeError, WaterologyError) as error:
        proposal["state"] = "blocked"
        driver["reason"] = (
            f"{type(error).__name__}: inspect the saved candidate/session; no automatic relaunch"
        )
        _save_driver(start, study_id, driver)
    return {"study": load_study(start, study_id).model_dump(mode="json"), "driver": driver}
