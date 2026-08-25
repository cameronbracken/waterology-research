import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from pydantic import ValidationError

from waterology import __version__
from waterology.core.config import ProjectConfig, load_project_config
from waterology.core.database import open_database
from waterology.core.errors import WaterologyError
from waterology.core.experiments import load_experiment, load_worktree
from waterology.core.git import resolve_commit
from waterology.core.project import Project, discover_project, project_state_lock
from waterology.core.records import ArchiveVerification, ExecutorReference, RunManifest

_RUN_ID = re.compile(r"^run-[a-z0-9][a-z0-9-]{0,62}$")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")
_CHECKSUM_LINE = re.compile(r"^(?P<sha256>[0-9a-f]{64})  (?P<path>.+)$")
_STAGING_PAYLOADS = {
    "artifacts",
    "assessment.json",
    "checksums.sha256",
    "command.json",
    "environment.json",
    "execution.json",
    ".execution.json.tmp",
    "manifest.json",
    "metrics.json",
    "result.md",
    "source.tar.zst",
    "stderr.log",
    "stdout.log",
    "torc-output",
    "torc-slurm-workflow.yaml",
    "torc.json",
    "torc-workflow.yaml",
}


class ArchiveError(WaterologyError):
    code = "archive_error"


class ArchiveConflictError(ArchiveError):
    code = "archive_conflict"


class ArchivePathError(ArchiveError):
    code = "archive_path_invalid"


class ArchiveArtifactMissingError(ArchiveError):
    code = "archive_artifact_missing"


class ArchiveNotFoundError(ArchiveError):
    code = "archive_not_found"


class ArchiveExportError(ArchiveError):
    code = "archive_export_failed"


def build_run_archive(
    start: Path,
    *,
    experiment_id: str,
    run_id: str,
    commit_sha: str,
    command: tuple[str, ...],
    started_at: str,
    finished_at: str,
    terminal_state: str,
    exit_code: int | None,
    stdout: str,
    stderr: str,
    metrics: dict[str, object],
    process_id: int | None = None,
    executor_reference: ExecutorReference | None = None,
    compute_profile: str | None = None,
    config: ProjectConfig | None = None,
) -> Path:
    if _RUN_ID.fullmatch(run_id) is None:
        raise ValueError(f"Invalid run identifier: {run_id}")
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    worktree_record = load_worktree(project.root, experiment_id)
    worktree = Path(worktree_record.path)
    if not worktree_record.exists:
        raise ArchivePathError(f"Experiment worktree is missing: {experiment_id}")
    variant_config = config or load_project_config(worktree / "waterology.toml")
    if variant_config.name != experiment.project_id:
        raise ArchiveError(
            f"Experiment project {experiment.project_id} does not match waterology.toml"
        )
    project = Project(project.root, variant_config, project.paths)
    resolved_commit = resolve_commit(project.root, commit_sha)
    if resolved_commit != commit_sha:
        raise ArchiveError(f"Run commit is not canonical: {commit_sha}")
    if command != project.config.command:
        raise ArchiveError("Run command does not match waterology.toml")

    staging = project.paths.staging / run_id
    destination = project.paths.runs / run_id
    if destination.exists() or destination.is_symlink():
        raise ArchiveConflictError(f"Run archive path already exists: {run_id}")
    artifact_sources, missing = _resolve_artifacts(project, worktree)
    if (
        missing
        and terminal_state == "completed"
        and not project.config.archive.allow_missing_outputs
    ):
        raise ArchiveArtifactMissingError(
            f"Declared artifacts are missing: {', '.join(missing)}",
            details={"missing": list(missing)},
        )
    _prepare_staging(staging)
    collected = _collect_artifacts(artifact_sources, staging)

    manifest = RunManifest(
        run_id=run_id,
        project_id=project.config.name,
        experiment_id=experiment.id,
        commit_sha=commit_sha,
        command=command,
        started_at=started_at,
        finished_at=finished_at,
        process_id=process_id,
        executor="torc" if executor_reference is not None else "direct",
        executor_reference=executor_reference,
        terminal_state=terminal_state,
        exit_code=exit_code,
        declared_artifacts=project.config.outputs,
        collected_artifacts=collected,
        missing_artifacts=missing,
    )
    _write_json(staging / "manifest.json", manifest.model_dump(mode="json"))
    _write_json(staging / "command.json", {"arguments": list(command), "shell": False})
    _write_json(
        staging / "environment.json",
        _environment_payload(project, worktree, compute_profile=compute_profile),
    )
    _write_json(staging / "metrics.json", metrics)
    _write_json(
        staging / "assessment.json",
        {"assessment": "unassessed", "schema_version": 1},
    )
    (staging / "stdout.log").write_text(_redact_log(project, stdout), encoding="utf-8")
    (staging / "stderr.log").write_text(_redact_log(project, stderr), encoding="utf-8")
    (staging / "result.md").write_text(
        f"# Run {run_id}\n\nOperational state: {terminal_state}\n",
        encoding="utf-8",
    )
    _write_source_archive(project.root, commit_sha, staging / "source.tar.zst")
    _write_checksums(staging)
    (staging / "execution.json").unlink(missing_ok=True)
    (staging / ".execution.json.tmp").unlink(missing_ok=True)
    staging.replace(destination)
    return destination


