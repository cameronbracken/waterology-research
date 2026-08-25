import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from waterology.core.database import Database, open_database
from waterology.core.errors import WaterologyError
from waterology.core.git import add_worktree, branch_exists, commit_contains, resolve_commit
from waterology.core.project import Project, discover_project
from waterology.core.records import (
    AssessmentRecord,
    ExperimentNoteRecord,
    ExperimentRecord,
    WorktreeRecord,
)

_EXPERIMENT_ID = re.compile(r"^exp-[a-z0-9][a-z0-9-]{0,62}$")


class ExperimentConflictError(WaterologyError):
    code = "experiment_conflict"


class ExperimentNotFoundError(WaterologyError):
    code = "experiment_not_found"


def create_experiment(
    start: Path,
    *,
    hypothesis: str,
    parent_ref: str = "HEAD",
    parent_experiment_id: str | None = None,
    owner: str | None = None,
    experiment_id: str | None = None,
) -> ExperimentRecord:
    project = discover_project(start)
    identifier = experiment_id or f"exp-{uuid4().hex[:12]}"
    _validate_identifier(identifier)
    hypothesis = hypothesis.strip()
    if not hypothesis:
        raise ValueError("hypothesis must not be blank")
    parent_commit = None
    if parent_experiment_id is not None:
        parent = load_experiment(project.root, parent_experiment_id)
        if parent.status != "frozen":
            raise ExperimentConflictError(
                f"Parent experiment must be frozen: {parent_experiment_id}"
            )
        if parent_ref != "HEAD":
            raise ValueError("--parent cannot be combined with --parent-experiment")
        parent_commit = _latest_answer_commit(project, parent.id)

    branch = f"waterology/{identifier}"
    worktree_relative = f".waterology/worktrees/{identifier}"
    worktree = project.root / worktree_relative
    record_directory = project.paths.experiments / identifier
    if branch_exists(project.root, branch):
        raise ExperimentConflictError(f"Experiment branch already exists: {branch}")
    if worktree.exists() or record_directory.exists():
        raise ExperimentConflictError(f"Experiment path already exists: {identifier}")

    base_commit = resolve_commit(project.root, parent_commit or parent_ref)
    if not commit_contains(project.root, base_commit, "waterology.toml"):
        raise ExperimentConflictError(f"Parent commit {base_commit} must contain waterology.toml")
    record = ExperimentRecord(
        id=identifier,
        project_id=project.config.name,
        parent_experiment_id=parent_experiment_id,
        hypothesis=hypothesis,
        base_commit=base_commit,
        branch=branch,
        worktree=worktree_relative,
        owner=owner,
        created_at=_utc_now(),
    )

    with open_database(project.paths.database) as database:
        _index_project(database, project, record.created_at)
        intent = database.append_intent(
            kind="experiment.create",
            entity_type="experiment",
            entity_id=identifier,
            payload={"base_commit": base_commit, "branch": branch},
        )
        try:
            add_worktree(project.root, worktree, branch, base_commit)
            _write_experiment_record(record_directory, record)
            _index_experiment(database, record)
        except BaseException as error:
            database.append_observation(
                intent.id,
                payload={"error": type(error).__name__, "outcome": "failed"},
            )
            raise
        database.append_observation(intent.id, payload={"outcome": "created"})
    return record


def load_experiment(start: Path, experiment_id: str) -> ExperimentRecord:
    _validate_identifier(experiment_id)
    project = discover_project(start)
    path = project.paths.experiments / experiment_id / "experiment.json"
    if not path.is_file():
        raise ExperimentNotFoundError(f"Experiment does not exist: {experiment_id}")
    return _derive_experiment_state(project, _read_experiment_record(path))


def list_experiments(start: Path) -> tuple[ExperimentRecord, ...]:
    project = discover_project(start)
    if not project.paths.experiments.is_dir():
        return ()
    records = [
        _derive_experiment_state(project, _read_experiment_record(path))
        for path in project.paths.experiments.glob("exp-*/experiment.json")
    ]
    return tuple(sorted(records, key=lambda record: (record.created_at, record.id)))


def add_experiment_note(
    start: Path,
    experiment_id: str,
    text: str,
    *,
    author: str | None = None,
) -> ExperimentNoteRecord:
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    stripped = text.strip()
    if not stripped:
        raise ValueError("experiment note must not be blank")
    note = ExperimentNoteRecord(
        id=f"note-{uuid4().hex[:16]}",
        experiment_id=experiment.id,
        text=stripped,
        author=author.strip() if author else None,
        created_at=_utc_now(),
    )
    notes_directory = project.paths.experiments / experiment.id / "notes"
    with open_database(project.paths.database) as database:
        _index_project(database, project, experiment.created_at)
        _index_experiment(database, experiment)
        intent = database.append_intent(
            kind="experiment.note",
            entity_type="experiment",
            entity_id=experiment.id,
            payload={"note_id": note.id},
        )
        try:
            notes_directory.mkdir(exist_ok=True)
            _write_json_record(notes_directory / f"{note.id}.json", note)
        except BaseException as error:
            database.append_observation(
                intent.id,
                payload={"error": type(error).__name__, "outcome": "failed"},
            )
            raise
        database.append_observation(
            intent.id,
            payload={"note_id": note.id, "outcome": "created"},
        )
    return note


