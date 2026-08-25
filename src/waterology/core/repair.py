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
from waterology.core.experiments import ensure_experiment_index, list_experiments
from waterology.core.project import Project, discover_project
from waterology.core.records import (
    AssessmentRecord,
    ExperimentRecord,
    RepairResult,
    RunManifest,
)

_EXPERIMENT_DIRECTORY = re.compile(r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
_RUN_DIRECTORY = re.compile(r"^run-[a-z0-9][a-z0-9-]{0,62}$")
_ASSESSMENT_FILE = re.compile(r"^assessment-[0-9a-f]{16}\.json$")


class RepairRecordError(WaterologyError):
    code = "repair_records_invalid"


def repair_index(start: Path) -> RepairResult:
    project = discover_project(start)
    validate_database_path(project.paths.database)
    _validate_durable_layout(project)
    experiments = list_experiments(project.root)
    runs = list_archives(project.root)
    _validate_archives(project, runs)
    _validate_record_relationships(project, experiments, runs)
    assessments = _load_assessments(project, runs)
    artifacts = tuple(artifact for run in runs for artifact in _archive_artifacts(project, run))
    result = RepairResult(
        projects=1,
        experiments=len(experiments),
        runs=len(runs),
        assessments=len(assessments),
        artifacts=len(artifacts),
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

    if rejected:
        paths = tuple(sorted(rejected))
        raise RepairRecordError(
            f"Repair rejected {len(paths)} malformed durable record location(s)",
            details={"paths": list(paths), "rejected_records": len(paths)},
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
    with database.connection:
        database.connection.execute(
            """
            INSERT INTO runs (
                id, experiment_id, commit_sha, operational_state, archive_path,
                executor, process_id, started_at, finished_at, exit_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
