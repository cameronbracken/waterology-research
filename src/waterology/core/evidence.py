import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from pydantic import ValidationError

from waterology.core.archive import load_archive
from waterology.core.atomic import write_json
from waterology.core.database import open_database
from waterology.core.errors import WaterologyError
from waterology.core.experiments import ensure_experiment_index, load_experiment
from waterology.core.project import Project, discover_project, project_state_lock
from waterology.core.records import ArtifactReferenceRecord, EvidenceRecord, ExperimentRecord
from waterology.core.sessions import load_session

_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")


class EvidencePathError(WaterologyError):
    code = "evidence_path_invalid"


class EvidenceRelationshipError(WaterologyError):
    code = "evidence_relationship_invalid"


def register_evidence(
    start: Path,
    *,
    experiment_id: str,
    claim: str,
    kind: str = "note",
    path: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    evidence_id: str | None = None,
) -> EvidenceRecord:
    project = discover_project(start)
    with project_state_lock(project.root):
        return _register_evidence_locked(
            project.root,
            experiment_id=experiment_id,
            claim=claim,
            kind=kind,
            path=path,
            run_id=run_id,
            session_id=session_id,
            evidence_id=evidence_id,
        )


def _register_evidence_locked(
    start: Path,
    *,
    experiment_id: str,
    claim: str,
    kind: str = "note",
    path: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    evidence_id: str | None = None,
) -> EvidenceRecord:
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    stripped = claim.strip()
    if not stripped:
        raise ValueError("evidence claim must not be blank")
    _validate_relationships(project, experiment.id, run_id, session_id)
    normalized = (
        validate_evidence_reference_path(project, experiment, path, run_id=run_id)
        if path
        else None
    )
    record = EvidenceRecord(
        id=evidence_id or f"evidence-{uuid4().hex[:16]}",
        experiment_id=experiment.id,
        claim=stripped,
        kind=kind,
        path=normalized,
        run_id=run_id,
        session_id=session_id,
        created_at=_utc_now(),
    )
    destination = project.paths.evidence / f"{record.id}.json"
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Evidence record already exists: {record.id}")
    _write_record(destination, record.model_dump(mode="json"))
    try:
        with open_database(project.paths.database) as database:
            ensure_experiment_index(database, project, experiment)
            with database.connection:
                database.connection.execute(
                    """
                    INSERT INTO evidence (
                        id, experiment_id, claim, kind, path, run_id, session_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.experiment_id,
                        record.claim,
                        record.kind,
                        record.path,
                        record.run_id,
                        record.session_id,
                        record.created_at,
                    ),
                )
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return record


def register_artifact_reference(
    start: Path,
    *,
    experiment_id: str,
    path: str,
    label: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    artifact_id: str | None = None,
) -> ArtifactReferenceRecord:
    project = discover_project(start)
    with project_state_lock(project.root):
        return _register_artifact_reference_locked(
            project.root,
            experiment_id=experiment_id,
            path=path,
            label=label,
            run_id=run_id,
            session_id=session_id,
            artifact_id=artifact_id,
        )


def _register_artifact_reference_locked(
    start: Path,
    *,
    experiment_id: str,
    path: str,
    label: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    artifact_id: str | None = None,
) -> ArtifactReferenceRecord:
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    _validate_relationships(project, experiment.id, run_id, session_id)
    normalized = validate_evidence_reference_path(project, experiment, path, run_id=run_id)
    record = ArtifactReferenceRecord(
        id=artifact_id or f"artifact-{uuid4().hex[:16]}",
        experiment_id=experiment.id,
        path=normalized,
        label=label.strip() if label else None,
        run_id=run_id,
        session_id=session_id,
        created_at=_utc_now(),
    )
    destination = project.paths.evidence / f"{record.id}.json"
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Artifact reference already exists: {record.id}")
    _write_record(destination, record.model_dump(mode="json"))
    try:
        with open_database(project.paths.database) as database:
            ensure_experiment_index(database, project, experiment)
            with database.connection:
                database.connection.execute(
                    """
                    INSERT INTO artifact_references (
                        id, experiment_id, path, label, run_id, session_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.experiment_id,
                        record.path,
                        record.label,
                        record.run_id,
                        record.session_id,
                        record.created_at,
                    ),
                )
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return record


