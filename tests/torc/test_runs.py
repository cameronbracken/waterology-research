import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from waterology.core.archive import load_archive
from waterology.core.config import ArchiveConfig, ProjectConfig, project_config_toml
from waterology.core.database import open_database
from waterology.core.execution import RunPreparationError
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.torc.gateway import (
    TorcCommandError,
    TorcLaunchRecord,
    TorcPartialLaunchError,
    TorcUnavailableError,
    TorcWorkflowNotFoundError,
    TorcWorkflowObservation,
)
from waterology.torc.runs import (
    RemoteProfileConfirmationError,
    TorcRunError,
    _acquire_collection_lock,
    _release_collection_lock,
    cancel_torc_run,
    inspect_torc_run,
    start_torc_run,
)


class FakeGateway:
    def validate(self, workflow: Path, *, cwd: Path) -> dict[str, object]:
        return {"valid": True}

    def version(self, *, cwd: Path) -> str:
        return "torc 0.39.0"

    def launch(self, workflow: Path, **kwargs: object) -> TorcLaunchRecord:
        return TorcLaunchRecord("42", ("9",), process_id=271)

    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        return TorcWorkflowObservation(workflow_id, "running", (), {})

    def cancel(self, workflow_id: str, *, cwd: Path) -> dict[str, object]:
        return {"workflow_id": workflow_id, "status": "cancel_requested"}

    def collect_logs(self, workflow_id: str, destination: Path, *, cwd: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)

    def results(self, workflow_id: str, *, cwd: Path) -> object:
        return {"items": [{"job_id": "9", "return_code": 0}]}


class CompletedGateway(FakeGateway):
    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        return TorcWorkflowObservation(workflow_id, "completed", ({"exit_code": 0},), {})


class UnavailableGateway(FakeGateway):
    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        raise TorcUnavailableError("offline")


class LostGateway(FakeGateway):
    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        raise TorcWorkflowNotFoundError("absent")

    def results(self, workflow_id: str, *, cwd: Path) -> object:
        raise AssertionError("lost workflows must not request TORC results")


class CountingGateway(FakeGateway):
    def __init__(self) -> None:
        self.cancel_calls = 0
        self.inspect_calls = 0

    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        self.inspect_calls += 1
        return super().inspect(workflow_id, cwd=cwd)

    def cancel(self, workflow_id: str, *, cwd: Path) -> dict[str, object]:
        self.cancel_calls += 1
        return super().cancel(workflow_id, cwd=cwd)


class LaunchFailureGateway(FakeGateway):
    def launch(self, workflow: Path, **kwargs: object) -> TorcLaunchRecord:
        raise TorcCommandError("submission rejected")


class ValidationFailureGateway(FakeGateway):
    def validate(self, workflow: Path, *, cwd: Path) -> dict[str, object]:
        raise TorcCommandError("token=secret-value")


class SecretLaunchFailureGateway(FakeGateway):
    def launch(self, workflow: Path, **kwargs: object) -> TorcLaunchRecord:
        raise TorcCommandError("token=secret-value")


class InspectionFailureGateway(FakeGateway):
    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        raise TorcCommandError("token=secret-value")


class CollectionFailureGateway(CompletedGateway):
    def results(self, workflow_id: str, *, cwd: Path) -> object:
        raise TorcCommandError("token=secret-value")


class PartialLaunchFailureGateway(FakeGateway):
    def launch(self, workflow: Path, **kwargs: object) -> TorcLaunchRecord:
        raise TorcPartialLaunchError("runner rejected", TorcLaunchRecord("42", ("9",)))


class CancellationFailureGateway(FakeGateway):
    def cancel(self, workflow_id: str, *, cwd: Path) -> dict[str, object]:
        raise TorcCommandError("token=secret-value")


class BlockingCancellationGateway(FakeGateway):
    def __init__(self) -> None:
        self.calls = 0
        self.entered = threading.Event()
        self.release = threading.Event()

    def cancel(self, workflow_id: str, *, cwd: Path) -> dict[str, object]:
        self.calls += 1
        self.entered.set()
        assert self.release.wait(timeout=5)
        return {"status": "success"}


