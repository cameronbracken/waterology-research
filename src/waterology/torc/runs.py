import json
import os
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from waterology.core.archive import ArchiveNotFoundError, build_run_archive, load_archive
from waterology.core.config import load_project_config
from waterology.core.database import Database, open_database
from waterology.core.errors import WaterologyError
from waterology.core.execution import (
    _extract_metrics,
    _prepare_execution_staging,
    _reserve_run,
    _transition,
    prepare_run_inputs,
)
from waterology.core.experiments import ensure_experiment_index, load_experiment, load_worktree
from waterology.core.profiles import load_machine_config, trust_profile
from waterology.core.project import discover_project
from waterology.core.providers import PreparedRun, ProviderInspection
from waterology.core.records import ExecutorReference, ManagedRunRecord, RunManifest
from waterology.torc.gateway import TorcCliGateway, TorcGateway
from waterology.torc.provider import TorcProvider
from waterology.torc.workflow import TorcWorkflowRequest


class RemoteProfileConfirmationError(WaterologyError):
    code = "remote_profile_confirmation_required"


class TorcRunError(WaterologyError):
    code = "torc_run_failed"


def start_torc_run(
    start: Path,
    experiment_id: str,
    *,
    profile_name: str,
    machine_config_file: Path,
    run_id: str | None = None,
    confirm_remote: bool = False,
    gateway: TorcGateway | None = None,
) -> ManagedRunRecord:
    inputs = prepare_run_inputs(start, experiment_id, run_id=run_id)
    machine_config = load_machine_config(machine_config_file)
    profile = machine_config.profile(profile_name)
    if profile.mode != "local" and not profile.trusted:
        if not confirm_remote:
            raise RemoteProfileConfirmationError(
                f"Compute profile requires confirmation before first use: {profile_name}",
                details={"mode": profile.mode, "profile": profile_name},
            )
        machine_config = trust_profile(machine_config_file, profile_name)
        profile = machine_config.profile(profile_name)

    started_at = _utc_now()
    selected_gateway = gateway or TorcCliGateway(profile.api_url)
    with open_database(inputs.project.paths.database) as database:
        ensure_experiment_index(database, inputs.project, inputs.experiment)
        _reserve_run(
            database,
            inputs.run_id,
            inputs.experiment.id,
            inputs.commit_sha,
            started_at,
            max_runs=inputs.config.concurrency.max_runs,
            executor="torc",
            compute_profile=profile_name,
        )
        _transition(database, inputs.run_id, "queued", "preparing")
        staging = _prepare_execution_staging(
            inputs.project.paths.staging / inputs.run_id,
            experiment_id=inputs.experiment.id,
            run_id=inputs.run_id,
            commit_sha=inputs.commit_sha,
            command=inputs.config.command,
            started_at=started_at,
        )
        provider = TorcProvider(
            config=inputs.config,
            request=TorcWorkflowRequest(
                run_id=inputs.run_id,
                experiment_id=inputs.experiment.id,
                commit_sha=inputs.commit_sha,
                mode=profile.mode,
                target_shell=profile.target_shell,
                torc_profile=profile.torc_profile,
            ),
            profile_name=profile_name,
            profile=profile,
            worktree=inputs.worktree,
            staging=staging,
            gateway=selected_gateway,
        )
        try:
            prepared = provider.prepare()
        except Exception as error:
            message = _redact_text(str(error), inputs.config.archive.log_redactions)
            _write_torc_metadata(
                staging,
                state="failed",
                profile_name=profile_name,
                reference=None,
                error=message,
            )
            _transition(database, inputs.run_id, "preparing", "failed", finished_at=_utc_now())
            raise TorcRunError(f"TORC preparation failed: {message}") from error
        intent = database.append_intent(
            kind="run.launch",
            entity_type="run",
            entity_id=inputs.run_id,
            payload={
                "compute_profile": profile_name,
                "executor": "torc",
                "mode": profile.mode,
                "worktree": inputs.experiment.worktree,
            },
        )
        try:
            launched = provider.launch(prepared)
            if launched.reference is None:
                raise RuntimeError("TORC provider returned no executor reference")
        except Exception as error:
            message = _redact_text(str(error), inputs.config.archive.log_redactions)
            reference = provider.reference
            if reference is not None:
                _record_reference(
                    database,
                    inputs.run_id,
                    reference,
                    _utc_now(),
                    process_id=None,
                )
            database.append_observation(
                intent.id,
                payload={
                    "error": message,
                    "outcome": "failed",
                    "workflow_id": reference.workflow_id if reference else None,
                },
            )
            _write_torc_metadata(
                staging,
                state="failed",
                profile_name=profile_name,
                reference=reference,
                error=message,
            )
            _transition(database, inputs.run_id, "preparing", "failed", finished_at=_utc_now())
            raise TorcRunError(f"TORC launch failed: {message}") from error
        reference = launched.reference
        observed_at = _utc_now()
        _record_reference(
            database,
            inputs.run_id,
            reference,
            observed_at,
            process_id=launched.process_id,
        )
        database.append_observation(
            intent.id,
            payload={
                "job_ids": list(reference.job_ids),
                "outcome": "started",
                "workflow_id": reference.workflow_id,
            },
        )
        _write_torc_metadata(
            staging,
            state="running",
            profile_name=profile_name,
            reference=reference,
        )
        _transition(database, inputs.run_id, "preparing", "running")
    return ManagedRunRecord(
        run_id=inputs.run_id,
        experiment_id=inputs.experiment.id,
        commit_sha=inputs.commit_sha,
        operational_state="running",
        started_at=started_at,
        last_observed_at=observed_at,
        reference=reference,
    )


