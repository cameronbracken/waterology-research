import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from waterology.core.archive import build_run_archive, load_archive
from waterology.core.database import Database, open_database
from waterology.core.errors import WaterologyError
from waterology.core.experiments import (
    ensure_experiment_index,
    load_experiment,
    load_worktree,
)
from waterology.core.git import current_commit, is_clean
from waterology.core.project import discover_project
from waterology.core.records import RunManifest

_RUN_ID = re.compile(r"^run-[a-z0-9][a-z0-9-]{0,62}$")


class RunPreparationError(WaterologyError):
    code = "run_preparation_failed"


class RunExecutionError(WaterologyError):
    code = "run_execution_failed"


def start_direct_run(
    start: Path,
    experiment_id: str,
    *,
    run_id: str | None = None,
) -> RunManifest:
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    worktree_record = load_worktree(project.root, experiment_id)
    worktree = Path(worktree_record.path)
    identifier = run_id or f"run-{uuid4().hex[:12]}"
    if _RUN_ID.fullmatch(identifier) is None:
        raise ValueError(f"Invalid run identifier: {identifier}")
    if not project.config.command:
        raise RunPreparationError("waterology.toml does not define a run command")
    if not worktree_record.exists:
        raise RunPreparationError(f"Experiment worktree is missing: {experiment_id}")
    if not is_clean(worktree):
        raise RunPreparationError(f"Experiment worktree must be clean: {experiment_id}")
    commit_sha = current_commit(worktree)
    if commit_sha == experiment.base_commit:
        raise RunPreparationError(f"Experiment must contain a committed variant: {experiment_id}")

    started_at = _utc_now()
    with open_database(project.paths.database) as database:
        ensure_experiment_index(database, project, experiment)
        _insert_run(database, identifier, experiment.id, commit_sha, started_at)
        _transition(database, identifier, "queued", "preparing")
        process = _launch(project.config.command, worktree)
        _set_process_id(database, identifier, process.pid)
        _transition(database, identifier, "preparing", "running")
        stdout, stderr = process.communicate()
        finished_at = _utc_now()
        terminal_state = "completed" if process.returncode == 0 else "failed"
        _transition(
            database,
            identifier,
            "running",
            "collecting",
            exit_code=process.returncode,
            finished_at=finished_at,
        )
        archive = build_run_archive(
            project.root,
            experiment_id=experiment.id,
            run_id=identifier,
            commit_sha=commit_sha,
            command=project.config.command,
            started_at=started_at,
            finished_at=finished_at,
            terminal_state=terminal_state,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            metrics={},
        )
        archive_relative = archive.relative_to(project.root).as_posix()
        _transition(
            database,
            identifier,
            "collecting",
            terminal_state,
            archive_path=archive_relative,
        )
    return load_archive(project.root, identifier)


def _launch(command: tuple[str, ...], worktree: Path) -> subprocess.Popen[str]:
    try:
        return subprocess.Popen(
            list(command),
            cwd=worktree,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as error:
        raise RunExecutionError(f"Unable to start direct run: {error}") from error


def _insert_run(
    database: Database,
    run_id: str,
    experiment_id: str,
    commit_sha: str,
    started_at: str,
) -> None:
    with database.connection:
        database.connection.execute(
            """
            INSERT INTO runs (
                id, experiment_id, commit_sha, operational_state, executor, started_at
            ) VALUES (?, ?, ?, 'queued', 'direct', ?)
            """,
            (run_id, experiment_id, commit_sha, started_at),
        )


def _set_process_id(database: Database, run_id: str, process_id: int) -> None:
    with database.connection:
        database.connection.execute(
            "UPDATE runs SET process_id = ? WHERE id = ?",
            (process_id, run_id),
        )


def _transition(
    database: Database,
    run_id: str,
    prior_state: str,
    state: str,
    *,
    exit_code: int | None = None,
    finished_at: str | None = None,
    archive_path: str | None = None,
) -> None:
    intent = database.append_intent(
        kind="run.transition",
        entity_type="run",
        entity_id=run_id,
        payload={"from": prior_state, "to": state},
    )
    assignments = ["operational_state = ?"]
    values: list[object] = [state]
    for column, value in (
        ("exit_code", exit_code),
        ("finished_at", finished_at),
        ("archive_path", archive_path),
    ):
        if value is not None:
            assignments.append(f"{column} = ?")
            values.append(value)
    values.append(run_id)
    with database.connection:
        database.connection.execute(
            f"UPDATE runs SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
    database.append_observation(
        intent.id,
        payload={"from": prior_state, "outcome": "recorded", "to": state},
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
