import sqlite3
import tarfile
import tempfile
from pathlib import Path

from waterology.core.config import ProjectConfig
from waterology.core.profiles import ComputeProfile
from waterology.core.providers import (
    PreparedRun,
    ProviderCollection,
    ProviderInspection,
    ProviderLaunch,
)
from waterology.core.records import ExecutorReference
from waterology.torc.gateway import TorcGateway, TorcLaunchRecord, TorcPartialLaunchError
from waterology.torc.reconcile import reconcile_workflow
from waterology.torc.workflow import TorcWorkflowFile, TorcWorkflowRequest, write_workflow


class TorcProvider:
    def __init__(
        self,
        *,
        config: ProjectConfig,
        request: TorcWorkflowRequest,
        profile_name: str,
        profile: ComputeProfile,
        worktree: Path,
        staging: Path,
        gateway: TorcGateway,
    ) -> None:
        self.config = config
        self.request = request
        self.profile_name = profile_name
        self.profile = profile
        self.worktree = worktree
        self.staging = staging
        self.gateway = gateway
        self.workflow_file: TorcWorkflowFile | None = None
        self.reference: ExecutorReference | None = None

    def prepare(self) -> PreparedRun:
        self.workflow_file = write_workflow(
            self.staging / "torc-workflow.yaml",
            self.config,
            self.request,
            worktree=self.worktree,
        )
        self.gateway.validate(self.workflow_file.path, cwd=self.worktree)
        return PreparedRun(
            run_id=self.request.run_id,
            experiment_id=self.request.experiment_id,
            commit_sha=self.request.commit_sha,
            worktree=self.worktree,
            staging=self.staging,
        )

    def launch(self, prepared: PreparedRun) -> ProviderLaunch:
        if self.workflow_file is None:
            raise RuntimeError("TORC provider must be prepared before launch")
        version = self.gateway.version(cwd=prepared.worktree)
        try:
            launch = self.gateway.launch(
                self.workflow_file.path,
                mode=self.profile.mode,
                ssh_alias=self.profile.ssh_alias,
                torc_profile=self.profile.torc_profile,
                slurm_account=self.profile.slurm_account,
                access_group_id=self.profile.access_group_id,
                output_dir=self._output_directory(),
                cwd=prepared.worktree,
            )
        except TorcPartialLaunchError as error:
            self.reference = self._make_reference(error.record, version)
            raise
        self.reference = self._make_reference(launch, version)
        return ProviderLaunch(
            state="running",
            reference=self.reference,
            process_id=launch.process_id,
        )

    def _make_reference(self, launch: TorcLaunchRecord, version: str) -> ExecutorReference:
        if self.workflow_file is None:
            raise RuntimeError("TORC provider must be prepared before launch")
        self.reference = ExecutorReference(
            compute_profile=self.profile_name,
            api_url=self.profile.api_url,
            execution_mode=self.profile.mode,
            workflow_id=launch.workflow_id,
            job_ids=launch.job_ids,
            torc_version=version,
            workflow_spec_sha256=self.workflow_file.sha256,
        )
        return self.reference

    def inspect(
        self,
        prepared: PreparedRun,
        *,
        prior_known_state: str = "running",
    ) -> ProviderInspection:
        reference = self._require_reference()
        return reconcile_workflow(
            self.gateway,
            reference.workflow_id,
            cwd=prepared.worktree,
            prior_known_state=prior_known_state,  # type: ignore[arg-type]
        )

    def cancel(self, prepared: PreparedRun) -> ProviderInspection:
        reference = self._require_reference()
        self.gateway.cancel(reference.workflow_id, cwd=prepared.worktree)
        return ProviderInspection(
            state="collecting",
            prior_known_state="running",
            terminal_state="cancelled",
        )

    def collect(self, prepared: PreparedRun) -> ProviderCollection:
        inspection = self.inspect(prepared)
        if inspection.terminal_state is None:
            raise RuntimeError("TORC workflow is not ready for collection")
        return self.collect_observed(
            inspection.terminal_state,
            exit_code=inspection.exit_code,
        )

    def collect_observed(
        self,
        terminal_state: str,
        *,
        exit_code: int | None,
    ) -> ProviderCollection:
        output = self._output_directory()
        reference = self._require_reference()
        if self.profile.mode == "remote" and terminal_state != "lost":
            self.gateway.collect_logs(reference.workflow_id, output, cwd=self.worktree)
            _extract_remote_log_archives(output)
        stdout = _read_matching_logs(output, stream="stdout")
        stderr = _read_matching_logs(output, stream="stderr")
        metrics = _read_resource_metrics(output)
        results = (
            None
            if terminal_state == "lost"
            else self.gateway.results(reference.workflow_id, cwd=self.worktree)
        )
        import re

        from waterology.core.atomic import write_json
        logs = {}
        total = 0
        for path in sorted(output.rglob("*")) if output.is_dir() else []:
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(output.resolve()):
                continue
            if path.suffix not in {".log", ".out", ".err", ".o", ".e"}:
                continue
            size = path.stat().st_size
            if size > 10_000_000 or total + size > 50_000_000:
                logs[path.relative_to(output).as_posix()] = {"omitted": "log retention size limit", "bytes": size}
                continue
            total += size
            text = path.read_bytes().decode("utf-8", errors="replace")
            for pattern in self.config.archive.log_redactions:
                text = re.sub(pattern, "[REDACTED]", text)
            logs[path.relative_to(output).as_posix()] = {"text": text}
        write_json(self.staging / "job-logs.json", logs)
        metrics = {"resource_metrics": metrics, "results": results}
        if terminal_state not in {"completed", "failed", "cancelled", "lost"}:
            raise RuntimeError(f"Invalid terminal TORC state: {terminal_state}")
        return ProviderCollection(
            stdout=stdout,
            stderr=stderr,
            metrics=metrics,
            exit_code=exit_code,
            terminal_state=terminal_state,  # type: ignore[arg-type]
        )

    def _output_directory(self) -> Path:
        if self.profile.local_output_root:
            root = Path(self.profile.local_output_root)
            _validate_output_directory(root, allow_missing=True)
            output = root / self.request.run_id
        else:
            output = self.staging / "torc-output"
        _validate_output_directory(output, allow_missing=True)
        return output

    def _require_reference(self) -> ExecutorReference:
        if self.reference is None:
            raise RuntimeError("TORC provider has not been launched")
        return self.reference