def inspect_torc_run(
    start: Path,
    run_id: str,
    *,
    machine_config_file: Path,
    gateway: TorcGateway | None = None,
) -> ManagedRunRecord | RunManifest:
    project = discover_project(start)
    try:
        return load_archive(project.root, run_id)
    except ArchiveNotFoundError:
        pass
    with open_database(project.paths.database) as database:
        row = _managed_run_row(database, run_id)
        if row["workflow_id"] is None:
            return ManagedRunRecord(
                run_id=run_id,
                experiment_id=row["experiment_id"],
                commit_sha=row["commit_sha"],
                operational_state=row["operational_state"],
                started_at=row["started_at"],
                last_observed_at=row["last_observed_at"],
            )
        reference = _reference_from_row(row)
        experiment = load_experiment(project.root, row["experiment_id"])
        worktree_record = load_worktree(project.root, experiment.id)
        worktree = Path(worktree_record.path)
        config = load_project_config(worktree / "waterology.toml")
        profile = load_machine_config(machine_config_file).profile(reference.compute_profile)
        selected_gateway = gateway or TorcCliGateway(reference.api_url)
        provider = TorcProvider(
            config=config,
            request=TorcWorkflowRequest(
                run_id=run_id,
                experiment_id=experiment.id,
                commit_sha=row["commit_sha"],
                mode=reference.execution_mode,
                target_shell=profile.target_shell,
                torc_profile=profile.torc_profile,
            ),
            profile_name=reference.compute_profile,
            profile=profile,
            worktree=worktree,
            staging=project.paths.staging / run_id,
            gateway=selected_gateway,
        )
        provider.reference = reference
        prior_state = (
            row["prior_operational_state"]
            if row["operational_state"] == "unknown"
            else row["operational_state"]
        )
        try:
            inspection = provider.inspect(
                prepared=_prepared_from_row(project.paths.staging / run_id, worktree, row),
                prior_known_state=prior_state,
            )
        except Exception as error:
            message = _redact_text(str(error), config.archive.log_redactions)
            raise TorcRunError(f"TORC inspection failed: {message}") from error
        observed_at = _utc_now()
        owns_observation = _record_inspection(
            database,
            run_id,
            row["operational_state"],
            inspection,
            observed_at,
            expected_last_observed_at=row["last_observed_at"],
        )
        if not owns_observation:
            refreshed = _managed_run_row(database, run_id)
            return ManagedRunRecord(
                run_id=run_id,
                experiment_id=experiment.id,
                commit_sha=refreshed["commit_sha"],
                operational_state=refreshed["operational_state"],
                started_at=refreshed["started_at"],
                last_observed_at=refreshed["last_observed_at"],
                reference=reference,
            )
        if inspection.terminal_state is None:
            return ManagedRunRecord(
                run_id=run_id,
                experiment_id=experiment.id,
                commit_sha=row["commit_sha"],
                operational_state=inspection.state,
                started_at=row["started_at"],
                last_observed_at=observed_at,
                reference=reference,
            )

        collection_lock = _acquire_collection_lock(
            project.paths.staging / ".locks" / f"{run_id}.lock"
        )
        if collection_lock is None:
            return ManagedRunRecord(
                run_id=run_id,
                experiment_id=experiment.id,
                commit_sha=row["commit_sha"],
                operational_state="collecting",
                started_at=row["started_at"],
                last_observed_at=observed_at,
                reference=reference,
            )
        try:
            try:
                collection = provider.collect_observed(
                    inspection.terminal_state,
                    exit_code=inspection.exit_code,
                )
            except Exception as error:
                message = _redact_text(str(error), config.archive.log_redactions)
                raise TorcRunError(f"TORC collection failed: {message}") from error
            scientific_metrics = _extract_metrics(
                config,
                worktree,
                required=inspection.terminal_state == "completed",
            )
            metrics = {"torc_resources": collection.metrics, **scientific_metrics}
            _write_torc_metadata(
                project.paths.staging / run_id,
                state=collection.terminal_state,
                profile_name=reference.compute_profile,
                reference=reference,
            )
            archive = build_run_archive(
                project.root,
                experiment_id=experiment.id,
                run_id=run_id,
                commit_sha=row["commit_sha"],
                command=config.command,
                started_at=row["started_at"],
                finished_at=observed_at,
                terminal_state=collection.terminal_state,
                exit_code=collection.exit_code,
                stdout=collection.stdout,
                stderr=collection.stderr,
                metrics=metrics,
                process_id=row["process_id"],
                executor_reference=reference,
                compute_profile=reference.compute_profile,
                config=config,
            )
            _transition(
                database,
                run_id,
                "collecting",
                collection.terminal_state,
                exit_code=collection.exit_code,
                finished_at=observed_at,
                archive_path=archive.relative_to(project.root).as_posix(),
            )
        finally:
            _release_collection_lock(collection_lock)
    return load_archive(project.root, run_id)