def verify_archive(path: Path) -> ArchiveVerification:
    checksums_path = path / "checksums.sha256"
    expected = _read_checksums(checksums_path)
    payloads = tuple(child for child in path.rglob("*") if child != checksums_path)
    symlinks = {child.relative_to(path).as_posix() for child in payloads if child.is_symlink()}
    actual_paths = {
        child.relative_to(path).as_posix()
        for child in payloads
        if not child.is_symlink() and child.is_file()
    } | symlinks
    expected_paths = set(expected)
    missing = tuple(sorted(expected_paths - actual_paths))
    unexpected = tuple(sorted(actual_paths - expected_paths))
    changed = tuple(
        sorted(
            (expected_paths & symlinks)
            | {
                relative
                for relative in expected_paths & actual_paths - symlinks
                if _sha256(path / relative) != expected[relative]
            }
        )
    )
    return ArchiveVerification(
        run_id=path.name,
        valid=not missing and not changed and not unexpected,
        missing=missing,
        changed=changed,
        unexpected=unexpected,
    )


def load_archive(start: Path, run_id: str) -> RunManifest:
    _validate_run_id(run_id)
    project = discover_project(start)
    directory = project.paths.runs / run_id
    if directory.is_symlink():
        raise ArchivePathError(f"Run archive directory must not be a symlink: {run_id}")
    path = directory / "manifest.json"
    if not path.is_file():
        raise ArchiveNotFoundError(f"Run archive does not exist: {run_id}")
    try:
        manifest = RunManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise ArchiveError(f"Invalid run archive manifest: {path}") from error
    if manifest.run_id != run_id:
        raise ArchiveError(f"Run identifier {manifest.run_id} does not match directory {run_id}")
    return manifest


def list_archives(start: Path) -> tuple[RunManifest, ...]:
    project = discover_project(start)
    if not project.paths.runs.is_dir():
        return ()
    manifests = [
        load_archive(project.root, path.parent.name)
        for path in project.paths.runs.glob("run-*/manifest.json")
    ]
    return tuple(sorted(manifests, key=lambda manifest: (manifest.started_at, manifest.run_id)))


def verify_project_archive(start: Path, run_id: str) -> ArchiveVerification:
    project = discover_project(start)
    load_archive(project.root, run_id)
    return verify_archive(project.paths.runs / run_id)


def read_archive_logs(start: Path, run_id: str) -> dict[str, str]:
    project = discover_project(start)
    load_archive(project.root, run_id)
    archive = project.paths.runs / run_id
    return {
        "stdout": (archive / "stdout.log").read_text(encoding="utf-8"),
        "stderr": (archive / "stderr.log").read_text(encoding="utf-8"),
    }


