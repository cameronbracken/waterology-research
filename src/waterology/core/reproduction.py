"""Portable source snapshots and separately recorded fresh reproduction attempts."""

import io
import json
import math
import shutil
import subprocess
import tarfile
from pathlib import Path
from uuid import uuid4

import zstandard

from waterology.core.archive import load_archive, verify_archive
from waterology.core.atomic import exclusive_file_lock, write_json
from waterology.core.config import DeliverableConfig, ProjectConfig
from waterology.core.errors import WaterologyError
from waterology.core.experiments import create_experiment, load_worktree
from waterology.core.git import current_commit, git_output, is_clean
from waterology.core.profiles import machine_config_path
from waterology.core.project import discover_project, initialize_project
from waterology.core.registry import file_sha256, project_file, register_entry, resolve_workflow
from waterology.core.workflows import watch_workflow
from waterology.torc.runs import inspect_torc_run, start_torc_run


def _verified(path: Path) -> None:
    if not verify_archive(path).valid:
        raise ValueError(f"Archive integrity check failed: {path.name}")


def register_deliverable(start: Path, name: str, definition: DeliverableConfig) -> dict:
    project = discover_project(start)
    reference = load_archive(start, definition.reference_run)
    archive = project.paths.runs / definition.reference_run
    _verified(archive)
    if reference.terminal_state != "completed":
        raise ValueError("A deliverable requires a completed reference run")
    snapshot = archive / "execution-config.json"
    if not snapshot.is_file():
        raise ValueError(
            "Reference run lacks an execution snapshot; execute the named workflow first"
        )
    config = ProjectConfig.model_validate(json.loads(snapshot.read_text())["config"])
    if definition.workflow not in config.workflows:
        raise ValueError("Reference run does not contain the selected workflow")
    selected = config.workflows[definition.workflow]
    if (selected.command or ("torc", "workflow", selected.torc_file)) != reference.command:
        raise ValueError("Reference run executed a different workflow")
    for field in ("outputs", "metrics", "restore", "environment_probe", "torc_file"):
        if getattr(selected, field) != getattr(config, field):
            raise ValueError("Reference run used a different workflow evidence contract")
    if selected.environment_files and selected.environment_files != config.environment_files:
        raise ValueError("Reference environment does not match the selected workflow")
    for check in definition.checks:
        path = project_file(archive / "artifacts", check.path)
        if not path.is_file():
            raise ValueError(f"Reference output is missing: {check.path}")
        if check.validator and check.validator not in config.workflows:
            raise ValueError(f"Validator is absent from the pinned source: {check.validator}")
    return register_entry(
        start, "deliverables", name, definition.model_dump(mode="json", exclude_none=True)
    )