def cancel_torc_run(
    start: Path,
    run_id: str,
    *,
    machine_config_file: Path,
    gateway: TorcGateway | None = None,
) -> ManagedRunRecord | RunManifest:
    project = discover_project(start)
    try:
        return load_archive(project.root, run_id)
    except ArchiveNotFoundError:
        pass
    with open_database(project.paths.database) as database:
        row = _managed_run_row(database, run_id)
        reference = _reference_from_row(row)
        worktree = Path(load_worktree(project.root, row["experiment_id"]).path)
        config = load_project_config(worktree / "waterology.toml")
        selected_gateway = gateway or TorcCliGateway(reference.api_url)
        cancel_lock = _acquire_collection_lock(
            project.paths.staging / ".locks" / f"{run_id}.cancel.lock",
            blocking=True,
        )
        if cancel_lock is None:
            raise TorcRunError("Unable to acquire the TORC cancellation lock")
        cancellation_was_requested = False
        try:
            cancellation_was_requested = cancellation_was_requested or any(
                event.kind == "run.cancel"
                and event.entity_id == run_id
                and event.phase == "observation"
                and event.payload.get("outcome") == "requested"
                for event in database.list_events()
            )
            if not cancellation_was_requested and row["operational_state"] not in {
                "completed",
                "failed",
                "cancelled",
                "lost",
            }:
                intent = database.append_intent(
                    kind="run.cancel",
                    entity_type="run",
                    entity_id=run_id,
                    payload={"workflow_id": reference.workflow_id},
                )
                try:
                    selected_gateway.cancel(reference.workflow_id, cwd=worktree)
                except Exception as error:
                    message = _redact_text(str(error), config.archive.log_redactions)
                    database.append_observation(
                        intent.id,
                        payload={"error": message, "outcome": "failed"},
                    )
                    raise TorcRunError(f"TORC cancellation failed: {message}") from error
                database.append_observation(intent.id, payload={"outcome": "requested"})
        finally:
            if cancel_lock is not None:
                _release_collection_lock(cancel_lock)
    return ManagedRunRecord(
        run_id=run_id,
        experiment_id=row["experiment_id"],
        commit_sha=row["commit_sha"],
        operational_state=row["operational_state"],
        started_at=row["started_at"],
        last_observed_at=row["last_observed_at"],
        reference=reference,
    )