def export_project_archive(start: Path, run_id: str, destination: str) -> Path:
    project = discover_project(start)
    relative = PurePosixPath(destination)
    if (
        not destination
        or "\\" in destination
        or _WINDOWS_ABSOLUTE.match(destination)
        or relative.is_absolute()
        or ".." in relative.parts
        or relative.as_posix() == "."
        or any(part.rstrip(" .") != part for part in relative.parts)
    ):
        raise ArchiveExportError("Archive export destination must be a relative project path")
    if relative.parts[0].casefold() in {".waterology", ".git"}:
        raise ArchiveExportError("Archive exports must be outside repository control state")
    output = project.root / relative.as_posix()
    parent = output.parent
    with project_state_lock(project.root), open_database(project.paths.database) as database:
        verification = verify_project_archive(project.root, run_id)
        if not verification.valid:
            raise ArchiveExportError(f"Archive failed verification before export: {run_id}")
        source = project.paths.runs / run_id
        for item in source.rglob("*"):
            if item.is_symlink():
                raise ArchiveExportError(
                    f"Archive contains a symlink: {item.relative_to(source)}"
                )
        expected_checksums = _read_checksums(source / "checksums.sha256")
        checksum_payload = (source / "checksums.sha256").read_bytes()
        current = project.root
        for part in relative.parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise ArchiveExportError(
                    f"Archive export parent must not be a symlink: {current}"
                )
        parent.mkdir(parents=True, exist_ok=True)
        try:
            resolved_parent = parent.resolve()
            resolved_parent.relative_to(project.root.resolve())
        except ValueError as error:
            raise ArchiveExportError("Archive export destination escapes the project") from error
        for reserved in (project.paths.state, project.root / ".git"):
            try:
                resolved_parent.relative_to(reserved.resolve())
            except ValueError:
                continue
            raise ArchiveExportError("Archive exports must be outside repository control state")
        if output.exists() or output.is_symlink():
            raise ArchiveExportError(f"Archive export already exists: {relative.as_posix()}")
        intent = database.append_intent(
            kind="archive.export",
            entity_type="run",
            entity_id=run_id,
            payload={"destination": relative.as_posix()},
        )
        descriptor, staged_name = tempfile.mkstemp(
            prefix=f".{output.name}.waterology-export-", dir=parent
        )
        staged = Path(staged_name)
        try:
            _write_export_tar(descriptor, staged, source, run_id)
            _verify_export_tar(
                staged,
                run_id,
                expected_checksums=expected_checksums,
                checksum_payload=checksum_payload,
            )
            os.link(staged, output)
            staged.unlink()
        except BaseException as error:
            staged.unlink(missing_ok=True)
            database.append_observation(
                intent.id,
                payload={"error": type(error).__name__, "outcome": "failed"},
            )
            if isinstance(error, FileExistsError):
                raise ArchiveExportError(
                    f"Archive export already exists: {relative.as_posix()}"
                ) from error
            if isinstance(error, ArchiveExportError):
                raise
            raise ArchiveExportError(f"Unable to export archive: {run_id}") from error
        database.append_observation(
            intent.id,
            payload={"destination": relative.as_posix(), "outcome": "exported"},
        )
    return output


def _write_export_tar(descriptor: int, staged: Path, source: Path, run_id: str) -> None:
    del staged
    with os.fdopen(descriptor, "wb") as stream:
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            archive.add(source, arcname=run_id, recursive=True)
        stream.flush()
        os.fsync(stream.fileno())


def _verify_export_tar(
    staged: Path,
    run_id: str,
    *,
    expected_checksums: dict[str, str],
    checksum_payload: bytes,
) -> None:
    expected_files = {
        f"{run_id}/checksums.sha256",
        *(f"{run_id}/{relative}" for relative in expected_checksums),
    }
    try:
        with tarfile.open(staged, mode="r:gz") as archive:
            members = archive.getmembers()
            if any(member.issym() or member.islnk() or not (member.isfile() or member.isdir()) for member in members):
                raise ArchiveExportError("Staged archive contains an unsafe entry")
            files = [member for member in members if member.isfile()]
            actual_files = {member.name for member in files}
            if len(actual_files) != len(files) or actual_files != expected_files:
                raise ArchiveExportError("Staged archive payload does not match its checksums")
            checksum_stream = archive.extractfile(f"{run_id}/checksums.sha256")
            if checksum_stream is None or checksum_stream.read() != checksum_payload:
                raise ArchiveExportError("Staged archive checksum file changed during export")
            for relative, expected in expected_checksums.items():
                stream = archive.extractfile(f"{run_id}/{relative}")
                if stream is None:
                    raise ArchiveExportError(
                        f"Staged archive payload is missing during export: {relative}"
                    )
                if _stream_sha256(stream) != expected:
                    raise ArchiveExportError(
                        f"Staged archive payload changed during export: {relative}"
                    )
    except (tarfile.TarError, OSError) as error:
        raise ArchiveExportError("Unable to verify staged archive export") from error


