import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from waterology.core.archive import ArchiveError, list_archives, verify_project_archive
from waterology.core.assessments import list_assessments
from waterology.core.database import Database, open_database
from waterology.core.experiments import ensure_experiment_index, list_experiments
from waterology.core.project import Project, discover_project
from waterology.core.records import (
    AssessmentRecord,
    ExperimentRecord,
    RepairResult,
    RunManifest,
)


def repair_index(start: Path) -> RepairResult:
    project = discover_project(start)
    experiments = list_experiments(project.root)
    runs = list_archives(project.root)
    _validate_archives(project, runs)
    assessments = tuple(
        assessment for run in runs for assessment in list_assessments(project.root, run.run_id)
    )
    artifacts = tuple(artifact for run in runs for artifact in _archive_artifacts(project, run))
    result = RepairResult(
        projects=1,
        experiments=len(experiments),
        runs=len(runs),
        assessments=len(assessments),
        artifacts=len(artifacts),
    )

    temporary = project.paths.database.with_name(f".state.sqlite.repair-{uuid4().hex[:12]}.sqlite")
    intent_id = ""
    try:
        with open_database(temporary) as database:
            intent = database.append_intent(
                kind="index.repair",
                entity_type="project",
                entity_id=project.config.name,
                payload=result.model_dump(mode="json"),
            )
            intent_id = intent.id
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
            database.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            database.connection.execute("PRAGMA journal_mode = DELETE")
        _replace_database(temporary, project.paths.database)
    except BaseException:
        _remove_database_files(temporary)
        raise

    with open_database(project.paths.database) as database:
        database.append_observation(intent_id, payload={"outcome": "repaired"})
    return result


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
    if destination.exists():
        try:
            connection = sqlite3.connect(destination)
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.close()
        except sqlite3.DatabaseError:
            pass
    _remove_database_sidecars(destination)
    temporary.replace(destination)


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
