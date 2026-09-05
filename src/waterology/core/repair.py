import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from waterology.core.archive import ArchiveError, list_archives, verify_project_archive
from waterology.core.assessments import AssessmentError, list_assessments
from waterology.core.database import Database, open_database, validate_database_path
from waterology.core.errors import WaterologyError
from waterology.core.evidence import (
    EvidencePathError,
    EvidenceRelationshipError,
    list_artifact_references,
    list_evidence,
    validate_evidence_reference_path,
)
from waterology.core.experiments import ensure_experiment_index, list_experiments
from waterology.core.project import Project, discover_project, project_state_lock
from waterology.core.records import (
    AgentProcessRecord,
    AgentResultRecord,
    AgentSessionRecord,
    AgentStartingRecord,
    ArtifactReferenceRecord,
    AssessmentRecord,
    EvidenceRecord,
    ExperimentRecord,
    RepairResult,
    RunManifest,
    SessionNoteRecord,
)
from waterology.core.sessions import (
    SessionConflictError,
    SessionNotFoundError,
    ensure_session_index,
    list_session_notes,
    list_sessions,
)

_EXPERIMENT_DIRECTORY = re.compile(r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
_RUN_DIRECTORY = re.compile(r"^run-[a-z0-9][a-z0-9-]{0,62}$")
_ASSESSMENT_FILE = re.compile(r"^assessment-[0-9a-f]{16}\.json$")
_SESSION_DIRECTORY = re.compile(r"^session-[0-9a-f]{16}$")
_ATTEMPT_DIRECTORY = re.compile(r"^attempt-[0-9]{3}$")
_NOTE_FILE = re.compile(r"^note-[0-9a-f]{16}\.json$")
_EVIDENCE_FILE = re.compile(r"^(?:evidence|artifact)-[0-9a-f]{16}\.json$")
_ATOMIC_STAGING_FILE = re.compile(r"^\..+\.waterology-stage-[A-Za-z0-9_-]+$")


class RepairRecordError(WaterologyError):
    code = "repair_records_invalid"


def repair_index(start: Path) -> RepairResult:
    project = discover_project(start)
    with project_state_lock(project.root):
        return _repair_index_locked(project)


def _repair_index_locked(project: Project) -> RepairResult:
    from waterology.core.studies import list_studies
    if any(a.state in {"submitting", "running"} for study in list_studies(project.root) for a in study.attempts):
        raise RepairRecordError("Reconcile active or ambiguous study attempts before index repair")
    validate_database_path(project.paths.database)
    _validate_durable_layout(project)
    experiments = list_experiments(project.root)
    runs = list_archives(project.root)
    _validate_archives(project, runs)
    _validate_record_relationships(project, experiments, runs)
    assessments = _load_assessments(project, runs)
    artifacts = tuple(artifact for run in runs for artifact in _archive_artifacts(project, run))
    try:
        sessions = list_sessions(project.root)
        session_notes = tuple(
            note for session in sessions for note in list_session_notes(project.root, session.id)
        )
    except (SessionConflictError, SessionNotFoundError, ValueError) as error:
        raise RepairRecordError(str(error)) from error
    evidence = list_evidence(project.root)
    artifact_references = list_artifact_references(project.root)
    _validate_slice_five_relationships(
        project,
        experiments,
        runs,
        sessions,
        evidence,
        artifact_references,
    )
    result = RepairResult(
        projects=1,
        experiments=len(experiments),
        runs=len(runs),
        assessments=len(assessments),
        artifacts=len(artifacts),
        sessions=len(sessions),
        session_notes=len(session_notes),
        evidence=len(evidence),
        artifact_references=len(artifact_references),
    )

    temporary = project.paths.database.with_name(f".state.sqlite.repair-{uuid4().hex[:12]}.sqlite")
    try:
        with open_database(temporary) as database:
            intent = database.append_intent(
                kind="index.repair",
                entity_type="project",
                entity_id=project.config.name,
                payload=result.model_dump(mode="json"),
            )
            _import_project(database, project, experiments, runs)
            for experiment in experiments:
                ensure_experiment_index(database, project, experiment)
            for run in runs:
                _import_run(database, run)
            for assessment in assessments:
                _import_assessment(database, assessment)
            for artifact in artifacts:
                _import_artifact(database, *artifact)
            for session in sessions:
                ensure_session_index(database, session)
            for note in session_notes:
                _import_session_note(database, note)
            for record in evidence:
                _import_evidence(database, record)
            for record in artifact_references:
                _import_artifact_reference(database, record)
            integrity = database.connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise sqlite3.IntegrityError(
                    f"Repaired database failed integrity check: {integrity}"
                )
            foreign_keys = database.connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_keys:
                raise sqlite3.IntegrityError("Repaired database failed foreign key validation")
            database.append_observation(intent.id, payload={"outcome": "repaired"})
            database.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            database.connection.execute("PRAGMA journal_mode = DELETE")
        _replace_database(temporary, project.paths.database)
    except BaseException:
        _remove_database_files(temporary)
        raise

    return result


def _validate_durable_layout(project: Project) -> None:
    rejected = []
    for directory, pattern, required_file in (
        (project.paths.experiments, _EXPERIMENT_DIRECTORY, "experiment.json"),
        (project.paths.runs, _RUN_DIRECTORY, "manifest.json"),
    ):
        for child in directory.iterdir():
            if child.name == ".DS_Store":
                continue
            required = child / required_file
            if (
                child.is_symlink()
                or not child.is_dir()
                or pattern.fullmatch(child.name) is None
                or required.is_symlink()
                or not required.is_file()
            ):
                rejected.append(child.relative_to(project.root).as_posix())

    for directory in project.paths.assessments.iterdir():
        if directory.name == ".DS_Store":
            continue
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or _RUN_DIRECTORY.fullmatch(directory.name) is None
        ):
            rejected.append(directory.relative_to(project.root).as_posix())
            continue
        for record in directory.iterdir():
            if record.name == ".DS_Store":
                continue
            if (
                record.is_symlink()
                or not record.is_file()
                or _ASSESSMENT_FILE.fullmatch(record.name) is None
            ):
                rejected.append(record.relative_to(project.root).as_posix())

    for directory in project.paths.sessions.iterdir():
        if directory.name == ".DS_Store":
            continue
        record = directory / "session.json"
        task = directory / "task.md"
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or _SESSION_DIRECTORY.fullmatch(directory.name) is None
            or record.is_symlink()
            or not record.is_file()
            or task.is_symlink()
            or not task.is_file()
        ):
            rejected.append(directory.relative_to(project.root).as_posix())
            continue
        try:
            payload = json.loads(record.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or payload.get("id") != directory.name:
            rejected.append(record.relative_to(project.root).as_posix())
        allowed_root_files = {".lock", "session.json", "task.md"}
        for child in directory.iterdir():
            relative = child.relative_to(project.root).as_posix()
            if _is_atomic_staging_file(child):
                continue
            if child.is_symlink():
                rejected.append(relative)
            elif child.name in allowed_root_files and child.is_file():
                continue
            elif child.name == "notes" and child.is_dir():
                for note in child.iterdir():
                    if _is_atomic_staging_file(note):
                        continue
                    if (
                        note.is_symlink()
                        or not note.is_file()
                        or _NOTE_FILE.fullmatch(note.name) is None
                    ):
                        rejected.append(note.relative_to(project.root).as_posix())
                        continue
                    try:
                        note_payload = json.loads(note.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    if (
                        not isinstance(note_payload, dict)
                        or note_payload.get("id") != note.stem
                        or note_payload.get("session_id") != directory.name
                    ):
                        rejected.append(note.relative_to(project.root).as_posix())
            elif _ATTEMPT_DIRECTORY.fullmatch(child.name) and child.is_dir():
                required = {"events.jsonl", "prompt.md", "stderr.log"}
                optional = {
                    "launch.ready",
                    "process.json",
                    "result.json",
                    "runtime-starting.json",
                }
                items = tuple(
                    item for item in child.iterdir() if not _is_atomic_staging_file(item)
                )
                names = {item.name for item in items}
                if not required.issubset(names) or not names.issubset(required | optional):
                    rejected.append(relative)
                for item in items:
                    if item.is_symlink() or not item.is_file():
                        rejected.append(item.relative_to(project.root).as_posix())
                        continue
                    record_type = {
                        "process.json": AgentProcessRecord,
                        "result.json": AgentResultRecord,
                        "runtime-starting.json": AgentStartingRecord,
                    }.get(item.name)
                    if record_type is not None:
                        try:
                            record_type.model_validate_json(item.read_text(encoding="utf-8"))
                        except (OSError, ValueError):
                            rejected.append(item.relative_to(project.root).as_posix())
            else:
                rejected.append(relative)

    for record in project.paths.evidence.iterdir():
        if record.name == ".DS_Store":
            continue
        if _is_atomic_staging_file(record):
            continue
        if (
            record.is_symlink()
            or not record.is_file()
            or _EVIDENCE_FILE.fullmatch(record.name) is None
        ):
            rejected.append(record.relative_to(project.root).as_posix())
            continue
        try:
            payload = json.loads(record.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or payload.get("id") != record.stem:
            rejected.append(record.relative_to(project.root).as_posix())

    if rejected:
        paths = tuple(sorted(rejected))
        raise RepairRecordError(
            f"Repair rejected {len(paths)} malformed durable record location(s)",
            details={"paths": list(paths), "rejected_records": len(paths)},
        )


def _is_atomic_staging_file(path: Path) -> bool:
    return (
        not path.is_symlink()
        and path.is_file()
        and _ATOMIC_STAGING_FILE.fullmatch(path.name) is not None
    )


def _validate_record_relationships(
    project: Project,
    experiments: tuple[ExperimentRecord, ...],
    runs: tuple[RunManifest, ...],
) -> None:
    experiment_ids = {experiment.id for experiment in experiments}
    for experiment in experiments:
        if experiment.project_id != project.config.name:
            raise ValueError(f"Experiment project does not match configuration: {experiment.id}")
    for run in runs:
        if run.project_id != project.config.name:
            raise ArchiveError(f"Run project does not match configuration: {run.run_id}")
        if run.experiment_id not in experiment_ids:
            raise ArchiveError(f"Run references an unknown experiment: {run.run_id}")


def _validate_slice_five_relationships(
    project: Project,
    experiments: tuple[ExperimentRecord, ...],
    runs: tuple[RunManifest, ...],
    sessions: tuple[AgentSessionRecord, ...],
    evidence: tuple[EvidenceRecord, ...],
    artifact_references: tuple[ArtifactReferenceRecord, ...],
) -> None:
    experiment_by_id = {record.id: record for record in experiments}
    run_by_id = {record.run_id: record for record in runs}
    session_by_id = {record.id: record for record in sessions}
    for session in sessions:
        experiment = experiment_by_id.get(session.experiment_id)
        if experiment is None:
            raise RepairRecordError(f"Session references an unknown experiment: {session.id}")
        if session.project_id != project.config.name:
            raise RepairRecordError(f"Session project does not match configuration: {session.id}")
        if session.worktree != experiment.worktree:
            raise RepairRecordError(f"Session worktree does not match experiment: {session.id}")
        prefix = f".waterology/sessions/{session.id}"
        if session.task_path != f"{prefix}/task.md":
            raise RepairRecordError(f"Session task path does not match layout: {session.id}")
        for expected_number, attempt in enumerate(session.attempts, start=1):
            attempt_prefix = f"{prefix}/attempt-{expected_number:03d}"
            if attempt.number != expected_number or (
                attempt.prompt_path,
                attempt.events_path,
                attempt.stderr_path,
            ) != (
                f"{attempt_prefix}/prompt.md",
                f"{attempt_prefix}/events.jsonl",
                f"{attempt_prefix}/stderr.log",
            ):
                raise RepairRecordError(f"Session attempt path does not match layout: {session.id}")
        directory = project.paths.sessions / session.id
        actual_attempts = {
            child.name
            for child in directory.iterdir()
            if child.is_dir() and _ATTEMPT_DIRECTORY.fullmatch(child.name)
        }
        expected_attempts = {
            f"attempt-{number:03d}" for number in range(1, len(session.attempts) + 1)
        }
        if actual_attempts != expected_attempts:
            raise RepairRecordError(f"Session attempt directories do not match record: {session.id}")
    for record in (*evidence, *artifact_references):
        if record.experiment_id not in experiment_by_id:
            raise RepairRecordError(f"Record references an unknown experiment: {record.id}")
        if record.path is not None:
            try:
                validate_evidence_reference_path(
                    project,
                    experiment_by_id[record.experiment_id],
                    record.path,
                    run_id=record.run_id,
                )
            except (EvidencePathError, EvidenceRelationshipError) as error:
                raise RepairRecordError(f"Invalid evidence path relationship: {record.id}") from error
        if record.run_id is not None:
            run = run_by_id.get(record.run_id)
            if run is None:
                raise RepairRecordError(f"Record references an unknown run: {record.id}")
            if run.experiment_id != record.experiment_id:
                raise RepairRecordError(f"Record run belongs to another experiment: {record.id}")
        if record.session_id is not None:
            session = session_by_id.get(record.session_id)
            if session is None:
                raise RepairRecordError(f"Record references an unknown session: {record.id}")
            if session.experiment_id != record.experiment_id:
                raise RepairRecordError(
                    f"Record session belongs to another experiment: {record.id}"
                )


def _load_assessments(
    project: Project,
    runs: tuple[RunManifest, ...],
) -> tuple[AssessmentRecord, ...]:
    run_ids = {run.run_id for run in runs}
    for directory in project.paths.assessments.iterdir():
        if directory.name == ".DS_Store":
            continue
        if directory.name not in run_ids:
            raise AssessmentError(f"Assessment references an unknown run directory: {directory}")
    return tuple(
        assessment for run in runs for assessment in list_assessments(project.root, run.run_id)
    )


def _validate_archives(project: Project, runs: tuple[RunManifest, ...]) -> None:
    for run in runs:
        archive_directory = project.paths.runs / run.run_id
        if archive_directory.name != run.run_id:
            raise ArchiveError(f"Archive directory does not match run identifier: {run.run_id}")
        verification = verify_project_archive(project.root, run.run_id)
        if not verification.valid:
            raise ArchiveError(
                f"Run archive failed checksum verification: {run.run_id}",
                details=verification.model_dump(mode="json"),
            )


def _archive_artifacts(project: Project, run: RunManifest) -> tuple[tuple[str, str, int], ...]:
    artifacts = []
    root = project.paths.runs / run.run_id / "artifacts"
    for declared in run.collected_artifacts:
        path = root / declared
        files = tuple(path.rglob("*")) if path.is_dir() else (path,)
        for file in files:
            if not file.is_file():
                continue
            relative = file.relative_to(root).as_posix()
            artifacts.append((run.run_id, relative, file.stat().st_size))
    return tuple(artifacts)


def _import_project(
    database: Database,
    project: Project,
    experiments: tuple[ExperimentRecord, ...],
    runs: tuple[RunManifest, ...],
) -> None:
    timestamps = [
        *(experiment.created_at for experiment in experiments),
        *(run.started_at for run in runs),
    ]
    created_at = min(timestamps) if timestamps else _utc_now()
    with database.connection:
        database.connection.execute(
            """
            INSERT INTO projects (id, name, root, config_schema_version, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                project.config.name,
                project.config.name,
                str(project.root),
                project.config.schema_version,
                created_at,
            ),
        )


def _import_run(database: Database, run: RunManifest) -> None:
    reference = run.executor_reference
    with database.connection:
        database.connection.execute(
            """
            INSERT INTO runs (
                id, experiment_id, commit_sha, operational_state, archive_path,
                executor, process_id, started_at, finished_at, exit_code,
                compute_profile, workflow_id, job_ids_json, api_url,
                execution_mode, torc_version, workflow_spec_sha256, last_observed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.experiment_id,
                run.commit_sha,
                run.terminal_state,
                f".waterology/runs/{run.run_id}",
                run.executor,
                run.process_id,
                run.started_at,
                run.finished_at,
                run.exit_code,
                reference.compute_profile if reference else None,
                reference.workflow_id if reference else None,
                json.dumps(reference.job_ids if reference else ()),
                reference.api_url if reference else None,
                reference.execution_mode if reference else None,
                reference.torc_version if reference else None,
                reference.workflow_spec_sha256 if reference else None,
                run.finished_at if reference else None,
            ),
        )


def _import_assessment(database: Database, assessment: AssessmentRecord) -> None:
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


def _import_artifact(database: Database, run_id: str, path: str, size: int) -> None:
    archive_path = Path(
        database.connection.execute(
            "SELECT archive_path FROM runs WHERE id = ?", (run_id,)
        ).fetchone()[0]
    )
    project_root = Path(
        database.connection.execute("SELECT root FROM projects LIMIT 1").fetchone()[0]
    )
    payload = project_root / archive_path / "artifacts" / path
    identifier = "artifact-" + hashlib.sha256(f"{run_id}:{path}".encode()).hexdigest()[:20]
    with database.connection:
        database.connection.execute(
            "INSERT INTO artifacts (id, run_id, path, sha256, size) VALUES (?, ?, ?, ?, ?)",
            (identifier, run_id, path, _sha256(payload), size),
        )


def _import_session_note(database: Database, note: SessionNoteRecord) -> None:
    with database.connection:
        database.connection.execute(
            """
            INSERT INTO session_notes (id, session_id, text, author, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (note.id, note.session_id, note.text, note.author, note.created_at),
        )


def _import_evidence(database: Database, record: EvidenceRecord) -> None:
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


def _import_artifact_reference(database: Database, record: ArtifactReferenceRecord) -> None:
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


def _replace_database(temporary: Path, destination: Path) -> None:
    backups: dict[Path, Path] = {}
    try:
        for suffix in ("-wal", "-shm"):
            sidecar = destination.with_name(destination.name + suffix)
            if not sidecar.exists():
                continue
            backup = temporary.with_name(f"{temporary.name}.previous{suffix}")
            sidecar.replace(backup)
            backups[sidecar] = backup
        temporary.replace(destination)
    except BaseException:
        for sidecar, backup in backups.items():
            if backup.exists():
                backup.replace(sidecar)
        raise
    for backup in backups.values():
        try:
            backup.unlink(missing_ok=True)
        except OSError:
            pass


def _remove_database_files(path: Path) -> None:
    path.unlink(missing_ok=True)
    _remove_database_sidecars(path)


def _remove_database_sidecars(path: Path) -> None:
    path.with_name(path.name + "-wal").unlink(missing_ok=True)
    path.with_name(path.name + "-shm").unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