def list_experiment_notes(start: Path, experiment_id: str) -> tuple[ExperimentNoteRecord, ...]:
    project = discover_project(start)
    load_experiment(project.root, experiment_id)
    notes_directory = project.paths.experiments / experiment_id / "notes"
    if not notes_directory.is_dir():
        return ()
    notes = [_read_note_record(path) for path in notes_directory.glob("note-*.json")]
    return tuple(sorted(notes, key=lambda note: (note.created_at, note.id)))


def load_worktree(start: Path, experiment_id: str) -> WorktreeRecord:
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    path = _resolve_worktree_path(project, experiment)
    return WorktreeRecord(
        experiment_id=experiment.id,
        branch=experiment.branch,
        path=str(path),
        owner=experiment.owner,
        exists=path.is_dir(),
    )


def list_worktrees(start: Path) -> tuple[WorktreeRecord, ...]:
    project = discover_project(start)
    return tuple(
        load_worktree(project.root, experiment.id) for experiment in list_experiments(start)
    )


def ensure_experiment_index(
    database: Database,
    project: Project,
    experiment: ExperimentRecord,
) -> None:
    _index_project(database, project, experiment.created_at)
    _index_experiment(database, experiment)


def _index_project(database: Database, project: Project, created_at: str) -> None:
    with database.connection:
        database.connection.execute(
            """
            INSERT OR IGNORE INTO projects (
                id, name, root, config_schema_version, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                project.config.name,
                project.config.name,
                str(project.root),
                project.config.schema_version,
                created_at,
            ),
        )


def _index_experiment(database: Database, record: ExperimentRecord) -> None:
    with database.connection:
        database.connection.execute(
            """
            INSERT OR IGNORE INTO experiments (
                id, project_id, parent_experiment_id, hypothesis, base_commit,
                branch, worktree, owner, status, created_at, frozen_at,
                decision_required
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.project_id,
                record.parent_experiment_id,
                record.hypothesis,
                record.base_commit,
                record.branch,
                record.worktree,
                record.owner,
                record.status,
                record.created_at,
                record.frozen_at,
                int(record.decision_required),
            ),
        )


def _write_experiment_record(directory: Path, record: ExperimentRecord) -> None:
    directory.mkdir()
    _write_json_record(directory / "experiment.json", record)


def _write_json_record(
    destination: Path,
    record: ExperimentRecord | ExperimentNoteRecord,
) -> None:
    staged = destination.with_name(f".{destination.name}.tmp")
    staged.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    staged.replace(destination)


def _read_experiment_record(path: Path) -> ExperimentRecord:
    try:
        return ExperimentRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise ValueError(f"Invalid experiment record: {path}") from error


def _read_note_record(path: Path) -> ExperimentNoteRecord:
    try:
        return ExperimentNoteRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise ValueError(f"Invalid experiment note record: {path}") from error


def _derive_experiment_state(
    project: Project,
    record: ExperimentRecord,
) -> ExperimentRecord:
    assessments = _experiment_assessments(project, record.id)
    answers = [assessment for assessment in assessments if assessment.kind == "answer"]
    if answers:
        answer = answers[-1]
        return record.model_copy(
            update={
                "decision_required": False,
                "frozen_at": answer.created_at,
                "status": "frozen",
            }
        )
    decision_required = len(assessments) >= 2 and all(
        assessment.kind == "no_answer" for assessment in assessments[-2:]
    )
    return record.model_copy(update={"decision_required": decision_required})


def _latest_answer_commit(project: Project, experiment_id: str) -> str:
    answers = [
        assessment
        for assessment in _experiment_assessments(project, experiment_id)
        if assessment.kind == "answer"
    ]
    if not answers:
        raise ExperimentConflictError(f"Parent experiment has no answer: {experiment_id}")
    return answers[-1].commit_sha


def _experiment_assessments(
    project: Project,
    experiment_id: str,
) -> tuple[AssessmentRecord, ...]:
    records = []
    for path in project.paths.assessments.glob("run-*/assessment-*.json"):
        try:
            assessment = AssessmentRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            raise ValueError(f"Invalid assessment record: {path}") from error
        if assessment.experiment_id == experiment_id:
            records.append(assessment)
    return tuple(sorted(records, key=lambda item: (item.created_at, item.id)))


def _resolve_worktree_path(project: Project, experiment: ExperimentRecord) -> Path:
    path = (project.root / experiment.worktree).resolve()
    try:
        path.relative_to(project.paths.worktrees.resolve())
    except ValueError as error:
        raise ValueError(f"Experiment worktree escapes local state: {experiment.id}") from error
    return path


def _validate_identifier(identifier: str) -> None:
    if _EXPERIMENT_ID.fullmatch(identifier) is None:
        raise ValueError(f"Invalid experiment identifier: {identifier}")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
