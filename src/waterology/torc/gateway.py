import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from waterology.core.errors import WaterologyError


class TorcError(WaterologyError):
    code = "torc_error"


class TorcUnavailableError(TorcError):
    code = "torc_unavailable"


class TorcCommandError(TorcError):
    code = "torc_command_failed"


class TorcWorkflowNotFoundError(TorcCommandError):
    code = "torc_workflow_not_found"


class TorcIncompatibleVersionError(TorcError):
    code = "torc_incompatible_version"


class TorcPartialLaunchError(TorcCommandError):
    code = "torc_partial_launch"

    def __init__(self, message: str, record: "TorcLaunchRecord") -> None:
        super().__init__(message)
        self.record = record


@dataclass(frozen=True)
class TorcLaunchRecord:
    workflow_id: str
    job_ids: tuple[str, ...]
    process_id: int | None = None


@dataclass(frozen=True)
class TorcWorkflowObservation:
    workflow_id: str
    state: str
    jobs: tuple[dict[str, object], ...]
    payload: dict[str, object]


class TorcGateway(Protocol):
    def validate(self, workflow: Path, *, cwd: Path) -> dict[str, object]: ...

    def create(self, workflow: Path, *, cwd: Path) -> TorcLaunchRecord: ...

    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation: ...

    def cancel(self, workflow_id: str, *, cwd: Path) -> dict[str, object]: ...

    def version(self, *, cwd: Path) -> str: ...

    def collect_logs(self, workflow_id: str, destination: Path, *, cwd: Path) -> None: ...

    def results(self, workflow_id: str, *, cwd: Path) -> object: ...

    def launch(
        self,
        workflow: Path,
        *,
        mode: Literal["local", "remote", "slurm"],
        ssh_alias: str | None,
        torc_profile: str | None,
        slurm_account: str | None,
        output_dir: Path,
        cwd: Path,
        access_group_id: int | None = None,
    ) -> TorcLaunchRecord: ...