def _record_reference(
    database: Database,
    run_id: str,
    reference: ExecutorReference,
    observed_at: str,
    *,
    process_id: int | None,
) -> None:
    connection = database.connection
    with connection:
        connection.execute(
            """
            UPDATE runs
            SET workflow_id = ?, job_ids_json = ?, api_url = ?, execution_mode = ?,
                torc_version = ?, workflow_spec_sha256 = ?, last_observed_at = ?,
                process_id = ?
            WHERE id = ?
            """,
            (
                reference.workflow_id,
                json.dumps(reference.job_ids),
                reference.api_url,
                reference.execution_mode,
                reference.torc_version,
                reference.workflow_spec_sha256,
                observed_at,
                process_id,
                run_id,
            ),
        )


def _write_torc_metadata(
    staging: Path,
    *,
    state: str,
    profile_name: str,
    reference: ExecutorReference | None,
    error: str | None = None,
) -> None:
    payload = {
        "error": error,
        "executor_reference": reference.model_dump(mode="json") if reference else None,
        "profile": profile_name,
        "schema_version": 1,
        "state": state,
        "updated_at": _utc_now(),
    }
    destination = staging / "torc.json"
    temporary = staging / ".torc.json.tmp"
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _redact_text(value: str, patterns: tuple[str, ...]) -> str:
    redacted = value
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def _managed_run_row(database: Database, run_id: str) -> sqlite3.Row:
    row = database.connection.execute(
        "SELECT * FROM runs WHERE id = ? AND executor = 'torc'",
        (run_id,),
    ).fetchone()
    if row is None:
        raise WaterologyError(f"Managed TORC run does not exist: {run_id}")
    return row


def _reference_from_row(row: sqlite3.Row) -> ExecutorReference:
    return ExecutorReference(
        compute_profile=row["compute_profile"],
        api_url=row["api_url"],
        execution_mode=row["execution_mode"],
        workflow_id=row["workflow_id"],
        job_ids=tuple(json.loads(row["job_ids_json"])),
        torc_version=row["torc_version"],
        workflow_spec_sha256=row["workflow_spec_sha256"],
    )


def _prepared_from_row(staging: Path, worktree: Path, row: sqlite3.Row) -> PreparedRun:
    return PreparedRun(
        run_id=row["id"],
        experiment_id=row["experiment_id"],
        commit_sha=row["commit_sha"],
        worktree=worktree,
        staging=staging,
    )


def _record_inspection(
    database: Database,
    run_id: str,
    current_state: str,
    inspection: ProviderInspection,
    observed_at: str,
    *,
    expected_last_observed_at: str | None,
) -> bool:
    recorded_state = "collecting" if inspection.terminal_state is not None else inspection.state
    prior = inspection.prior_known_state if inspection.state == "unknown" else None
    intent = database.append_intent(
        kind="run.reconcile",
        entity_type="run",
        entity_id=run_id,
        payload={"from": current_state},
    )
    with database.connection:
        cursor = database.connection.execute(
            """
            UPDATE runs
            SET operational_state = ?, prior_operational_state = ?, last_observed_at = ?
            WHERE id = ? AND last_observed_at IS ?
            """,
            (recorded_state, prior, observed_at, run_id, expected_last_observed_at),
        )
    database.append_observation(
        intent.id,
        payload={
            "outcome": "observed" if cursor.rowcount == 1 else "superseded",
            "state": recorded_state,
        },
    )
    return cursor.rowcount == 1


def _acquire_collection_lock(path: Path, *, blocking: bool = False) -> BinaryIO | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            if stream.seek(0, os.SEEK_END) == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
            msvcrt.locking(stream.fileno(), mode, 1)
        else:
            import fcntl

            mode = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
            fcntl.flock(stream.fileno(), mode)
    except OSError:
        stream.close()
        return None
    return stream


def _release_collection_lock(stream: BinaryIO) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    finally:
        stream.close()
