import io
import sqlite3
import tarfile
from pathlib import Path

import pytest

from waterology.core.config import ProjectConfig
from waterology.core.profiles import ComputeProfile
from waterology.core.providers import PreparedRun
from waterology.torc.gateway import (
    TorcLaunchRecord,
    TorcWorkflowObservation,
)
from waterology.torc.provider import (
    TorcProvider,
    _extract_remote_log_archives,
    _read_matching_logs,
    _read_resource_metrics,
)
from waterology.torc.workflow import TorcWorkflowRequest


class FakeGateway:
    def __init__(self) -> None:
        self.validated: Path | None = None
        self.launched: tuple[str, str | None, int | None] | None = None

    def validate(self, workflow: Path, *, cwd: Path) -> dict[str, object]:
        self.validated = workflow
        return {"valid": True}

    def launch(
        self,
        workflow: Path,
        *,
        mode: str,
        ssh_alias: str | None,
        torc_profile: str | None,
        slurm_account: str | None,
        access_group_id: int | None,
        output_dir: Path,
        cwd: Path,
    ) -> TorcLaunchRecord:
        self.launched = (mode, ssh_alias, access_group_id)
        return TorcLaunchRecord("42", ("9",))

    def version(self, *, cwd: Path) -> str:
        return "torc 0.39.0"

    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        return TorcWorkflowObservation(workflow_id, "running", (), {})

    def cancel(self, workflow_id: str, *, cwd: Path) -> dict[str, object]:
        return {"workflow": {"id": workflow_id, "state": "canceled"}}

    def collect_logs(self, workflow_id: str, destination: Path, *, cwd: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)

    def results(self, workflow_id: str, *, cwd: Path) -> object:
        return {"items": []}


def test_provider_prepares_and_launches_remote_workflow(tmp_path: Path) -> None:
    gateway = FakeGateway()
    worktree = tmp_path / "worktree"
    staging = tmp_path / "staging"
    worktree.mkdir()
    staging.mkdir()
    provider = TorcProvider(
        config=ProjectConfig(name="study", command=("python", "run.py")),
        request=TorcWorkflowRequest(
            run_id="run-one",
            experiment_id="exp-one",
            commit_sha="a" * 40,
            mode="remote",
        ),
        profile_name="remote",
        profile=ComputeProfile(
            mode="remote",
            api_url="http://control.example:8080",
            ssh_alias="worker-a",
            access_group_id=2,
        ),
        worktree=worktree,
        staging=staging,
        gateway=gateway,  # type: ignore[arg-type]
    )

    prepared = provider.prepare()
    launched = provider.launch(prepared)

    assert gateway.validated == staging / "torc-workflow.yaml"
    assert gateway.launched == ("remote", "worker-a", 2)
    assert launched.reference is not None
    assert launched.reference.workflow_id == "42"
    assert launched.reference.job_ids == ("9",)
    assert launched.reference.workflow_spec_sha256 is not None
    assert launched.state == "running"


def test_provider_inspection_maps_torc_state(tmp_path: Path) -> None:
    gateway = FakeGateway()
    worktree = tmp_path / "worktree"
    staging = tmp_path / "staging"
    worktree.mkdir()
    staging.mkdir()
    provider = TorcProvider(
        config=ProjectConfig(name="study", command=("python", "run.py")),
        request=TorcWorkflowRequest(
            run_id="run-one",
            experiment_id="exp-one",
            commit_sha="a" * 40,
            mode="local",
        ),
        profile_name="local",
        profile=ComputeProfile(mode="local", api_url="http://localhost:8080"),
        worktree=worktree,
        staging=staging,
        gateway=gateway,  # type: ignore[arg-type]
    )
    prepared = PreparedRun("run-one", "exp-one", "a" * 40, worktree, staging)
    provider.reference = provider.launch(provider.prepare()).reference

    inspection = provider.inspect(prepared)

    assert inspection.state == "running"


def test_remote_log_collection_extracts_regular_files(tmp_path: Path) -> None:
    archive = tmp_path / "torc_logs_42_worker.tar.gz"
    payload = b"managed stdout\n"
    with tarfile.open(archive, "w:gz") as target:
        info = tarfile.TarInfo("job_stdio/job_wf42_j7.o")
        info.size = len(payload)
        target.addfile(info, io.BytesIO(payload))

    _extract_remote_log_archives(tmp_path)
    _extract_remote_log_archives(tmp_path)

    assert (tmp_path / "torc_logs_42_worker/job_stdio/job_wf42_j7.o").read_bytes() == payload


