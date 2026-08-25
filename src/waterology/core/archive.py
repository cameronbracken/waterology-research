import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from waterology.core.errors import WaterologyError
from waterology.core.experiments import load_experiment, load_worktree
from waterology.core.git import resolve_commit
from waterology.core.project import Project, discover_project
from waterology.core.records import ArchiveVerification, RunManifest

_RUN_ID = re.compile(r"^run-[a-z0-9][a-z0-9-]{0,62}$")
_CHECKSUM_LINE = re.compile(r"^(?P<sha256>[0-9a-f]{64})  (?P<path>.+)$")
_STAGING_PAYLOADS = {
    "artifacts",
    "assessment.json",
    "checksums.sha256",
    "command.json",
    "environment.json",
    "manifest.json",
    "metrics.json",
    "result.md",
    "source.tar.zst",
    "stderr.log",
    "stdout.log",
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
) -> Path:
    if _RUN_ID.fullmatch(run_id) is None:
        raise ValueError(f"Invalid run identifier: {run_id}")
    project = discover_project(start)
    experiment = load_experiment(project.root, experiment_id)
    worktree_record = load_worktree(project.root, experiment_id)
    worktree = Path(worktree_record.path)
    if not worktree_record.exists:
        raise ArchivePathError(f"Experiment worktree is missing: {experiment_id}")
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
        terminal_state=terminal_state,
        exit_code=exit_code,
        declared_artifacts=project.config.outputs,
        collected_artifacts=collected,
        missing_artifacts=missing,
    )
    _write_json(staging / "manifest.json", manifest.model_dump(mode="json"))
    _write_json(staging / "command.json", {"arguments": list(command), "shell": False})
    _write_json(staging / "environment.json", _environment_payload(project, worktree))
    _write_json(staging / "metrics.json", metrics)
    _write_json(
        staging / "assessment.json",
        {"assessment": "unassessed", "schema_version": 1},
    )
    (staging / "stdout.log").write_text(stdout, encoding="utf-8")
    (staging / "stderr.log").write_text(stderr, encoding="utf-8")
    (staging / "result.md").write_text(
        f"# Run {run_id}\n\nOperational state: {terminal_state}\n",
        encoding="utf-8",
    )
    _write_source_archive(project.root, commit_sha, staging / "source.tar.zst")
    _write_checksums(staging)
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
    path = project.paths.runs / run_id / "manifest.json"
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


def _environment_payload(project: Project, worktree: Path) -> dict[str, object]:
    config = project.config
    environment_files = {}
    for relative in config.environment_files:
        path = worktree / relative
        environment_files[relative] = _sha256(path) if path.is_file() else None
    variables = {
        name: hashlib.sha256(os.environ[name].encode()).hexdigest()
        for name in config.archive.environment_allowlist
        if name in os.environ
    }
    return {
        "architecture": platform.machine(),
        "compute_profile": config.default_compute_profile,
        "environment_files": environment_files,
        "operating_system": platform.system(),
        "python": platform.python_version(),
        "schema_version": 1,
        "variables_sha256": variables,
    }


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
    paths = sorted(
        path for path in directory.rglob("*") if path.is_file() and path.name != "checksums.sha256"
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
