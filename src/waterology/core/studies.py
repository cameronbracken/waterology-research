"""Durable, bounded research and engineering evaluations through TORC."""

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

from waterology.core.atomic import write_json
from waterology.core.config import _portable_project_paths
from waterology.core.errors import WaterologyError
from waterology.core.execution import prepare_run_inputs
from waterology.core.experiments import load_experiment
from waterology.core.git import git_output
from waterology.core.profiles import load_machine_config, machine_config_path
from waterology.core.project import discover_project, project_state_lock
from waterology.torc.runs import start_torc_run


class StudyError(WaterologyError):
    code = "study_error"


class MetricRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    direction: Literal["minimize", "maximize"] = "minimize"
    threshold: float


class StudyContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    mode: Literal["research", "engineering"]
    objective: str = Field(min_length=1)
    workflow: str | None = None
    baseline_experiment: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    allowed_paths: tuple[str, ...] = Field(min_length=1)
    evaluation: dict[str, object] = Field(min_length=1)
    acceptance: tuple[MetricRule, ...] = Field(min_length=1)
    promotion_metric: str | None = None
    promotion_margin: float = Field(default=0, ge=0, allow_inf_nan=False)
    max_iterations: int = Field(ge=1)
    max_seconds: int = Field(ge=1)
    max_retries: int = Field(default=0, ge=0)
    max_parallel: int = Field(default=1, ge=1)
    stop_behavior: Literal["drain", "cancel"] = "drain"
    local_checks: tuple[str, ...] = ()
    input_files: dict[str, str] = Field(default_factory=dict)
    uncertainty: str = "not estimated"

    _paths = field_validator("allowed_paths")(_portable_project_paths)

    @model_serializer(mode="wrap")
    def serialize_compatible(self, handler):
        payload = handler(self)
        if self.workflow is None:
            payload.pop("workflow", None)
        return payload

    @model_validator(mode="after")
    def validate_rules(self):
        names = [rule.name for rule in self.acceptance]
        if len(names) != len(set(names)):
            raise ValueError("Acceptance metric names must be unique")
        if self.promotion_metric is not None and self.promotion_metric not in names:
            raise ValueError("Promotion metric must have an acceptance rule")
        return self


class EvaluationAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: str
    experiment_id: str
    commit_sha: str
    state: Literal["submitting", "running", "completed", "failed", "cancelled", "lost"]
    retry: int = 0
    result: dict[str, object] | None = None
    assessment: dict[str, object] | None = None


class StudyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^study-[0-9a-f]{16}$")
    contract: StudyContract
    contract_hash: str
    profile: str
    execution_hash: str
    evaluation_hash: str
    baseline_commit: str
    authorized_by: str = Field(min_length=1)
    authorized_at: str
    state: Literal[
        "ready", "running", "blocked", "stopping", "stopped", "complete", "exhausted"
    ] = "ready"
    queue: tuple[str, ...] = ()
    attempts: tuple[EvaluationAttempt, ...] = ()
    best_run: str | None = None
    stop_requested: bool = False
    reason: str | None = None
    conclusion: dict[str, object] | None = None


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    ).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _directory(start: Path) -> Path:
    project = discover_project(start)
    path = project.paths.state / "studies"
    if path.is_symlink():
        raise StudyError("Study directory must not be a symlink")
    path.mkdir(exist_ok=True)
    return path


def _path(start: Path, identifier: str) -> Path:
    if not re.fullmatch(r"study-[0-9a-f]{16}", identifier):
        raise StudyError("Invalid study identifier")
    path = _directory(start) / f"{identifier}.json"
    if path.is_symlink():
        raise StudyError("Study record must not be a symlink")
    return path


def _save(start: Path, record: StudyRecord) -> StudyRecord:
    # Revalidate updates because pydantic model_copy does not validate them.
    record = StudyRecord.model_validate(record.model_dump())
    write_json(_path(start, record.id), record.model_dump(mode="json"))
    return record


def load_study(start: Path, identifier: str) -> StudyRecord:
    record = StudyRecord.model_validate_json(_path(start, identifier).read_text())
    if (
        record.id != identifier
        or fingerprint(record.contract.model_dump(mode="json")) != record.contract_hash
    ):
        raise StudyError("Study identity or contract changed")
    return record