def export_deliverable(start: Path, name: str, destination: Path) -> dict:
    project = discover_project(start)
    definition = project.config.deliverables[name]
    source = project.paths.runs / definition.reference_run
    _verified(source)
    if not (source / "source-commit.txt").is_file():
        raise ValueError("Legacy archive has no source commit object; rerun before export")
    destination = destination.resolve()
    if destination.is_relative_to(project.root) and any(
        part in {".git", ".waterology"} for part in destination.relative_to(project.root).parts
    ):
        raise ValueError("Export destination cannot be inside project control state")
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, destination / "reference", symlinks=False)
    write_json(destination / "deliverable.json", definition.model_dump(mode="json"))
    payloads = {
        p.relative_to(destination).as_posix(): file_sha256(p)
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    write_json(destination / "bundle-checksums.json", payloads)
    return {
        "destination": str(destination),
        "name": name,
        "reference_run": definition.reference_run,
    }


def _verify_bundle(bundle: Path) -> DeliverableConfig:
    expected = json.loads((bundle / "bundle-checksums.json").read_text())
    actual = {
        p.relative_to(bundle).as_posix()
        for p in bundle.rglob("*")
        if p.is_file() and p != bundle / "bundle-checksums.json"
    }
    if set(expected) != actual:
        raise ValueError("Bundle files differ from the export manifest")
    for relative, digest in expected.items():
        path = project_file(bundle, relative)
        if file_sha256(path) != digest:
            raise ValueError(f"Bundle file changed: {relative}")
    _verified(bundle / "reference")
    return DeliverableConfig.model_validate_json((bundle / "deliverable.json").read_text())


def _restore_source(archive: Path, destination: Path) -> None:
    destination.mkdir()
    with (
        (archive / "source.tar.zst").open("rb") as source,
        zstandard.ZstdDecompressor().stream_reader(source) as decompressed,
        tarfile.open(fileobj=io.BytesIO(decompressed.read())) as tar,
    ):
        members = tar.getmembers()
        for member in members:
            if not member.isfile() and not member.isdir():
                raise ValueError("Portable reproduction currently requires regular source files")
            path = project_file(destination, member.name.rstrip("/"))
            if ".git" in path.relative_to(destination).parts:
                raise ValueError("Source archive contains Git control paths")
        tar.extractall(destination, filter="data")
    git_output(destination, "init", "-q")
    git_output(destination, "config", "core.autocrlf", "false")
    git_output(destination, "add", "--force", ".")
    for member in members:
        if member.isfile():
            git_output(
                destination,
                "update-index",
                "--chmod=+x" if member.mode & 0o111 else "--chmod=-x",
                "--",
                member.name,
            )
    raw = (archive / "source-commit.txt").read_bytes()
    tree = raw.split(b"\n", 1)[0].decode().removeprefix("tree ")
    if git_output(destination, "write-tree") != tree:
        raise ValueError("Restored source does not match the original Git tree")
    result = subprocess.run(
        ["git", "-C", str(destination), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=raw,
        capture_output=True,
        check=True,
    )
    commit = result.stdout.decode().strip()
    expected = json.loads((archive / "manifest.json").read_text())["commit_sha"]
    if commit != expected:
        raise ValueError("Source commit object does not match the reference")
    if b"\nparent " in raw:
        (destination / ".git" / "shallow").write_text(commit + "\n")
    git_output(destination, "update-ref", "HEAD", commit)
    git_output(destination, "reset", "--hard", commit)
    initialize_project(destination)


def _compare(reference: Path, actual: Path, checks) -> list[dict]:
    outcomes = []
    for check in checks:
        if check.mode == "statistical":
            continue
        expected_file = project_file(reference / "artifacts", check.path)
        actual_file = project_file(actual / "artifacts", check.path)
        passed = False
        reason = "output is missing"
        if actual_file.is_file():
            if check.mode == "bytes":
                passed = expected_file.read_bytes() == actual_file.read_bytes()
                reason = "byte comparison"
            else:
                try:
                    expected = json.loads(expected_file.read_text())
                    observed = json.loads(actual_file.read_text())
                    for key in check.field.split("."):
                        expected, observed = expected[key], observed[key]
                    if isinstance(expected, bool) or isinstance(observed, bool):
                        raise TypeError("Boolean values are not numeric results")
                    passed = (
                        math.isfinite(expected)
                        and math.isfinite(observed)
                        and math.isclose(observed, expected, rel_tol=check.rtol, abs_tol=check.atol)
                    )
                    reason = "numeric comparison"
                except (ValueError, TypeError, KeyError):
                    reason = "numeric output is missing, invalid or nonfinite"
        outcomes.append(
            {"path": check.path, "mode": check.mode, "passed": passed, "reason": reason}
        )
    return outcomes


def reproduce_deliverable(
    start: Path,
    name: str,
    destination: Path,
    *,
    profile: str | None = None,
    bundle: bool = False,
    resume: bool = False,
    inputs: Path | None = None,
    gateway=None,
    progress=None,
    wait: bool = True,
    confirm_remote: bool = False,
) -> dict:
    destination = destination.resolve()
    if not resume:
        destination.mkdir(parents=True, exist_ok=False)
        if bundle:
            _verify_bundle(start)
            shutil.copytree(start, destination / "bundle")
        else:
            export_deliverable(start, name, destination / "bundle")
        record = {
            "id": f"reproduction-{uuid4().hex[:16]}",
            "state": "preparing",
            "name": name,
            "profile": profile,
            "run_id": None,
            "validator_runs": {},
        }
        write_json(destination / "reproduction.json", record)
    with exclusive_file_lock(destination / ".reproduction.lock"):
        record = json.loads((destination / "reproduction.json").read_text())
        definition = _verify_bundle(destination / "bundle")
        reference = destination / "bundle" / "reference"
        source = destination / "project"
        if record["state"] in {"passed", "failed"}:
            seal = destination / "reproduction-checksum.txt"
            if not seal.is_file() or seal.read_text().strip() != file_sha256(
                destination / "reproduction.json"
            ):
                raise ValueError("Reproduction record integrity check failed")
            if record["state"] == "passed":
                for identifier in [record["run_id"], *record["validator_runs"].values()]:
                    _verified(source / ".waterology" / "runs" / identifier)
            return record
        try:
            if profile is not None and profile != record["profile"]:
                if record["run_id"] and source.exists() and _reserved(source, record["run_id"]):
                    raise ValueError("Cannot change profile after a reproduction run was reserved")
                record.setdefault("profile_changes", []).append(
                    {"from": record["profile"], "to": profile}
                )
                record["profile"] = profile
                write_json(destination / "reproduction.json", record)
            if not source.exists():
                staged_source = destination / f"source-stage-{uuid4().hex[:12]}"
                record.setdefault("source_stages", []).append(staged_source.name)
                write_json(destination / "reproduction.json", record)
                _restore_source(reference, staged_source)
                staged_source.replace(source)
            if record.get("experiment_id") is None:
                experiment = create_experiment(
                    source, hypothesis=f"Reproduce {name}", workflow=definition.workflow
                )
                record["experiment_id"] = experiment.id
                write_json(destination / "reproduction.json", record)
            worktree = Path(load_worktree(source, record["experiment_id"]).path)
            # Inputs are explicitly supplied, hashed and copied; never harvested from the original checkout.
            source_config = discover_project(source).config
            workflow = source_config.workflows[definition.workflow]
            for relative, expected in workflow.input_files.items():
                target = project_file(worktree, relative)
                if not target.is_file() and inputs is not None:
                    supplied = project_file(inputs.resolve(), relative)
                    if not supplied.is_file() or file_sha256(supplied) != expected:
                        raise ValueError(f"Supplied input does not match its identity: {relative}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(supplied, target)
            expected_commit = json.loads((reference / "manifest.json").read_text())["commit_sha"]
            if current_commit(worktree) != expected_commit or not is_clean(worktree):
                raise ValueError("Reproduction source changed; restore the exact selected commit")
            config = resolve_workflow(worktree, definition.workflow)
            pinned_config = ProjectConfig.model_validate(
                json.loads((reference / "execution-config.json").read_text())["config"]
            )
            if config != pinned_config:
                raise ValueError("Reproduction execution configuration differs from the reference")
            if not workflow.environment_files and not config.environment_files:
                raise ValueError(
                    "Reproduction requires declared environment files and restore commands"
                )
            if not workflow.restore:
                raise ValueError(
                    "Reproduction requires explicit locked environment restore commands"
                )
            if not workflow.environment_probe:
                raise ValueError("Reproduction requires a worker environment_probe command")
            # A newly restored worktree has no native task caches. Tracked generated outputs are refused.
            if not record["run_id"]:
                record["run_id"] = f"run-{uuid4().hex[:12]}"
                record["state"] = "submitting"
                write_json(destination / "reproduction.json", record)
            if not _reserved(source, record["run_id"]):
                for relative in config.outputs:
                    if project_file(worktree, relative).exists():
                        raise ValueError(f"Fresh reproduction output already exists: {relative}")
                for cache in (".pixi/task-cache-v0", ".pixi/task-cache"):
                    if project_file(worktree, cache).exists():
                        raise ValueError(f"Fresh reproduction task cache already exists: {cache}")
                start_torc_run(
                    source,
                    record["experiment_id"],
                    profile_name=record["profile"] or config.default_compute_profile,
                    machine_config_file=machine_config_path(),
                    run_id=record["run_id"],
                    gateway=gateway,
                    confirm_remote=confirm_remote,
                )
            record["state"] = "running"
            write_json(destination / "reproduction.json", record)
            result = (
                watch_workflow(source, record["run_id"], gateway=gateway, progress=progress)
                if wait
                else inspect_torc_run(
                    source,
                    record["run_id"],
                    machine_config_file=machine_config_path(),
                    gateway=gateway,
                )
            )
            if getattr(result, "terminal_state", None) != "completed":
                record["state"] = (
                    "failed"
                    if getattr(result, "terminal_state", None)
                    or getattr(result, "operational_state", None) in {"failed", "lost", "cancelled"}
                    else "blocked"
                    if getattr(result, "operational_state", None) == "unknown"
                    else "running"
                )
                record["reason"] = (
                    "Fresh execution did not complete; inspect the saved run. A failed preparation requires a new reproduction directory after repair."
                )
            else:
                actual = discover_project(source).paths.runs / record["run_id"]
                _verified(actual)
                if result.commit_sha != expected_commit:
                    raise ValueError("Fresh run used a different source commit")
                logs = json.loads((actual / "job-logs.json").read_text())
                evidence = [
                    entry.get("text", "").split("WATEROLOGY_WORKER_ENVIRONMENT", 1)[1].strip()
                    for entry in logs.values()
                    if "WATEROLOGY_WORKER_ENVIRONMENT" in entry.get("text", "")
                ]
                if not any(evidence):
                    raise ValueError("Worker environment probe evidence is missing")
                record["worker_environment_evidence"] = "job-logs.json"
                outcomes = _compare(reference, actual, definition.checks)
                for check in definition.checks:
                    if check.mode != "statistical":
                        continue
                    if not project_file(actual / "artifacts", check.path).is_file():
                        outcomes.append(
                            {
                                "path": check.path,
                                "mode": "statistical",
                                "passed": False,
                                "reason": "output is missing",
                            }
                        )
                        continue
                    validator = check.validator
                    reference_target = worktree / ".waterology-reference"
                    if reference_target.exists() and not record.get("reference_staged"):
                        raise ValueError("Reserved validator reference path already exists")
                    if not reference_target.exists():
                        exclude = Path(
                            git_output(worktree, "rev-parse", "--git-path", "info/exclude")
                        )
                        if not exclude.is_absolute():
                            exclude = worktree / exclude
                        exclude.parent.mkdir(parents=True, exist_ok=True)
                        with exclude.open("a") as stream:
                            stream.write("\n.waterology-reference/\n")
                        shutil.copytree(reference / "artifacts", reference_target)
                        record["reference_staged"] = True
                        write_json(destination / "reproduction.json", record)
                    _verify_validation_inputs(reference, actual, worktree)
                    validation_config = resolve_workflow(worktree, validator)
                    if validator not in record["validator_runs"]:
                        identifier = f"run-{uuid4().hex[:12]}"
                        record["validator_runs"][validator] = identifier
                        write_json(destination / "reproduction.json", record)
                    if not _reserved(source, record["validator_runs"][validator]):
                        identifier = record["validator_runs"][validator]
                        start_torc_run(
                            source,
                            record["experiment_id"],
                            profile_name=record["profile"] or config.default_compute_profile,
                            machine_config_file=machine_config_path(),
                            run_id=identifier,
                            gateway=gateway,
                            config_override=validation_config,
                            confirm_remote=confirm_remote,
                        )
                    validation = (
                        watch_workflow(
                            source,
                            record["validator_runs"][validator],
                            gateway=gateway,
                            progress=progress,
                        )
                        if wait
                        else inspect_torc_run(
                            source,
                            record["validator_runs"][validator],
                            machine_config_file=machine_config_path(),
                            gateway=gateway,
                        )
                    )
                    if getattr(validation, "operational_state", None) in {
                        "failed",
                        "lost",
                        "cancelled",
                    }:
                        outcomes.append(
                            {
                                "path": check.path,
                                "mode": "statistical",
                                "passed": False,
                                "reason": "Validator preparation or execution failed",
                                "validator_run": validation.run_id,
                            }
                        )
                        continue
                    if getattr(validation, "terminal_state", None) is None:
                        if not wait:
                            record["state"] = "validating"
                            write_json(destination / "reproduction.json", record)
                            return record
                        raise ValueError(
                            "Validator execution remains unresolved; resume this reproduction"
                        )
                    validator_archive = discover_project(source).paths.runs / validation.run_id
                    _verified(validator_archive)
                    if validation.commit_sha != expected_commit:
                        raise ValueError("Validator source differs from the selected commit")
                    saved_validator = ProjectConfig.model_validate(
                        json.loads((validator_archive / "execution-config.json").read_text())[
                            "config"
                        ]
                    )
                    if saved_validator != validation_config:
                        raise ValueError("Validator execution configuration changed")
                    _verify_validation_inputs(reference, actual, worktree)
                    outcomes.append(
                        {
                            "path": check.path,
                            "mode": "statistical",
                            "validator_run": validation.run_id,
                            "passed": validation.terminal_state == "completed",
                        }
                    )
                record["checks"] = outcomes
                record["state"] = (
                    "passed" if outcomes and all(o["passed"] for o in outcomes) else "failed"
                )
                record.pop("reason", None)
        except (
            ValueError,
            OSError,
            KeyError,
            subprocess.SubprocessError,
            WaterologyError,
        ) as error:
            record["state"] = "blocked"
            record["reason"] = str(error)
            identifiers = [record.get("run_id"), *record["validator_runs"].values()]
            if (source / ".waterology" / "state.sqlite").is_file() and any(
                identifier and _run_state(source, identifier) in {"failed", "lost", "cancelled"}
                for identifier in identifiers
            ):
                record["state"] = "failed"
        write_json(destination / "reproduction.json", record)
        if record["state"] in {"passed", "failed"}:
            from waterology.core.atomic import write_text

            write_text(
                destination / "reproduction-checksum.txt",
                file_sha256(destination / "reproduction.json") + "\n",
            )
        return record


def _run_state(source: Path, identifier: str) -> str | None:
    from waterology.core.database import open_database

    with open_database(discover_project(source).paths.database) as database:
        row = database.connection.execute(
            "SELECT operational_state FROM runs WHERE id = ?", (identifier,)
        ).fetchone()
        return row[0] if row else None


def _reserved(source: Path, identifier: str) -> bool:
    return _run_state(source, identifier) is not None


def _verify_validation_inputs(reference: Path, actual: Path, worktree: Path) -> None:
    for archived, staged, exact in (
        (reference / "artifacts", worktree / ".waterology-reference", True),
        (actual / "artifacts", worktree, False),
    ):
        expected = {
            path.relative_to(archived).as_posix(): file_sha256(path)
            for path in archived.rglob("*")
            if path.is_file()
        }
        if staged.is_symlink() or not staged.resolve().is_relative_to(worktree.resolve()):
            raise ValueError("Validator inputs escape the worktree")
        if exact:
            files = list(staged.rglob("*"))
            if any(p.is_symlink() for p in files) or {
                p.relative_to(staged).as_posix() for p in files if p.is_file()
            } != set(expected):
                raise ValueError("Validator reference contents changed")
        for relative, digest in expected.items():
            path = project_file(staged, relative)
            if not path.is_file() or file_sha256(path) != digest:
                raise ValueError(f"Validator input differs from archived evidence: {relative}")