class TorcCliGateway:
    def __init__(
        self,
        api_url: str,
        *,
        executable: str = "torc",
        timeout_seconds: float = 30,
    ) -> None:
        self.api_url = api_url
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def create(self, workflow: Path, *, cwd: Path) -> TorcLaunchRecord:
        payload = self._json(
            ["create", str(workflow)],
            cwd=cwd,
        )
        return _launch_record(payload)

    def validate(self, workflow: Path, *, cwd: Path) -> dict[str, object]:
        return self._json(["create", "--dry-run", str(workflow)], cwd=cwd)

    def launch(
        self,
        workflow: Path,
        *,
        mode: Literal["local", "remote", "slurm"],
        ssh_alias: str | None,
        torc_profile: str | None,
        slurm_account: str | None,
        output_dir: Path,
        cwd: Path,
        access_group_id: int | None = None,
    ) -> TorcLaunchRecord:
        _prepare_output_directory(output_dir)
        if mode == "local":
            created = self.create(workflow, cwd=cwd)
            try:
                process_id = self._spawn(
                    ["run", created.workflow_id, "--output-dir", str(output_dir)],
                    cwd=cwd,
                    stdout_path=output_dir / "torc-runner.stdout.log",
                    stderr_path=output_dir / "torc-runner.stderr.log",
                )
            except TorcError as error:
                raise TorcPartialLaunchError(str(error), created) from error
            return TorcLaunchRecord(created.workflow_id, created.job_ids, process_id)
        if mode == "slurm":
            generated = workflow.with_name("torc-slurm-workflow.yaml")
            arguments = ["slurm", "generate"]
            if torc_profile:
                arguments.extend(["--profile", torc_profile])
            if slurm_account:
                arguments.extend(["--account", slurm_account])
            arguments.extend(["--output", str(generated), str(workflow)])
            self._run(arguments, cwd=cwd, json_output=False)
            return _launch_record(
                self._json(
                    ["submit", str(generated), "--output-dir", str(output_dir), "--no-prompts"],
                    cwd=cwd,
                )
            )
        if not ssh_alias:
            raise TorcCommandError("Remote TORC launch requires an SSH alias")
        created = self.create(workflow, cwd=cwd)
        try:
            if access_group_id is not None:
                self._run(
                    [
                        "access-groups",
                        "add-workflow",
                        created.workflow_id,
                        str(access_group_id),
                    ],
                    cwd=cwd,
                    json_output=False,
                )
            self._run(
                ["remote", "add-workers", created.workflow_id, ssh_alias],
                cwd=cwd,
                json_output=False,
            )
            self._run(
                ["remote", "run", created.workflow_id],
                cwd=cwd,
                json_output=False,
            )
        except TorcError as error:
            raise TorcPartialLaunchError(str(error), created) from error
        return created

    def inspect(self, workflow_id: str, *, cwd: Path) -> TorcWorkflowObservation:
        payload = self._json(["status", workflow_id], cwd=cwd)
        if isinstance(payload.get("jobs_by_status"), dict):
            return TorcWorkflowObservation(
                workflow_id=str(payload.get("workflow_id", workflow_id)),
                state=_state_from_status_counts(payload["jobs_by_status"]),
                jobs=(),
                payload=payload,
            )
        workflow = payload.get("workflow", payload)
        identifier = _required_identifier(workflow, "id", "workflow")
        state = workflow.get("status", workflow.get("state"))
        if not isinstance(state, str):
            raise TorcCommandError("TORC workflow response has no state")
        jobs = payload.get("jobs", workflow.get("jobs", []))
        if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
            raise TorcCommandError("TORC workflow response has invalid jobs")
        return TorcWorkflowObservation(identifier, state, tuple(jobs), payload)

    def cancel(self, workflow_id: str, *, cwd: Path) -> dict[str, object]:
        payload = self._json(["cancel", workflow_id, "--no-prompts"], cwd=cwd)
        status = str(payload.get("status", "")).strip().lower()
        if status != "success":
            raise TorcCommandError("TORC cancellation was not completed for every allocation")
        return payload

    def version(self, *, cwd: Path) -> str:
        completed = self._run(["--version"], cwd=cwd, json_output=False)
        version = completed.stdout.strip()
        if not version:
            raise TorcCommandError("TORC version command returned no version")
        match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version)
        if match is None:
            raise TorcIncompatibleVersionError(f"Unable to parse TORC version: {version}")
        parsed = tuple(int(value) for value in match.groups())
        if parsed < (0, 40, 0):
            raise TorcIncompatibleVersionError(
                f"TORC 0.40.0 or newer is required; found {match.group(0)}"
            )
        return version

    def collect_logs(self, workflow_id: str, destination: Path, *, cwd: Path) -> None:
        _prepare_output_directory(destination)
        self._run(
            ["remote", "collect-logs", workflow_id, "--local-output-dir", str(destination)],
            cwd=cwd,
            json_output=False,
        )

    def results(self, workflow_id: str, *, cwd: Path) -> object:
        return self._json(["results", "list", workflow_id], cwd=cwd)

    def health(self, *, cwd: Path) -> dict[str, object]:
        return self._json(["workflows", "list", "--limit", "1"], cwd=cwd)

    def _json(self, arguments: list[str], *, cwd: Path) -> dict[str, object]:
        completed = self._run(arguments, cwd=cwd, json_output=True)
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise TorcCommandError("TORC command returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise TorcCommandError("TORC command returned a non-object JSON response")
        return payload

    def _run(
        self,
        arguments: list[str],
        *,
        cwd: Path,
        json_output: bool,
    ) -> subprocess.CompletedProcess[str]:
        command = [self.executable]
        if json_output:
            command.extend(["--format", "json"])
        command.extend(arguments)
        environment = os.environ.copy()
        environment["TORC_CLIENT__API_URL"] = self.api_url
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as error:
            raise TorcUnavailableError(
                f"TORC executable was not found: {self.executable}"
            ) from error
        except subprocess.TimeoutExpired as error:
            raise TorcUnavailableError("TORC command timed out") from error
        if completed.returncode != 0:
            message = completed.stderr.strip() or "TORC command failed"
            lowered = message.lower()
            status_lookup = len(arguments) >= 2 and arguments[0] == "status"
            confirmed_absence = status_lookup and (
                re.search(r"workflow[^\n]*(?:not found|404)", lowered) is not None
                or re.search(r"404[^\n]*workflow", lowered) is not None
            )
            if confirmed_absence:
                raise TorcWorkflowNotFoundError(message)
            if any(
                marker in lowered
                for marker in (
                    "connection refused",
                    "could not connect",
                    "timed out",
                    "unavailable",
                )
            ):
                raise TorcUnavailableError(message)
            raise TorcCommandError(message)
        return completed

    def _spawn(
        self,
        arguments: list[str],
        *,
        cwd: Path,
        stdout_path: Path,
        stderr_path: Path,
    ) -> int:
        command = [self.executable, *arguments]
        environment = os.environ.copy()
        environment["TORC_CLIENT__API_URL"] = self.api_url
        try:
            with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                )
        except FileNotFoundError as error:
            raise TorcUnavailableError(
                f"TORC executable was not found: {self.executable}"
            ) from error
        except OSError as error:
            raise TorcCommandError(f"Unable to start TORC runner: {error}") from error
        return process.pid