def list_studies(start: Path) -> list[StudyRecord]:
    return [load_study(start, p.stem) for p in sorted(_directory(start).glob("study-*.json"))]


def execution_identity(start: Path, experiment_id: str, profile_name: str) -> tuple[str, str]:
    inputs = prepare_run_inputs(start, experiment_id)
    profile = load_machine_config(machine_config_path()).profile(profile_name)
    if profile.mode != "local" and not profile.trusted:
        raise StudyError("Trust the selected remote profile before authorizing the study")
    config = inputs.config
    hashes = {}
    for relative in config.environment_files:
        path = inputs.worktree / relative
        if not path.is_file() or not path.resolve().is_relative_to(inputs.worktree.resolve()):
            raise StudyError(f"Missing or escaping environment file: {relative}")
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    # No environment values or credentials are persisted in the study.
    import os

    env_hash = fingerprint(
        {name: os.environ.get(name) for name in config.archive.environment_allowlist}
    )
    identity = {
        "config": config.model_dump(mode="json"),
        "profile": profile.model_dump(mode="json", exclude={"trusted"}),
        "environment_files": hashes,
        "environment_hash": env_hash,
    }
    return fingerprint(identity), inputs.commit_sha


def create_study(
    start: Path, contract: StudyContract, *, profile: str | None = None, authorized_by: str
) -> StudyRecord:
    from waterology.services import resolve_run_profile

    with project_state_lock(start):
        selected = resolve_run_profile(start, contract.baseline_experiment, profile)
        if selected == "direct":
            raise StudyError("Managed studies require a TORC profile, including local studies")
        if not authorized_by.strip():
            raise StudyError("Record the existing authorization before creating a study")
        if contract.workflow and load_experiment(start, contract.baseline_experiment).workflow != contract.workflow:
            raise StudyError("Baseline must use the study workflow")
        identity, commit = execution_identity(start, contract.baseline_experiment, selected)
        config = prepare_run_inputs(start, contract.baseline_experiment).config
        if contract.max_parallel > config.concurrency.max_runs:
            raise StudyError("Study concurrency exceeds project concurrency")
        return _save(
            start,
            StudyRecord(
                id=f"study-{uuid4().hex[:16]}",
                contract=contract,
                contract_hash=fingerprint(contract.model_dump(mode="json")),
                profile=selected,
                execution_hash=identity,
                evaluation_hash=fingerprint(
                    {
                        "execution": identity,
                        "inputs": contract.input_files,
                        "protected_source": [
                            line
                            for line in git_output(
                                discover_project(start).root, "ls-tree", "-r", commit
                            ).splitlines()
                            if not any(
                                line.split("\t", 1)[-1] == allowed
                                or line.split("\t", 1)[-1].startswith(allowed.rstrip("/") + "/")
                                for allowed in contract.allowed_paths
                            )
                        ],
                    }
                ),
                baseline_commit=commit,
                authorized_by=authorized_by.strip(),
                authorized_at=_now(),
                queue=(contract.baseline_experiment,),
            ),
        )


