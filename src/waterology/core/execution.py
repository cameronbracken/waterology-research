import json
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from waterology.core.archive import build_run_archive, load_archive
from waterology.core.config import ProjectConfig, load_project_config
from waterology.core.database import Database, open_database
from waterology.core.errors import WaterologyError
from waterology.core.experiments import (
    ensure_experiment_index,
    load_experiment,
    load_worktree,
)
from waterology.core.git import current_branch, current_commit, is_ancestor, is_clean
from waterology.core.project import Project, discover_project
from waterology.core.records import ExperimentRecord, RunManifest

_RUN_ID = re.compile(r"^run-[a-z0-9][a-z0-9-]{0,62}$")


class RunPreparationError(WaterologyError):
    code = "run_preparation_failed"


class RunExecutionError(WaterologyError):
    code = "run_execution_failed"


class MetricExtractionError(WaterologyError):
    code = "metric_extraction_failed"


@dataclass(frozen=True)
class RunInputs:
    project: Project
    experiment: ExperimentRecord
    worktree: Path
    config: ProjectConfig
    run_id: str
    commit_sha: str


def start_direct_run(
    start: Path,
    experiment_id: str,
    *,
    run_id: str | None = None,
) -> RunManifest:
    from waterology.core.studies import guard_submission

    guard_submission(start, experiment_id)
    inputs = prepare_run_inputs(start, experiment_id, run_id=run_id)
    if inputs.experiment.workflow is not None or inputs.config.torc_file:
        raise RunPreparationError("Named workflows require TORC execution")
    project = inputs.project
    experiment = inputs.experiment
    worktree = inputs.worktree
    config = inputs.config
    identifier = inputs.run_id
    commit_sha = inputs.commit_sha

    started_at = _utc_now()
    with open_database(project.paths.database) as database:
        ensure_experiment_index(database, project, experiment)
        _reserve_run(
            database,
            identifier,
            experiment.id,
            commit_sha,
            started_at,
            max_runs=config.concurrency.max_runs if config.concurrency is not None else None,
        )
        _transition(database, identifier, "queued", "preparing")
        staging = _prepare_execution_staging(
            project.paths.staging / identifier,
            experiment_id=experiment.id,
            run_id=identifier,
            commit_sha=commit_sha,
            command=config.command,
            started_at=started_at,
        )
        launch_intent = database.append_intent(
            kind="run.launch",
            entity_type="run",
            entity_id=identifier,
            payload={"command": list(config.command), "worktree": experiment.worktree},
        )
        try:
            with (
                (staging / "stdout.log").open("wb") as stdout_stream,
                (staging / "stderr.log").open("wb") as stderr_stream,
            ):
                process = _launch(config.command, worktree, stdout_stream, stderr_stream)
                _write_execution_metadata(
                    staging,
                    experiment_id=experiment.id,
                    run_id=identifier,
                    commit_sha=commit_sha,
                    command=config.command,
                    started_at=started_at,
                    state="running",
                    process_id=process.pid,
                )
                database.append_observation(
                    launch_intent.id,
                    payload={"outcome": "started", "process_id": process.pid},
                )
                _set_process_id(database, identifier, process.pid)
                _transition(database, identifier, "preparing", "running")
                process.wait()
        except RunExecutionError as error:
            finished_at = _utc_now()
            _write_execution_metadata(
                staging,
                experiment_id=experiment.id,
                run_id=identifier,
                commit_sha=commit_sha,
                command=config.command,
                started_at=started_at,
                state="failed",
                process_id=None,
                finished_at=finished_at,
                exit_code=None,
            )
            database.append_observation(
                launch_intent.id,
                payload={"error": str(error), "outcome": "failed"},
            )
            _transition(
                database,
                identifier,
                "preparing",
                "collecting",
                finished_at=finished_at,
            )
            archive = build_run_archive(
                project.root,
                experiment_id=experiment.id,
                run_id=identifier,
                commit_sha=commit_sha,
                command=config.command,
                started_at=started_at,
                finished_at=finished_at,
                terminal_state="failed",
                exit_code=None,
                stdout=(staging / "stdout.log").read_text(encoding="utf-8"),
                stderr=(staging / "stderr.log").read_text(encoding="utf-8"),
                metrics={},
                process_id=None,
                config=config,
            )
            _transition(
                database,
                identifier,
                "collecting",
                "failed",
                archive_path=archive.relative_to(project.root).as_posix(),
            )
            raise
        finished_at = _utc_now()
        terminal_state = "completed" if process.returncode == 0 else "failed"
        _write_execution_metadata(
            staging,
            experiment_id=experiment.id,
            run_id=identifier,
            commit_sha=commit_sha,
            command=config.command,
            started_at=started_at,
            state=terminal_state,
            process_id=process.pid,
            finished_at=finished_at,
            exit_code=process.returncode,
        )
        stdout = (staging / "stdout.log").read_bytes().decode("utf-8", errors="replace")
        stderr = (staging / "stderr.log").read_bytes().decode("utf-8", errors="replace")
        _transition(
            database,
            identifier,
            "running",
            "collecting",
            exit_code=process.returncode,
            finished_at=finished_at,
        )
        metrics = _extract_metrics(config, worktree, required=terminal_state == "completed")
        archive = build_run_archive(
            project.root,
            experiment_id=experiment.id,
            run_id=identifier,
            commit_sha=commit_sha,
            command=config.command,
            started_at=started_at,
            finished_at=finished_at,
            terminal_state=terminal_state,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            metrics=metrics,
            process_id=process.pid,
            config=config,
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


def prepare_run_inputs(
    start: Path,
    experiment_id: str,
    *,
    run_id: str | None = None,
) -> RunInputs:
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    worktree_record = load_worktree(project.root, experiment_id)
    worktree = Path(worktree_record.path)
    identifier = run_id or f"run-{uuid4().hex[:12]}"
    if _RUN_ID.fullmatch(identifier) is None:
        raise ValueError(f"Invalid run identifier: {identifier}")
    if experiment.status == "frozen":
        raise RunPreparationError(f"Experiment is frozen: {experiment_id}")
    if not worktree_record.exists:
        raise RunPreparationError(f"Experiment worktree is missing: {experiment_id}")
    config = load_project_config(worktree / "waterology.toml")
    if experiment.workflow:
        from waterology.core.registry import resolve_workflow

        config = resolve_workflow(worktree, experiment.workflow)
    if config.name != experiment.project_id:
        raise RunPreparationError(
            f"Experiment project {experiment.project_id} does not match waterology.toml"
        )
    if not config.command:
        raise RunPreparationError("waterology.toml does not define a run command")
    if not is_clean(worktree):
        raise RunPreparationError(f"Experiment worktree must be clean: {experiment_id}")
    if current_branch(worktree) != experiment.branch:
        raise RunPreparationError(
            f"Experiment worktree is not on its recorded branch: {experiment.branch}"
        )
    commit_sha = current_commit(worktree)
    if not is_ancestor(worktree, experiment.base_commit, commit_sha):
        raise RunPreparationError(
            f"Experiment commit is not descended from its base commit: {experiment_id}"
        )
    if commit_sha == experiment.base_commit and experiment.workflow is None:
        raise RunPreparationError(f"Experiment must contain a committed variant: {experiment_id}")

    return RunInputs(project, experiment, worktree, config, identifier, commit_sha)


def _launch(
    command: tuple[str, ...],
    worktree: Path,
    stdout: object,
    stderr: object,
) -> subprocess.Popen[bytes]:
    try:
        return subprocess.Popen(
            list(command),
            cwd=worktree,
            shell=False,
            stdout=stdout,
            stderr=stderr,
        )
    except OSError as error:
        raise RunExecutionError(f"Unable to start direct run: {error}") from error


def _prepare_execution_staging(
    staging: Path,
    *,
    experiment_id: str,
    run_id: str,
    commit_sha: str,
    command: tuple[str, ...],
    started_at: str,
) -> Path:
    if staging.exists() or staging.is_symlink():
        raise RunPreparationError(f"Run staging path already exists: {run_id}")
    staging.mkdir()
    (staging / "stdout.log").touch()
    (staging / "stderr.log").touch()
    _write_execution_metadata(
        staging,
        experiment_id=experiment_id,
        run_id=run_id,
        commit_sha=commit_sha,
        command=command,
        started_at=started_at,
        state="preparing",
        process_id=None,
    )
    return staging


def _write_execution_metadata(
    staging: Path,
    *,
    experiment_id: str,
    run_id: str,
    commit_sha: str,
    command: tuple[str, ...],
    started_at: str,
    state: str,
    process_id: int | None,
    finished_at: str | None = None,
    exit_code: int | None = None,
) -> None:
    payload = {
        "command": list(command),
        "commit_sha": commit_sha,
        "exit_code": exit_code,
        "experiment_id": experiment_id,
        "finished_at": finished_at,
        "process_id": process_id,
        "run_id": run_id,
        "schema_version": 1,
        "started_at": started_at,
        "state": state,
    }
    destination = staging / "execution.json"
    temporary = staging / ".execution.json.tmp"
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)