def _required_identifier(payload: object, field: str, kind: str) -> str:
    if not isinstance(payload, dict) or not isinstance(payload.get(field), str):
        raise TorcCommandError(f"TORC response has no {kind} identifier")
    return payload[field]


def _launch_record(payload: dict[str, object]) -> TorcLaunchRecord:
    if isinstance(payload.get("workflow_id"), (str, int)):
        workflow_id = str(payload["workflow_id"])
        raw_job_ids = payload.get("job_ids", [])
        if not isinstance(raw_job_ids, list):
            raise TorcCommandError("TORC response has invalid job identifiers")
        return TorcLaunchRecord(workflow_id, tuple(str(value) for value in raw_job_ids))
    workflow_payload = payload.get("workflow", payload)
    workflow_id = _required_identifier(workflow_payload, "id", "workflow")
    jobs = payload.get("jobs")
    if jobs is None and isinstance(workflow_payload, dict):
        jobs = workflow_payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise TorcCommandError("TORC response has invalid jobs")
    job_ids = tuple(_required_identifier(job, "id", "job") for job in jobs if isinstance(job, dict))
    return TorcLaunchRecord(workflow_id=workflow_id, job_ids=job_ids)


def _state_from_status_counts(counts: object) -> str:
    if not isinstance(counts, dict):
        raise TorcCommandError("TORC status response has invalid job counts")

    def count(name: str) -> int:
        value = counts.get(name, 0)
        if not isinstance(value, int) or value < 0:
            raise TorcCommandError("TORC status response has invalid job counts")
        return value

    if any(not isinstance(value, int) or value < 0 for value in counts.values()):
        raise TorcCommandError("TORC status response has invalid job counts")
    if count("running"):
        return "running"
    if count("pending"):
        return "pending"
    if count("ready") or count("blocked") or count("uninitialized"):
        return "ready"
    known_states = {
        "blocked",
        "canceled",
        "completed",
        "disabled",
        "failed",
        "pending",
        "pending_failed",
        "ready",
        "running",
        "terminated",
        "uninitialized",
    }
    if count("pending_failed") or any(
        value > 0 for name, value in counts.items() if name not in known_states
    ):
        return "unknown"
    if count("failed") or count("terminated"):
        return "failed"
    if count("canceled"):
        return "canceled"
    if count("completed"):
        return "completed"
    if count("disabled"):
        return "completed"
    return "unknown"


def _prepare_output_directory(path: Path) -> None:
    if path.is_symlink():
        raise TorcCommandError(f"TORC output directory must not be a symlink: {path}")
    if path.exists() and not path.is_dir():
        raise TorcCommandError(f"TORC output path must be a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
