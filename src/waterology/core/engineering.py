"""Specification-first entry points over the shared managed study records."""

from pathlib import Path

import nestedtext

from waterology.core.formats import load_document
from waterology.core.studies import StudyError, evaluate_metrics, load_study


def scaffold_contract(
    destination: Path,
    *,
    objective: str,
    workflow: str,
    allowed_paths: list[str],
    max_iterations: int,
    max_seconds: int,
    target_seconds: float | None = None,
) -> dict:
    from waterology.core.studies import StudyContract

    if destination.suffix != ".nt":
        raise ValueError("Engineering draft contracts must use the .nt extension")
    acceptance = [
        {"name": "failed_checks", "unit": "count", "direction": "minimize", "threshold": 0}
    ]
    if target_seconds is not None:
        if target_seconds <= 0:
            raise ValueError("Target seconds must be positive")
        acceptance.append(
            {"name": "elapsed", "unit": "s", "direction": "minimize", "threshold": target_seconds}
        )
    data = {
        "mode": "engineering",
        "objective": objective,
        "workflow": workflow,
        "candidate_strategy": "best" if target_seconds is not None else "latest_completed",
        "allowed_paths": allowed_paths,
        "evaluation": {
            "specification": "Describe required behavior and protected acceptance tests before creating the study",
            "failed_checks": "Qualification workflow must emit a finite count; zero means every required check passed",
        },
        "acceptance": acceptance,
        "max_iterations": max_iterations,
        "max_seconds": max_seconds,
        "max_retries": 0,
        "max_parallel": 1,
        "stop_behavior": "cancel",
        "uncertainty": "Declare timing repetitions for optimization; deterministic checks otherwise",
    }
    if target_seconds is not None:
        data["promotion_metric"] = "elapsed"
    # Validate without reserving a baseline, registering a workflow, or granting authority.
    StudyContract.model_validate({**data, "baseline_experiment": "exp-placeholder"})
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(nestedtext.dumps(data, default=str) + "\n")
    return {"contract": str(destination), "mode": "engineering", "status": "draft"}


def create_engineering_study(start, contract_path, *, authorized_by, profile=None):
    from waterology.core.registry import project_file
    from waterology.core.workflows import create_registered_study

    root = Path(start).resolve()
    contract_path = Path(contract_path).resolve()
    relative = contract_path.relative_to(root).as_posix()
    project_file(root, relative)
    data = load_document(contract_path)
    if data.get("mode") != "engineering":
        raise StudyError(
            "Engineering entry requires mode: engineering; use study create for research"
        )
    return create_registered_study(
        start, Path(contract_path), authorized_by=authorized_by, profile=profile
    )


def require_engineering(start, identifier):
    record = load_study(start, identifier)
    if record.contract.mode != "engineering":
        raise StudyError("This operation requires an engineering study")
    return record


def engineering_status(start, identifier):
    from waterology.core.archive import verify_project_archive

    record = require_engineering(start, identifier)
    attempts = []
    for attempt in record.attempts:
        assessment = attempt.assessment
        integrity = None
        if assessment:
            from waterology.core.errors import WaterologyError

            try:
                integrity = verify_project_archive(start, attempt.run_id).valid
            except (WaterologyError, OSError, ValueError):
                integrity = False
        assessment_current = True
        if assessment and integrity:
            from waterology.services import run_metrics

            measured = evaluate_metrics(record.contract, run_metrics(start, attempt.run_id))
            assessment_current = measured["accepted"] == assessment["accepted"] and [
                (c["name"], c["value"], c["passed"]) for c in measured["checks"]
            ] == [(c["name"], c["value"], c["passed"]) for c in assessment["checks"]]
        attempts.append(
            {
                "run_id": attempt.run_id,
                "experiment_id": attempt.experiment_id,
                "execution": attempt.state,
                "archive_valid": integrity,
                "assessment_current": assessment_current if assessment else None,
                "acceptance": "passed"
                if assessment and integrity and assessment_current and assessment["accepted"]
                else "failed"
                if assessment and integrity and assessment_current
                else "unverified",
                "checks": assessment["checks"] if assessment else [],
            }
        )
    return {
        "id": record.id,
        "objective": record.contract.objective,
        "state": record.state,
        "reason": record.reason,
        "profile": record.profile,
        "candidate_strategy": record.contract.candidate_strategy,
        "requirements": [rule.model_dump() for rule in record.contract.acceptance],
        "attempts": attempts,
        "accepted_runs": [a["run_id"] for a in attempts if a["acceptance"] == "passed"],
        "remaining_attempts": max(0, record.contract.max_iterations - len(record.attempts)),
        "max_seconds": record.contract.max_seconds,
        "authorized_at": record.authorized_at,
    }