def _reserve_run(
    database: Database,
    run_id: str,
    experiment_id: str,
    commit_sha: str,
    started_at: str,
    *,
    max_runs: int | None,
    executor: str = "direct",
    compute_profile: str | None = None,
) -> None:
    active_states = ("queued", "preparing", "running", "collecting", "unknown")
    try:
        database.connection.execute("BEGIN IMMEDIATE")
        active = database.connection.execute(
            f"SELECT id, experiment_id FROM runs WHERE operational_state IN "
            f"({', '.join('?' for _ in active_states)}) ORDER BY started_at",
            active_states,
        ).fetchall()
        same_experiment = next(
            (row["id"] for row in active if row["experiment_id"] == experiment_id),
            None,
        )
        if same_experiment is not None:
            raise RunPreparationError(
                f"Experiment already has an active run: {same_experiment}",
                details={"active_run_id": same_experiment},
            )
        if max_runs is not None and len(active) >= max_runs:
            raise RunPreparationError(
                f"Project concurrency limit reached ({max_runs})",
                details={"active_run_ids": [row["id"] for row in active]},
            )
        database.connection.execute(
            """
            INSERT INTO runs (
                id, experiment_id, commit_sha, operational_state, executor,
                compute_profile, started_at
            ) VALUES (?, ?, ?, 'queued', ?, ?, ?)
            """,
            (run_id, experiment_id, commit_sha, executor, compute_profile, started_at),
        )
        database.connection.commit()
    except sqlite3.IntegrityError as error:
        database.connection.rollback()
        raise RunPreparationError(f"Run identifier already exists: {run_id}") from error
    except BaseException:
        database.connection.rollback()
        raise


def _extract_metrics(
    config: ProjectConfig,
    worktree: Path,
    *,
    required: bool,
) -> dict[str, object]:
    metrics: dict[str, object] = {}
    root = worktree.resolve()
    for extractor in config.metrics:
        path = worktree / extractor.path
        if not path.exists():
            if required:
                raise MetricExtractionError(f"Metric source does not exist: {extractor.path}")
            continue
        try:
            path.resolve().relative_to(root)
        except ValueError as error:
            raise MetricExtractionError(
                f"Metric source escapes the experiment worktree: {extractor.path}"
            ) from error
        try:
            value: object = json.loads(path.read_text(encoding="utf-8"))
            for component in extractor.field.split("."):
                if not isinstance(value, dict) or component not in value:
                    raise KeyError(component)
                value = value[component]
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as error:
            if required:
                raise MetricExtractionError(
                    f"Unable to extract metric {extractor.name} from {extractor.path}"
                ) from error
            continue
        metrics[extractor.name] = value
    return metrics


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