def _validate_candidate(start: Path, record: StudyRecord, experiment_id: str) -> str:
    identity, commit = execution_identity(start, experiment_id, record.profile)
    if identity != record.execution_hash:
        raise StudyError("Execution configuration changed; restore it or authorize a new study")
    root = discover_project(start).root
    inputs = prepare_run_inputs(start, experiment_id)
    for relative, expected in record.contract.input_files.items():
        from waterology.core.config import _portable_project_path

        path = inputs.worktree / _portable_project_path(relative)
        if (
            not path.is_file()
            or not path.resolve().is_relative_to(inputs.worktree.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise StudyError(f"Input identity mismatch: {relative}")
    changed = git_output(
        root, "diff", "--name-only", "--no-renames", record.baseline_commit, commit
    ).splitlines()
    for name in changed:
        if not any(
            name == allowed or name.startswith(allowed.rstrip("/") + "/")
            for allowed in record.contract.allowed_paths
        ):
            raise StudyError(f"Candidate changed a protected path: {name}")
    return commit


def enqueue_candidate(start: Path, identifier: str, experiment_id: str) -> StudyRecord:
    with project_state_lock(start):
        record = load_study(start, identifier)
        if record.stop_requested or record.state in {"complete", "exhausted", "stopped"}:
            raise StudyError("Study no longer accepts candidates")
        if experiment_id in record.queue or any(
            a.experiment_id == experiment_id for a in record.attempts
        ):
            raise StudyError("Candidate is already queued or evaluated; create a new experiment")
        _validate_candidate(start, record, experiment_id)
        return _save(start, record.model_copy(update={"queue": (*record.queue, experiment_id)}))


def evaluate_metrics(contract: StudyContract, metrics: dict[str, object]) -> dict[str, object]:
    checks = []
    for rule in contract.acceptance:
        value = metrics.get(rule.name)
        numeric = type(value) in (int, float) and math.isfinite(value)
        passed = numeric and (
            value <= rule.threshold if rule.direction == "minimize" else value >= rule.threshold
        )
        checks.append(
            {
                "name": rule.name,
                "unit": rule.unit,
                "value": value if numeric else None,
                "passed": bool(passed),
                "reason": None if numeric else "missing or nonfinite measurement",
            }
        )
    feasible = all(check["passed"] for check in checks)
    return {
        "feasible": feasible,
        "accepted": feasible and contract.mode == "engineering",
        "checks": checks,
        "scientific_answer": "unassessed",
    }


def _best(record: StudyRecord, attempt: EvaluationAttempt) -> str | None:
    if not attempt.assessment or not attempt.assessment["feasible"]:
        return record.best_run
    metric = record.contract.promotion_metric
    if record.best_run is None:
        return attempt.run_id
    if metric is None:
        return record.best_run
    previous = next(a for a in record.attempts if a.run_id == record.best_run)
    values = {c["name"]: c["value"] for c in attempt.assessment["checks"]}
    old = {c["name"]: c["value"] for c in previous.assessment["checks"]}
    rule = next(r for r in record.contract.acceptance if r.name == metric)
    delta = (
        old[metric] - values[metric]
        if rule.direction == "minimize"
        else values[metric] - old[metric]
    )
    return attempt.run_id if delta > record.contract.promotion_margin else record.best_run


def advance_study(start: Path, identifier: str) -> StudyRecord:
    from waterology.core.learning import capture_study_outcomes, learning_warning

    record = _advance_study(start, identifier)
    try:
        capture_study_outcomes(start, record)
    except (OSError, ValueError, TypeError, KeyError) as error:
        learning_warning(start, error)
    return record


def _advance_study(start: Path, identifier: str) -> StudyRecord:
    """One durable controller tick. Safe to repeat after process restart."""
    from waterology import services
    from waterology.core.archive import verify_project_archive

    with project_state_lock(start):
        record = load_study(start, identifier)
        if record.state in {"complete", "stopped", "exhausted"}:
            return record
        try:
            attempts = list(record.attempts)
            active = [a for a in attempts if a.state in {"submitting", "running"}]
            deadline = (
                datetime.now(UTC) - datetime.fromisoformat(record.authorized_at)
            ).total_seconds() >= record.contract.max_seconds
            stopping = record.stop_requested or deadline or _stop_path(start, identifier).exists()
            if stopping and record.contract.stop_behavior == "cancel":
                cancellation_errors = []
                for attempt in active:
                    try:
                        services.cancel_run(start, attempt.run_id)
                    except (WaterologyError, ValueError, OSError, RuntimeError) as error:
                        cancellation_errors.append(type(error).__name__)
                if cancellation_errors:
                    raise StudyError(
                        "Some active cancellations remain unresolved: "
                        + ", ".join(cancellation_errors)
                    )
            for attempt in active:
                # Validate again before collection uses a worktree or machine settings.
                if _validate_candidate(start, record, attempt.experiment_id) != attempt.commit_sha:
                    raise StudyError(
                        "Active candidate commit changed; restore before reconciliation"
                    )
                result = services.run_status(start, attempt.run_id)
                if not result.get("terminal_state"):
                    if not result.get("reference"):
                        raise StudyError(
                            f"Unresolved submission {attempt.run_id}; reconcile TORC identity before any retry"
                        )
                    continue
                if not verify_project_archive(start, attempt.run_id).valid:
                    raise StudyError(f"Archive integrity failed: {attempt.run_id}")
                assessment = (
                    evaluate_metrics(record.contract, services.run_metrics(start, attempt.run_id))
                    if result["terminal_state"] == "completed"
                    else None
                )
                updated = attempt.model_copy(
                    update={
                        "state": result["terminal_state"],
                        "result": result,
                        "assessment": assessment,
                    }
                )
                attempts[attempts.index(attempt)] = updated
                best = _best(record, updated)
                record = record.model_copy(update={"attempts": tuple(attempts), "best_run": best})
                if assessment and assessment["accepted"]:
                    stopping = True
                    record = record.model_copy(
                        update={"stop_requested": True, "reason": "Engineering specification met"}
                    )
                elif (
                    result["terminal_state"] == "failed"
                    and attempt.retry < record.contract.max_retries
                    and not stopping
                ):
                    # Only sealed, terminal failures are eligible for retry.
                    record = record.model_copy(
                        update={"queue": (attempt.experiment_id, *record.queue)}
                    )
                _save(start, record)
            active = [a for a in attempts if a.state in {"submitting", "running"}]
            exhausted = len(attempts) >= record.contract.max_iterations or deadline
            if stopping or exhausted:
                state = (
                    "stopping"
                    if active
                    else (
                        "complete"
                        if record.conclusion is not None
                        or (
                            record.contract.mode == "engineering"
                            and any(a.assessment and a.assessment["accepted"] for a in attempts)
                        )
                        else "exhausted"
                        if exhausted
                        else "stopped"
                    )
                )
                return _save(
                    start, record.model_copy(update={"state": state, "stop_requested": True})
                )
            record = record.model_copy(
                update={"state": "running" if active else "ready", "reason": None}
            )
            while (
                record.queue
                and len(active) < record.contract.max_parallel
                and len(record.attempts) < record.contract.max_iterations
            ):
                if (
                    datetime.now(UTC) - datetime.fromisoformat(record.authorized_at)
                ).total_seconds() >= record.contract.max_seconds:
                    return _save(
                        start,
                        record.model_copy(
                            update={
                                "state": "stopping" if active else "exhausted",
                                "stop_requested": True,
                            }
                        ),
                    )
                if _stop_path(start, identifier).exists():
                    return _save(
                        start,
                        record.model_copy(update={"state": "stopping", "stop_requested": True}),
                    )
                experiment = record.queue[0]
                if any(a.experiment_id == experiment for a in active):
                    break
                commit = _validate_candidate(start, record, experiment)
                previous = [a for a in record.attempts if a.experiment_id == experiment]
                if previous and previous[-1].commit_sha != commit:
                    raise StudyError("Retry candidate changed; restore the exact failed commit")
                retry = len(previous)
                attempt = EvaluationAttempt(
                    run_id=f"run-{uuid4().hex[:16]}",
                    experiment_id=experiment,
                    commit_sha=commit,
                    state="submitting",
                    retry=retry,
                )
                record = _save(
                    start,
                    record.model_copy(
                        update={
                            "queue": record.queue[1:],
                            "attempts": (*record.attempts, attempt),
                            "state": "running",
                        }
                    ),
                )
                # The run ID is saved before crossing the external submission boundary.
                result = start_torc_run(
                    start,
                    experiment,
                    profile_name=record.profile,
                    machine_config_file=machine_config_path(),
                    run_id=attempt.run_id,
                    study_context={
                        "study_id": record.id,
                        "contract": record.contract.model_dump(mode="json"),
                        "contract_hash": record.contract_hash,
                        "execution_hash": record.execution_hash,
                        "evaluation_hash": record.evaluation_hash,
                    },
                )
                updated = attempt.model_copy(
                    update={"state": "running", "result": result.model_dump(mode="json")}
                )
                record = _save(
                    start, record.model_copy(update={"attempts": (*record.attempts[:-1], updated)})
                )
                active.append(updated)
            return _save(start, record)
        except (WaterologyError, ValueError, OSError, KeyError, RuntimeError) as error:
            # Store the error class, not a possibly credential-bearing remote message.
            reason = (
                str(error)
                if isinstance(error, StudyError)
                else f"{type(error).__name__}: inspect saved run identity and TORC status; no fallback or resubmission"
            )
            return _save(start, record.model_copy(update={"state": "blocked", "reason": reason}))


def _stop_path(start: Path, identifier: str) -> Path:
    return _path(start, identifier).with_suffix(".stop")


def stop_study(start: Path, identifier: str) -> StudyRecord:
    record = load_study(start, identifier)
    if record.state not in {"complete", "exhausted", "stopped"}:
        # Persist the stop before waiting for a controller holding the project lock.
        write_json(_stop_path(start, identifier), {"requested_at": _now()})
    result = advance_study(start, identifier)
    if (_directory(start) / f"{identifier}.driver").is_file():
        from waterology.core.study_driver import drive_study

        try:
            driver_result = drive_study(start, identifier)
            if driver_result["driver"].get("draining"):
                with project_state_lock(start):
                    result = _save(
                        start,
                        load_study(start, identifier).model_copy(
                            update={
                                "state": "stopping",
                                "reason": "Authorized candidate session is draining",
                            }
                        ),
                    )
        except (WaterologyError, ValueError, OSError, RuntimeError) as error:
            with project_state_lock(start):
                result = _save(
                    start,
                    load_study(start, identifier).model_copy(
                        update={
                            "state": "blocked",
                            "reason": f"{type(error).__name__}: candidate cancellation unresolved",
                        }
                    ),
                )
    return result


def guard_submission(start: Path, experiment_id: str, study_id: str | None = None) -> None:
    """Prevent generic execution from bypassing a managed study's routing."""
    for record in list_studies(start):
        driver_path = _directory(start) / f"{record.id}.driver"
        driver_owned = False
        if driver_path.exists():
            if driver_path.is_symlink():
                raise StudyError("Driver record must not be a symlink")
            driver = json.loads(driver_path.read_text())
            driver_owned = any(
                p["experiment_id"] == experiment_id and p["state"] != "evaluating"
                for p in driver["proposals"]
            )
        owned = driver_owned or (
            (record.state not in {"complete", "exhausted", "stopped"})
            and (
                experiment_id in record.queue
                or any(a.experiment_id == experiment_id for a in record.attempts)
            )
        )
        if owned and record.id != study_id:
            raise StudyError(
                "Candidate belongs to a managed study; use study advance with its pinned profile"
            )


def conclude_study(
    start: Path, identifier: str, *, conclusion: str, evidence: list[str], author: str
) -> StudyRecord:
    """Record an evidence-backed research conclusion, including a negative finding."""
    from waterology.core.claims import list_claims, verify_claim

    if not conclusion.strip() or not author.strip() or not evidence:
        raise StudyError("A research conclusion needs an author and assessed claim evidence")
    with project_state_lock(start):
        record = load_study(start, identifier)
        if record.contract.mode != "research" or record.conclusion is not None:
            raise StudyError(
                "Only a research study without a completed conclusion accepts a conclusion"
            )
        claims = {c.id: c for c in list_claims(start)}
        run_ids = {a.run_id for a in record.attempts}
        for identifier_claim in evidence:
            claim = claims.get(identifier_claim)
            if (
                claim is None
                or claim.run_id not in run_ids
                or verify_claim(start, claim)["status"] not in {"PASS", "EXPLAINED"}
            ):
                raise StudyError("Conclusion evidence must be assessed claims from this study")
        _save(
            start,
            record.model_copy(
                update={
                    "conclusion": {
                        "text": conclusion,
                        "evidence": evidence,
                        "author": author,
                        "created_at": _now(),
                    },
                    "stop_requested": True,
                    "state": "stopping",
                    "reason": "Research conclusion recorded",
                }
            ),
        )
    return stop_study(start, record.id)