def _read_matching_logs(root: Path, *, stream: str) -> str:
    if not root.is_dir() or root.is_symlink():
        return ""
    payloads = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        lowered = path.name.lower()
        keywords = ("stdout",) if stream == "stdout" else ("stderr",)
        suffixes = (".out", ".o") if stream == "stdout" else (".err", ".e")
        if not any(keyword in lowered for keyword in keywords) and not lowered.endswith(suffixes):
            continue
        payloads.append(path.read_bytes().decode("utf-8", errors="replace"))
    return "".join(payloads)


def _read_resource_metrics(root: Path) -> dict[str, object]:
    if not root.is_dir() or root.is_symlink():
        return {"databases": []}
    databases = []
    for path in sorted(root.rglob("resource_metrics_*.db")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        databases.append(_summarize_resource_database(path, relative))
    return {"databases": databases}


def _summarize_resource_database(path: Path, relative: str) -> dict[str, object]:
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        jobs = [
            dict(row)
            for row in connection.execute(
                """
                SELECT samples.job_id, metadata.job_name,
                       COUNT(*) AS sample_count,
                       MAX(samples.cpu_percent) AS peak_cpu_percent,
                       AVG(samples.cpu_percent) AS avg_cpu_percent,
                       MAX(samples.memory_bytes) AS peak_memory_bytes,
                       CAST(AVG(samples.memory_bytes) AS INTEGER) AS avg_memory_bytes,
                       MAX(samples.num_processes) AS peak_process_count
                FROM job_resource_samples AS samples
                LEFT JOIN job_metadata AS metadata USING (job_id)
                GROUP BY samples.job_id, metadata.job_name
                ORDER BY samples.job_id
                """
            )
        ]
        system_row = connection.execute(
            """
            SELECT sample_count, peak_cpu_percent, avg_cpu_percent,
                   peak_memory_bytes, avg_memory_bytes
            FROM system_resource_summary
            WHERE id = 1
            """
        ).fetchone()
        system = (
            dict(system_row) if system_row is not None else _aggregate_system_samples(connection)
        )
    finally:
        connection.close()
    return {"jobs": jobs, "path": relative, "system": system}


def _aggregate_system_samples(connection: sqlite3.Connection) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT COUNT(*) AS sample_count,
               MAX(cpu_percent) AS peak_cpu_percent,
               AVG(cpu_percent) AS avg_cpu_percent,
               MAX(memory_bytes) AS peak_memory_bytes,
               CAST(AVG(memory_bytes) AS INTEGER) AS avg_memory_bytes
        FROM system_resource_samples
        """
    ).fetchone()
    if row is None or row["sample_count"] == 0:
        return None
    return dict(row)


def _validate_output_directory(path: Path, *, allow_missing: bool) -> None:
    if path.is_symlink():
        raise RuntimeError(f"TORC output directory must not be a symlink: {path}")
    if path.exists() and not path.is_dir():
        raise RuntimeError(f"TORC output path must be a directory: {path}")
    if not allow_missing and not path.is_dir():
        raise RuntimeError(f"TORC output directory does not exist: {path}")


def _extract_remote_log_archives(root: Path) -> None:
    for archive in sorted(root.glob("torc_logs_*.tar.gz")):
        if archive.is_symlink() or not archive.is_file():
            continue
        destination = root / archive.name.removesuffix(".tar.gz")
        if destination.is_dir() and not destination.is_symlink():
            continue
        with tarfile.open(archive, "r:gz") as source:
            members = source.getmembers()
            if len(members) > 10_000 or sum(member.size for member in members) > 1_000_000_000:
                raise RuntimeError("TORC remote log archive exceeds collection limits")
            if any(
                member.issym()
                or member.islnk()
                or member.isdev()
                or Path(member.name).is_absolute()
                or ".." in Path(member.name).parts
                for member in members
            ):
                raise RuntimeError("TORC remote log archive contains an unsafe path")
            with tempfile.TemporaryDirectory(prefix=".torc-logs-", dir=root) as temporary:
                extracted = Path(temporary) / "extracted"
                extracted.mkdir()
                source.extractall(extracted, members=members, filter="data")
                try:
                    extracted.replace(destination)
                except FileExistsError:
                    if not destination.is_dir() or destination.is_symlink():
                        raise
