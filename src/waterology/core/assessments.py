import json
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from pydantic import ValidationError

from waterology.core.archive import load_archive
from waterology.core.database import Database, open_database
from waterology.core.errors import WaterologyError
from waterology.core.experiments import ensure_experiment_index, load_experiment
from waterology.core.project import Project, discover_project
from waterology.core.records import AssessmentRecord, RunManifest

_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")


class AssessmentError(WaterologyError):
    code = "assessment_error"


class AssessmentEvidenceError(AssessmentError):
    code = "assessment_evidence_invalid"


def assess_run(
    start: Path,
    run_id: str,
    *,
    kind: str,
    conclusion: str,
    author: str,
    evidence: tuple[str, ...] = (),
    note: str | None = None,
) -> AssessmentRecord:
    project = discover_project(start)
    run = load_archive(project.root, run_id)
    experiment = load_experiment(project.root, run.experiment_id)
    if experiment.status == "frozen":
        raise AssessmentError(f"Experiment is frozen: {experiment.id}")
    conclusion = conclusion.strip()
    author = author.strip()
    if not conclusion:
        raise ValueError("assessment conclusion must not be blank")
    if not author:
        raise ValueError("assessment author must not be blank")
    if kind == "answer" and not evidence:
        raise AssessmentEvidenceError("An answer assessment must cite evidence")
    validated_evidence = tuple(_validate_evidence(project, run_id, item) for item in evidence)
    assessment = AssessmentRecord(
        id=f"assessment-{uuid4().hex[:16]}",
        run_id=run.run_id,
        experiment_id=run.experiment_id,
        commit_sha=run.commit_sha,
        kind=kind,
        conclusion=conclusion,
        author=author,
        evidence=validated_evidence,
        note=note.strip() if note else None,
        created_at=_utc_now(),
    )
    directory = _validated_assessment_directory(project, run.run_id, create=True)
    destination = directory / f"{assessment.id}.json"
    with open_database(project.paths.database) as database:
        ensure_experiment_index(database, project, experiment)
        _ensure_run_index(database, run)
        intent = database.append_intent(
            kind="run.assess",
            entity_type="run",
            entity_id=run.run_id,
            payload={"assessment_id": assessment.id, "kind": assessment.kind},
        )
        try:
            _write_assessment(destination, assessment)
            _index_assessment(database, assessment)
            derived = load_experiment(project.root, experiment.id)
            _update_experiment_state(database, derived)
        except BaseException as error:
            database.append_observation(
                intent.id,
                payload={"error": type(error).__name__, "outcome": "failed"},
            )
            raise
        database.append_observation(
            intent.id,
            payload={"assessment_id": assessment.id, "outcome": "created"},
        )
    return assessment


def list_assessments(start: Path, run_id: str) -> tuple[AssessmentRecord, ...]:
    project = discover_project(start)
    run = load_archive(project.root, run_id)
    directory = project.paths.assessments / run_id
    if not directory.exists() and not directory.is_symlink():
        return ()
    directory = _validated_assessment_directory(project, run_id, create=False)
    records = []
    for path in directory.glob("assessment-*.json"):
        try:
            assessment = AssessmentRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            raise AssessmentError(f"Invalid assessment record: {path}") from error
        if assessment.run_id != run_id:
            raise AssessmentError(
                f"Assessment run {assessment.run_id} does not match directory {run_id}"
            )
        if assessment.experiment_id != run.experiment_id:
            raise AssessmentError(
                f"Assessment experiment does not match run manifest: {assessment.id}"
            )
        if assessment.commit_sha != run.commit_sha:
            raise AssessmentError(f"Assessment commit does not match run manifest: {assessment.id}")
        for evidence in assessment.evidence:
            _validate_evidence(project, run_id, evidence)
        records.append(assessment)
    return tuple(sorted(records, key=lambda item: (item.created_at, item.id)))


def _validate_evidence(project: Project, run_id: str, value: str) -> str:
    if not value or "\\" in value or _WINDOWS_ABSOLUTE.match(value):
        raise AssessmentEvidenceError("Evidence must be a relative project path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise AssessmentEvidenceError("Evidence must be a relative project path")
    path = (project.root / relative.as_posix()).resolve()
    allowed_roots = [
        *(project.root / root for root in project.config.artifact_roots),
        project.paths.runs / run_id,
    ]
    if not any(_is_within(path, root.resolve()) for root in allowed_roots):
        raise AssessmentEvidenceError(f"Evidence is outside allowed roots: {value}")
    if not path.exists():
        raise AssessmentEvidenceError(f"Evidence does not exist: {value}")
    return relative.as_posix()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _ensure_run_index(database: Database, run: RunManifest) -> None:
    with database.connection:
        database.connection.execute(
            """
            INSERT OR IGNORE INTO runs (
                id, experiment_id, commit_sha, operational_state, archive_path,
                executor, started_at, finished_at, exit_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.experiment_id,
                run.commit_sha,
                run.terminal_state,
                f".waterology/runs/{run.run_id}",
                run.executor,
                run.started_at,
                run.finished_at,
                run.exit_code,
            ),
        )


def _index_assessment(database: Database, assessment: AssessmentRecord) -> None:
    with database.connection:
        database.connection.execute(
            """
            INSERT INTO assessments (
                id, run_id, kind, conclusion, author, evidence_json, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assessment.id,
                assessment.run_id,
                assessment.kind,
                assessment.conclusion,
                assessment.author,
                json.dumps(assessment.evidence),
                assessment.note,
                assessment.created_at,
            ),
        )


def _update_experiment_state(database: Database, experiment: object) -> None:
    with database.connection:
        database.connection.execute(
            """
            UPDATE experiments
            SET status = ?, frozen_at = ?, decision_required = ?
            WHERE id = ?
            """,
            (
                experiment.status,
                experiment.frozen_at,
                int(experiment.decision_required),
                experiment.id,
            ),
        )


def _write_assessment(path: Path, assessment: AssessmentRecord) -> None:
    staged = path.with_name(f".{path.name}.tmp")
    if path.exists() or path.is_symlink() or staged.exists() or staged.is_symlink():
        raise AssessmentError(f"Assessment record path already exists: {path}")
    with staged.open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(assessment.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        )
    staged.replace(path)


def _validated_assessment_directory(
    project: Project,
    run_id: str,
    *,
    create: bool,
) -> Path:
    directory = project.paths.assessments / run_id
    if directory.is_symlink():
        raise AssessmentError(f"Assessment directory must not be a symlink: {run_id}")
    if create:
        directory.mkdir(exist_ok=True)
    if not directory.is_dir():
        raise AssessmentError(f"Invalid assessment directory: {run_id}")
    try:
        directory.resolve().relative_to(project.paths.assessments.resolve())
    except ValueError as error:
        raise AssessmentError(f"Assessment directory escapes local state: {run_id}") from error
    return directory


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