def test_log_collection_matches_official_local_remote_and_slurm_names(tmp_path: Path) -> None:
    log_dir = tmp_path / "job_stdio"
    log_dir.mkdir()
    (log_dir / "job_wf42_j7.o").write_text("local out\n", encoding="utf-8")
    (log_dir / "job_wf42_j7.e").write_text("local err\n", encoding="utf-8")
    (log_dir / "slurm_output_wf42_123.o").write_text("slurm out\n", encoding="utf-8")
    (log_dir / "slurm_output_wf42_123.e").write_text("slurm err\n", encoding="utf-8")

    assert _read_matching_logs(tmp_path, stream="stdout") == "local out\nslurm out\n"
    assert _read_matching_logs(tmp_path, stream="stderr") == "local err\nslurm err\n"


def test_resource_collection_normalizes_multiple_torc_databases(tmp_path: Path) -> None:
    first = tmp_path / "resource_utilization" / "resource_metrics_node1_wf42_1.db"
    second = tmp_path / "remote" / "resource_utilization" / "resource_metrics_node2_wf42_1.db"
    _write_resource_database(first, job_id=7, cpu=(10.0, 30.0), memory=(100, 300))
    _write_resource_database(second, job_id=8, cpu=(20.0, 40.0), memory=(200, 400))

    metrics = _read_resource_metrics(tmp_path)

    assert [database["path"] for database in metrics["databases"]] == [
        "remote/resource_utilization/resource_metrics_node2_wf42_1.db",
        "resource_utilization/resource_metrics_node1_wf42_1.db",
    ]
    first_job = metrics["databases"][1]["jobs"][0]
    assert first_job == {
        "job_id": 7,
        "job_name": "job-7",
        "sample_count": 2,
        "peak_cpu_percent": 30.0,
        "avg_cpu_percent": 20.0,
        "peak_memory_bytes": 300,
        "avg_memory_bytes": 200,
        "peak_process_count": 2,
    }
    assert metrics["databases"][0]["system"]["sample_count"] == 2


def test_remote_log_collection_rejects_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "torc_logs_42_worker.tar.gz"
    payload = b"escape"
    with tarfile.open(archive, "w:gz") as target:
        info = tarfile.TarInfo("../outside.log")
        info.size = len(payload)
        target.addfile(info, io.BytesIO(payload))

    with pytest.raises(RuntimeError, match="unsafe path"):
        _extract_remote_log_archives(tmp_path)

    assert not (tmp_path.parent / "outside.log").exists()


def test_provider_rejects_preexisting_output_symlink(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    staging = tmp_path / "staging"
    output_root = tmp_path / "outputs"
    outside = tmp_path / "outside"
    for path in (worktree, staging, output_root, outside):
        path.mkdir()
    (output_root / "run-one").symlink_to(outside, target_is_directory=True)
    provider = TorcProvider(
        config=ProjectConfig(name="study", command=("python", "run.py")),
        request=TorcWorkflowRequest(
            run_id="run-one",
            experiment_id="exp-one",
            commit_sha="a" * 40,
            mode="local",
        ),
        profile_name="local",
        profile=ComputeProfile(
            mode="local",
            api_url="http://localhost:8080",
            local_output_root=str(output_root),
        ),
        worktree=worktree,
        staging=staging,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="must not be a symlink"):
        provider.launch(provider.prepare())

    assert tuple(outside.iterdir()) == ()


def _write_resource_database(
    path: Path,
    *,
    job_id: int,
    cpu: tuple[float, float],
    memory: tuple[int, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    with connection:
        connection.executescript(
            """
            CREATE TABLE job_resource_samples (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                cpu_percent REAL NOT NULL,
                memory_bytes INTEGER NOT NULL,
                num_processes INTEGER NOT NULL
            );
            CREATE TABLE job_metadata (job_id INTEGER PRIMARY KEY, job_name TEXT NOT NULL);
            CREATE TABLE system_resource_samples (
                id INTEGER PRIMARY KEY,
                timestamp INTEGER NOT NULL,
                cpu_percent REAL NOT NULL,
                memory_bytes INTEGER NOT NULL,
                total_memory_bytes INTEGER NOT NULL
            );
            CREATE TABLE system_resource_summary (
                id INTEGER PRIMARY KEY,
                sample_count INTEGER NOT NULL,
                peak_cpu_percent REAL NOT NULL,
                avg_cpu_percent REAL NOT NULL,
                peak_memory_bytes INTEGER NOT NULL,
                avg_memory_bytes INTEGER NOT NULL
            );
            """
        )
        connection.execute("INSERT INTO job_metadata VALUES (?, ?)", (job_id, f"job-{job_id}"))
        connection.executemany(
            "INSERT INTO job_resource_samples VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, job_id, 1.0, cpu[0], memory[0], 1),
                (2, job_id, 2.0, cpu[1], memory[1], 2),
            ],
        )
        connection.executemany(
            "INSERT INTO system_resource_samples VALUES (?, ?, ?, ?, ?)",
            [(1, 1, cpu[0], memory[0], 1000), (2, 2, cpu[1], memory[1], 1000)],
        )
    connection.close()