def list_evidence(
    start: Path,
    *,
    experiment_id: str | None = None,
) -> tuple[EvidenceRecord, ...]:
    project = discover_project(start)
    records = []
    for path in project.paths.evidence.glob("evidence-*.json"):
        if path.is_symlink():
            raise EvidencePathError(f"Evidence record must not be a symlink: {path}")
        try:
            record = EvidenceRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            raise ValueError(f"Invalid evidence record: {path}") from error
        if experiment_id is None or record.experiment_id == experiment_id:
            records.append(record)
    return tuple(sorted(records, key=lambda record: (record.created_at, record.id)))


def list_artifact_references(
    start: Path,
    *,
    experiment_id: str | None = None,
) -> tuple[ArtifactReferenceRecord, ...]:
    project = discover_project(start)
    records = []
    for path in project.paths.evidence.glob("artifact-*.json"):
        if path.is_symlink():
            raise EvidencePathError(f"Artifact record must not be a symlink: {path}")
        try:
            record = ArtifactReferenceRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            raise ValueError(f"Invalid artifact reference: {path}") from error
        if experiment_id is None or record.experiment_id == experiment_id:
            records.append(record)
    return tuple(sorted(records, key=lambda record: (record.created_at, record.id)))


def validate_evidence_reference_path(
    project: Project,
    experiment: ExperimentRecord,
    value: str,
    *,
    run_id: str | None,
) -> str:
    portable = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or portable.is_absolute()
        or _WINDOWS_ABSOLUTE.match(value)
        or ".." in portable.parts
    ):
        raise EvidencePathError("Evidence paths must be relative project paths")
    candidate = project.root.joinpath(*portable.parts)
    _reject_symlink_components(project.root, candidate)
    if not candidate.is_file():
        raise EvidencePathError(f"Evidence path is not an existing file: {value}")
    resolved = candidate.resolve()
    worktree_root = (project.root / experiment.worktree).resolve()
    if _is_within(resolved, worktree_root):
        if run_id is not None:
            raise EvidenceRelationshipError(
                "Evidence tied to a run must use a file from that run archive"
            )
        return portable.as_posix()
    if _is_within(resolved, project.paths.worktrees.resolve()):
        raise EvidenceRelationshipError("Evidence worktree belongs to another experiment")
    runs_root = project.paths.runs.resolve()
    if not _is_within(resolved, runs_root):
        raise EvidencePathError("Evidence path must be inside the experiment worktree or run archive")
    relative_archive = resolved.relative_to(runs_root)
    if len(relative_archive.parts) < 2:
        raise EvidencePathError("Evidence path must identify a file inside one run archive")
    path_run_id = relative_archive.parts[0]
    run = load_archive(project.root, path_run_id)
    if run.experiment_id != experiment.id:
        raise EvidenceRelationshipError("Evidence archive belongs to another experiment")
    if run_id is not None and run_id != path_run_id:
        raise EvidenceRelationshipError("Evidence path does not match its declared run")
    return portable.as_posix()


def _validate_relationships(
    project: Project,
    experiment_id: str,
    run_id: str | None,
    session_id: str | None,
) -> None:
    if run_id is not None:
        run = load_archive(project.root, run_id)
        if run.experiment_id != experiment_id:
            raise EvidenceRelationshipError("Evidence run belongs to another experiment")
    if session_id is not None:
        session = load_session(project.root, session_id)
        if session.experiment_id != experiment_id:
            raise EvidenceRelationshipError("Evidence session belongs to another experiment")


def _reject_symlink_components(root: Path, candidate: Path) -> None:
    current = root
    try:
        parts = candidate.relative_to(root).parts
    except ValueError as error:
        raise EvidencePathError("Evidence path escapes the project") from error
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise EvidencePathError(f"Evidence path must not contain a symlink: {candidate}")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _write_record(path: Path, payload: dict[str, object]) -> None:
    write_json(path, payload)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