class BlockingFirstFailureGateway(BlockingCancellationGateway):
    def cancel(self, workflow_id: str, *, cwd: Path) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            self.entered.set()
            assert self.release.wait(timeout=5)
            raise TorcCommandError("first cancellation failed")
        return {"status": "success"}


def test_collection_lock_is_exclusive_and_released(tmp_path: Path) -> None:
    path = tmp_path / "locks" / "run-one.lock"
    first = _acquire_collection_lock(path)

    assert first is not None
    assert _acquire_collection_lock(path) is None

    _release_collection_lock(first)
    second = _acquire_collection_lock(path)
    assert second is not None
    _release_collection_lock(second)


def make_variant(path: Path) -> tuple[Path, str]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    config = ProjectConfig(name="managed", command=("python", "model.py"))
    (path / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    (path / "model.py").write_text("print('base')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "base"], check=True)
    experiment = create_experiment(path, hypothesis="Managed run", experiment_id="exp-torc")
    worktree = path / experiment.worktree
    (worktree / "model.py").write_text("print('variant')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(worktree), "add", "model.py"], check=True)
    subprocess.run(["git", "-C", str(worktree), "commit", "--quiet", "-m", "variant"], check=True)
    return path, experiment.id


def test_start_torc_run_persists_launch_reference(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        """\
[profiles.local]
provider = "torc"
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"
""",
        encoding="utf-8",
    )

    run = start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-managed",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    assert run.operational_state == "running"
    assert run.reference.workflow_id == "42"
    assert (root / ".waterology/staging/run-managed/torc-workflow.yaml").is_file()
    with open_database(root / ".waterology/state.sqlite") as database:
        row = database.connection.execute(
            "SELECT executor, compute_profile, workflow_id, job_ids_json, process_id "
            "FROM runs WHERE id = ?",
            (run.run_id,),
        ).fetchone()
    assert tuple(row) == ("torc", "local", "42", '["9"]', 271)


def test_remote_profile_requires_confirmation_then_records_trust(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        """\
[profiles.remote]
provider = "torc"
mode = "remote"
api_url = "http://localhost:8080/torc-service/v1"
ssh_alias = "worker-a"
""",
        encoding="utf-8",
    )

    with pytest.raises(RemoteProfileConfirmationError, match="first use"):
        start_torc_run(
            root,
            experiment_id,
            profile_name="remote",
            machine_config_file=machine,
            run_id="run-untrusted",
            gateway=FakeGateway(),  # type: ignore[arg-type]
        )

    run = start_torc_run(
        root,
        experiment_id,
        profile_name="remote",
        machine_config_file=machine,
        run_id="run-trusted",
        confirm_remote=True,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    assert run.reference.execution_mode == "remote"
    assert 'trusted_profiles = ["remote"]' in machine.read_text(encoding="utf-8")


def test_managed_run_keeps_direct_preparation_rules(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    worktree = root / ".waterology/worktrees" / experiment_id
    (worktree / "model.py").write_text("dirty\n", encoding="utf-8")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )

    with pytest.raises(RunPreparationError, match="must be clean"):
        start_torc_run(
            root,
            experiment_id,
            profile_name="local",
            machine_config_file=machine,
            gateway=FakeGateway(),  # type: ignore[arg-type]
        )


def test_inspect_collects_terminal_torc_run_into_sealed_archive(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-complete",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    result = inspect_torc_run(
        root,
        "run-complete",
        machine_config_file=machine,
        gateway=CompletedGateway(),  # type: ignore[arg-type]
    )

    manifest = load_archive(root, "run-complete")
    assert result == manifest
    assert manifest.terminal_state == "completed"
    assert manifest.executor_reference is not None
    assert (root / ".waterology/runs/run-complete/torc-workflow.yaml").is_file()


def test_inspect_marks_unreachable_torc_unknown_without_failing(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-offline",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    first = inspect_torc_run(
        root,
        "run-offline",
        machine_config_file=machine,
        gateway=UnavailableGateway(),  # type: ignore[arg-type]
    )
    second = inspect_torc_run(
        root,
        "run-offline",
        machine_config_file=machine,
        gateway=UnavailableGateway(),  # type: ignore[arg-type]
    )

    assert first.operational_state == second.operational_state == "unknown"
    with open_database(root / ".waterology/state.sqlite") as database:
        row = database.connection.execute(
            "SELECT operational_state, prior_operational_state FROM runs WHERE id = 'run-offline'"
        ).fetchone()
    assert tuple(row) == ("unknown", "running")


def test_cancel_records_intent_without_inventing_terminal_state(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-cancel",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    gateway = CountingGateway()
    result = cancel_torc_run(
        root,
        "run-cancel",
        machine_config_file=machine,
        gateway=gateway,  # type: ignore[arg-type]
    )
    repeated = cancel_torc_run(
        root,
        "run-cancel",
        machine_config_file=machine,
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert result.operational_state == repeated.operational_state == "running"
    assert gateway.cancel_calls == 1
    with open_database(root / ".waterology/state.sqlite") as database:
        events = [
            event
            for event in database.list_events()
            if event.kind == "run.cancel" and event.entity_id == "run-cancel"
        ]
    assert [event.phase for event in events] == ["intent", "observation"]


def test_cancel_failure_is_redacted_audited_and_retryable(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    worktree = root / ".waterology/worktrees" / experiment_id
    config = ProjectConfig(
        name="managed",
        command=("python", "model.py"),
        archive=ArchiveConfig(log_redactions=(r"token=[^\s]+",)),
    )
    (worktree / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    subprocess.run(["git", "-C", str(worktree), "add", "waterology.toml"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "redactions"], check=True
    )
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-cancel-retry",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    with pytest.raises(TorcRunError) as captured:
        cancel_torc_run(
            root,
            "run-cancel-retry",
            machine_config_file=machine,
            gateway=CancellationFailureGateway(),  # type: ignore[arg-type]
        )

    assert "secret-value" not in str(captured.value)
    retry = CountingGateway()
    cancel_torc_run(
        root,
        "run-cancel-retry",
        machine_config_file=machine,
        gateway=retry,  # type: ignore[arg-type]
    )
    assert retry.cancel_calls == 1
    with open_database(root / ".waterology/state.sqlite") as database:
        observations = [
            event.payload
            for event in database.list_events()
            if event.kind == "run.cancel" and event.phase == "observation"
        ]
    assert observations == [
        {"error": "[REDACTED]", "outcome": "failed"},
        {"outcome": "requested"},
    ]


def test_concurrent_cancel_issues_one_external_request(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-cancel-concurrent",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )
    gateway = BlockingCancellationGateway()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            cancel_torc_run,
            root,
            "run-cancel-concurrent",
            machine_config_file=machine,
            gateway=gateway,  # type: ignore[arg-type]
        )
        assert gateway.entered.wait(timeout=5)
        second = executor.submit(
            cancel_torc_run,
            root,
            "run-cancel-concurrent",
            machine_config_file=machine,
            gateway=gateway,  # type: ignore[arg-type]
        )
        gateway.release.set()
        first.result(timeout=5)
        second.result(timeout=5)

    assert gateway.calls == 1


def test_concurrent_cancel_waiter_retries_after_owner_failure(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-cancel-owner-fails",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )
    gateway = BlockingFirstFailureGateway()

    with ThreadPoolExecutor(max_workers=2) as executor:
        owner = executor.submit(
            cancel_torc_run,
            root,
            "run-cancel-owner-fails",
            machine_config_file=machine,
            gateway=gateway,  # type: ignore[arg-type]
        )
        assert gateway.entered.wait(timeout=5)
        waiter = executor.submit(
            cancel_torc_run,
            root,
            "run-cancel-owner-fails",
            machine_config_file=machine,
            gateway=gateway,  # type: ignore[arg-type]
        )
        gateway.release.set()
        with pytest.raises(TorcRunError, match="first cancellation failed"):
            owner.result(timeout=5)
        result = waiter.result(timeout=5)

    assert result.operational_state == "running"
    assert gateway.calls == 2
    with open_database(root / ".waterology/state.sqlite") as database:
        outcomes = [
            event.payload["outcome"]
            for event in database.list_events()
            if event.kind == "run.cancel" and event.phase == "observation"
        ]
    assert outcomes == ["failed", "requested"]


def test_confirmed_lost_run_seals_without_requesting_absent_results(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-lost",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    result = inspect_torc_run(
        root,
        "run-lost",
        machine_config_file=machine,
        gateway=LostGateway(),  # type: ignore[arg-type]
    )

    assert result.terminal_state == "lost"


def test_inspect_returns_existing_archive_without_recontacting_torc(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-sealed",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )
    inspect_torc_run(
        root,
        "run-sealed",
        machine_config_file=machine,
        gateway=CompletedGateway(),  # type: ignore[arg-type]
    )
    gateway = CountingGateway()

    result = inspect_torc_run(
        root,
        "run-sealed",
        machine_config_file=machine,
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert result.terminal_state == "completed"
    assert gateway.inspect_calls == 0


def test_launch_failure_preserves_queryable_staging_record(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )

    with pytest.raises(TorcRunError, match="submission rejected"):
        start_torc_run(
            root,
            experiment_id,
            profile_name="local",
            machine_config_file=machine,
            run_id="run-rejected",
            gateway=LaunchFailureGateway(),  # type: ignore[arg-type]
        )

    status = inspect_torc_run(
        root,
        "run-rejected",
        machine_config_file=machine,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )
    assert status.operational_state == "failed"
    assert status.reference is None
    staging = root / ".waterology/staging/run-rejected"
    assert (staging / "torc.json").is_file()
    assert (staging / "torc-workflow.yaml").is_file()


@pytest.mark.parametrize(
    ("gateway", "phase"),
    [
        (ValidationFailureGateway(), "preparation"),
        (SecretLaunchFailureGateway(), "launch"),
    ],
)
def test_start_errors_are_redacted(tmp_path: Path, gateway: FakeGateway, phase: str) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    _commit_log_redaction(root, experiment_id)
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )

    with pytest.raises(TorcRunError, match=phase) as captured:
        start_torc_run(
            root,
            experiment_id,
            profile_name="local",
            machine_config_file=machine,
            run_id=f"run-redacted-{phase}",
            gateway=gateway,  # type: ignore[arg-type]
        )

    assert "secret-value" not in str(captured.value)


def test_inspection_and_collection_errors_are_redacted(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    _commit_log_redaction(root, experiment_id)
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    start_torc_run(
        root,
        experiment_id,
        profile_name="local",
        machine_config_file=machine,
        run_id="run-redacted-inspect",
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    with pytest.raises(TorcRunError, match="inspection") as inspection:
        inspect_torc_run(
            root,
            "run-redacted-inspect",
            machine_config_file=machine,
            gateway=InspectionFailureGateway(),  # type: ignore[arg-type]
        )
    with pytest.raises(TorcRunError, match="collection") as collection:
        inspect_torc_run(
            root,
            "run-redacted-inspect",
            machine_config_file=machine,
            gateway=CollectionFailureGateway(),  # type: ignore[arg-type]
        )

    assert "secret-value" not in str(inspection.value)
    assert "secret-value" not in str(collection.value)


def test_partial_launch_failure_preserves_created_workflow_reference(tmp_path: Path) -> None:
    root, experiment_id = make_variant(tmp_path / "study")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )

    with pytest.raises(TorcRunError, match="runner rejected"):
        start_torc_run(
            root,
            experiment_id,
            profile_name="local",
            machine_config_file=machine,
            run_id="run-partial",
            gateway=PartialLaunchFailureGateway(),  # type: ignore[arg-type]
        )

    status = inspect_torc_run(
        root,
        "run-partial",
        machine_config_file=machine,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )
    assert status.reference is not None
    assert status.reference.workflow_id == "42"


def _commit_log_redaction(root: Path, experiment_id: str) -> None:
    worktree = root / ".waterology/worktrees" / experiment_id
    config = ProjectConfig(
        name="managed",
        command=("python", "model.py"),
        archive=ArchiveConfig(log_redactions=(r"token=[^\s]+",)),
    )
    (worktree / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    subprocess.run(["git", "-C", str(worktree), "add", "waterology.toml"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "redactions"], check=True
    )