def _stream_sha256(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def _resolve_artifacts(
    project: Project,
    worktree: Path,
) -> tuple[tuple[tuple[str, Path], ...], tuple[str, ...]]:
    config = project.config
    sources = []
    missing = []
    for relative in config.outputs:
        _require_declared_artifact_root(relative, config.artifact_roots)
        source = worktree / relative
        if not source.exists() and not source.is_symlink():
            missing.append(relative)
            continue
        resolved = source.resolve()
        try:
            resolved.relative_to(worktree.resolve())
        except ValueError as error:
            raise ArchivePathError(
                f"Declared artifact escapes the experiment worktree: {relative}"
            ) from error
        if resolved.is_dir():
            for nested in resolved.rglob("*"):
                try:
                    nested.resolve().relative_to(worktree.resolve())
                except ValueError as error:
                    nested_relative = nested.relative_to(resolved).as_posix()
                    raise ArchivePathError(
                        "Declared artifact nested path escapes the experiment worktree: "
                        f"{relative}/{nested_relative}"
                    ) from error
        sources.append((relative, resolved))
    return tuple(sources), tuple(missing)


def _collect_artifacts(
    sources: tuple[tuple[str, Path], ...],
    staging: Path,
) -> tuple[str, ...]:
    artifacts_root = staging / "artifacts"
    artifacts_root.mkdir()
    collected = []
    for relative, resolved in sources:
        destination = artifacts_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if resolved.is_dir():
            shutil.copytree(resolved, destination)
        else:
            shutil.copy2(resolved, destination)
        collected.append(relative)
    return tuple(collected)


def _prepare_staging(staging: Path) -> None:
    if staging.is_symlink():
        raise ArchiveConflictError(f"Run staging path is a symlink: {staging.name}")
    if not staging.exists():
        staging.mkdir()
        return
    if not staging.is_dir():
        raise ArchiveConflictError(f"Run staging path is not a directory: {staging.name}")
    unexpected = sorted(
        child.name for child in staging.iterdir() if child.name not in _STAGING_PAYLOADS
    )
    if unexpected:
        raise ArchiveConflictError(
            f"Run staging path contains unknown payloads: {', '.join(unexpected)}"
        )
    for child in staging.iterdir():
        if (
            child.name
            in {
                "execution.json",
                "stdout.log",
                "stderr.log",
                "torc.json",
                "torc-slurm-workflow.yaml",
                "torc-workflow.yaml",
            }
            and not child.is_symlink()
            and child.is_file()
        ):
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def _require_declared_artifact_root(path: str, roots: tuple[str, ...]) -> None:
    candidate = PurePosixPath(path)
    if any(
        candidate == PurePosixPath(root) or PurePosixPath(root) in candidate.parents
        for root in roots
    ):
        return
    raise ArchivePathError(f"Declared artifact is outside configured artifact roots: {path}")


def _environment_payload(
    project: Project,
    worktree: Path,
    *,
    compute_profile: str | None = None,
) -> dict[str, object]:
    config = project.config
    environment_files = {}
    for relative in config.environment_files:
        path = worktree / relative
        if path.exists() or path.is_symlink():
            try:
                path.resolve().relative_to(worktree.resolve())
            except ValueError as error:
                raise ArchivePathError(
                    f"Environment file escapes the experiment worktree: {relative}"
                ) from error
        environment_files[relative] = _sha256(path) if path.is_file() else None
    variables = {
        name: hashlib.sha256(os.environ[name].encode()).hexdigest()
        for name in config.archive.environment_allowlist
        if name in os.environ
    }
    return {
        "architecture": platform.machine(),
        "compute_profile": compute_profile or config.default_compute_profile,
        "environment_files": environment_files,
        "operating_system": platform.system(),
        "python": platform.python_version(),
        "schema_version": 1,
        "tool_versions": {
            "git": _git_version(project.root),
            "waterology": __version__,
        },
        "variables_sha256": variables,
    }


def _redact_log(project: Project, value: str) -> str:
    redacted = value
    for pattern in project.config.archive.log_redactions:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def _git_version(repository: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


def _write_source_archive(repository: Path, commit_sha: str, destination: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repository), "archive", "--format=tar", commit_sha],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise ArchiveError(completed.stderr.decode(errors="replace").strip())
    destination.write_bytes(_zstd_compress(completed.stdout))


def _zstd_compress(data: bytes) -> bytes:
    if sys.version_info >= (3, 14):
        from compression import zstd

        return zstd.compress(data)
    import zstandard

    return zstandard.ZstdCompressor().compress(data)


def _write_checksums(directory: Path) -> None:
    excluded = {"checksums.sha256", "execution.json", ".execution.json.tmp"}
    paths = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.relative_to(directory).as_posix() not in excluded
    )
    lines = [f"{_sha256(path)}  {path.relative_to(directory).as_posix()}" for path in paths]
    (directory / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_checksums(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ArchiveError(f"Archive checksum file is missing: {path}")
    checksums = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise ArchiveError(f"Invalid archive checksum line: {line}")
        relative = PurePosixPath(match.group("path"))
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in match.group("path")
            or relative.as_posix() in {".", "checksums.sha256"}
        ):
            raise ArchivePathError(f"Archive checksum contains unsafe path: {match.group('path')}")
        normalized = relative.as_posix()
        if normalized in checksums:
            raise ArchiveError(f"Duplicate archive checksum path: {normalized}")
        checksums[normalized] = match.group("sha256")
    return checksums


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_run_id(run_id: str) -> None:
    if _RUN_ID.fullmatch(run_id) is None:
        raise ValueError(f"Invalid run identifier: {run_id}")
