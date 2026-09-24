"""Derived run provenance using the profiles supported by roc-validator 0.11.4.

Profile requirements: https://www.researchobject.org/workflow-run-crate/profiles/0.5/
Metadata is constructed from archived evidence, never from the current project config.
"""

import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from waterology.core.atomic import write_json

VALIDATOR_VERSION = "0.11.4"
PROCESS_PROFILE = "https://w3id.org/ro/wfrun/process/0.5"
WORKFLOW_PROFILE = "https://w3id.org/ro/wfrun/workflow/0.5"
WORKFLOW_RO_PROFILE = "https://w3id.org/workflowhub/workflow-ro-crate/1.0"


def export_crate(start, run_id, destination, *, validate=True, automatic=False):
    from waterology.core.archive import ArchiveExportError, load_archive, verify_archive
    from waterology.core.project import discover_project

    project = discover_project(start)
    relative = PurePosixPath(destination)
    if (
        not destination
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in destination
        or re.match(r"^[A-Za-z]:", destination)
        or relative.as_posix() == "."
        or any(part.rstrip(" .") != part for part in relative.parts)
    ):
        raise ArchiveExportError("RO-Crate destination must be a relative project path")
    output = project.root / relative
    expected_auto = project.paths.state / "ro-crates" / run_id
    if automatic and output != expected_auto:
        raise ArchiveExportError("Invalid automatic RO-Crate destination")
    if not automatic and relative.parts[0].casefold() in {".waterology", ".git"}:
        raise ArchiveExportError("RO-Crate exports must be outside repository control state")
    current = project.root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ArchiveExportError("RO-Crate destination must not contain symlinks")
    if output.exists():
        raise ArchiveExportError(f"RO-Crate export already exists: {relative.as_posix()}")
    try:
        output.resolve().relative_to(project.root.resolve())
    except ValueError as error:
        raise ArchiveExportError("RO-Crate destination escapes the project") from error
    source = project.paths.runs / run_id
    manifest = load_archive(start, run_id)
    verification = verify_archive(source)
    if not verification.valid:
        raise ArchiveExportError(f"Archive failed verification before RO-Crate export: {run_id}")
    metadata, profile = run_metadata(source, manifest, verification)
    output.mkdir(parents=True)
    shutil.copytree(source, output / "run", symlinks=False)
    copied = verify_archive(output / "run")
    if not copied.valid or copied.seal_hash != verification.seal_hash:
        raise ArchiveExportError("RO-Crate payload changed during copying")
    write_json(output / "ro-crate-metadata.json", metadata)
    result = (
        validate_crate(output, profile)
        if validate
        else {
            "status": "skipped",
            "reason": "Validation explicitly disabled",
            "profile": profile,
        }
    )
    write_json(output / "ro-crate-validation.json", result)
    if result["status"] in {"failed", "error"}:
        raise ArchiveExportError(
            f"RO-Crate validation {result['status']}; inspect {relative}/ro-crate-validation.json"
        )
    return output


def automatic_crate(start, run_id):
    from waterology.core.archive import ArchiveExportError
    from waterology.core.project import discover_project

    project = discover_project(start)
    destination = project.paths.state / "ro-crates" / run_id
    # Never remove an earlier derived export or its diagnostics during reconciliation.
    if destination.exists() or destination.is_symlink():
        return destination
    try:
        return export_crate(
            start, run_id, destination.relative_to(project.root).as_posix(), automatic=True
        )
    except (ArchiveExportError, OSError, ValueError) as error:
        # Packaging is downstream of sealing. Preserve computation and make the failure durable.
        try:
            warning = project.paths.state / "ro-crate-errors"
            if warning.is_symlink():
                raise ValueError("RO-Crate error directory must not be a symlink")
            warning.mkdir(parents=True, exist_ok=True)
            write_json(
                warning / f"{run_id}.json",
                {
                    "run_id": run_id,
                    "status": "error",
                    "error": str(error),
                    "destination": destination.relative_to(project.root).as_posix(),
                },
            )
        except (OSError, ValueError) as warning_error:
            logging.getLogger(__name__).warning(
                "Run %s is sealed; RO-Crate export failed (%s), and its error record could not be saved (%s)",
                run_id,
                error,
                warning_error,
            )
        return destination


def _file_id(relative):
    return quote(f"run/{relative}", safe="/")


def run_metadata(source, manifest, verification):
    # Only actual archived executable definitions justify Workflow Run conformance.
    reference = manifest.executor_reference
    definition = (
        "torc-slurm-workflow.yaml"
        if reference and reference.execution_mode == "slurm"
        else "torc-workflow.yaml"
    )
    workflow_path = definition if reference and (source / definition).is_file() else None
    profiles = [PROCESS_PROFILE]
    if workflow_path:
        profiles += [WORKFLOW_PROFILE, WORKFLOW_RO_PROFILE]
    validator_profile = "workflow-run-crate-0.5" if workflow_path else "process-run-crate-0.5"
    files = [p for p in sorted(source.rglob("*")) if p.is_file()]
    parts = [{"@id": _file_id(p.relative_to(source).as_posix())} for p in files]
    root = {
        "@id": "./",
        "@type": "Dataset",
        "name": f"Waterology sealed run {manifest.run_id}",
        "description": "Archived execution evidence and derived provenance metadata.",
        "datePublished": manifest.finished_at[:10],
        "license": {"@id": "#rights"},
        "conformsTo": [{"@id": profile} for profile in profiles],
        "hasPart": parts,
        "mentions": [{"@id": "#run"}],
        "waterology:sealState": verification.seal_state,
        "waterology:sealHash": verification.seal_hash,
    }
    graph = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": "./"},
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
        },
        root,
        {
            "@id": "#rights",
            "@type": "CreativeWork",
            "name": "Rights not specified",
            "description": "No redistribution permission is granted by this export. Consult the source and data owners.",
        },
        {
            "@id": "#source-code",
            "@type": "SoftwareSourceCode",
            "name": "Evaluated source",
            "version": manifest.commit_sha,
            "hasPart": {"@id": "run/source.tar.zst"},
        },
    ]
    for profile, name in [
        (PROCESS_PROFILE, "Process Run Crate"),
        (WORKFLOW_PROFILE, "Workflow Run Crate"),
        (WORKFLOW_RO_PROFILE, "Workflow RO-Crate"),
    ]:
        if profile in profiles:
            graph.append(
                {
                    "@id": profile,
                    "@type": "CreativeWork",
                    "name": name,
                    "version": profile.rsplit("/", 1)[-1],
                }
            )
    entities = {}
    for path in files:
        relative = path.relative_to(source).as_posix()
        entity = {"@id": _file_id(relative), "@type": "File", "name": relative}
        if relative.endswith(".json"):
            entity["encodingFormat"] = "application/json"
        if relative in {"stdout.log", "stderr.log", "environment.json"}:
            entity["about"] = {"@id": "#run"}
        graph.append(entity)
        entities[relative] = entity
    metrics = json.loads((source / "metrics.json").read_text())
    snapshot = source / "execution-config.json"
    workflow = None
    if snapshot.is_file():
        from waterology.core.config import ProjectConfig

        saved = ProjectConfig.model_validate(json.loads(snapshot.read_text())["config"])
        matches = [
            w
            for w in saved.workflows.values()
            if tuple(w.command or (("torc", "workflow", w.torc_file) if w.torc_file else ()))
            == manifest.command
        ]
        if len(matches) == 1:
            workflow = matches[0]
    selectors = {m.name: m.field for m in workflow.metrics} if workflow else {}
    measurements = []
    for name, value in sorted(metrics.items()):
        identifier = "#metric-" + quote(name, safe="")
        measurements.append({"@id": identifier})
        graph.append(
            {
                "@id": identifier,
                "@type": "PropertyValue",
                "name": name,
                "value": json.dumps(value) if isinstance(value, (dict, list)) else value,
                **({"propertyID": selectors[name]} if name in selectors else {}),
            }
        )
    entities["metrics.json"]["variableMeasured"] = measurements
    identities = []
    for name, digest in workflow.input_files.items() if workflow else []:
        identifier = "#input-identity-" + quote(name, safe="")
        identities.append({"@id": identifier})
        graph.append(
            {
                "@id": identifier,
                "@type": "PropertyValue",
                "name": name,
                "propertyID": "sha256",
                "value": digest,
                "description": "Declared input identity; input bytes are not implied to be included.",
            }
        )
    instrument = "#tool"
    if workflow_path:
        instrument = _file_id(workflow_path)
        root["mainEntity"] = {"@id": instrument}
        entities[workflow_path].update(
            {
                "@type": ["File", "SoftwareSourceCode", "ComputationalWorkflow"],
                "programmingLanguage": {"@id": "#torc-language"},
            }
        )
        graph.append(
            {
                "@id": "#torc-language",
                "@type": "ComputerLanguage",
                "name": "TORC YAML",
            }
        )
    else:
        graph.append(
            {
                "@id": "#tool",
                "@type": "SoftwareApplication",
                "name": manifest.command[0],
                "subjectOf": {"@id": "#source-code"},
            }
        )
    graph.append(
        {
            "@id": "#run",
            "@type": "CreateAction",
            "name": f"Waterology run {manifest.run_id}",
            "description": json.dumps(list(manifest.command)),
            "instrument": {"@id": instrument},
            "waterology:inputIdentities": identities,
            "object": [{"@id": "run/source.tar.zst"}],
            "result": [{"@id": _file_id(f"artifacts/{p}")} for p in manifest.collected_artifacts]
            + [{"@id": "run/metrics.json"}],
            "startTime": manifest.started_at,
            "endTime": manifest.finished_at,
            "actionStatus": {
                "@id": "http://schema.org/CompletedActionStatus"
                if manifest.terminal_state == "completed"
                else "http://schema.org/FailedActionStatus"
            },
        }
    )
    return {
        "@context": [
            "https://w3id.org/ro/crate/1.1/context",
            "https://w3id.org/ro/terms/workflow-run/context",
            {"waterology": "https://waterology.dev/terms#"},
        ],
        "@graph": graph,
    }, validator_profile


def validate_crate(crate: Path, profile: str):
    command = shutil.which("rocrate-validator")
    result = {"profile": profile, "severity": "required", "validator_version": VALIDATOR_VERSION}
    if command is None:
        return {**result, "status": "skipped", "reason": "Install the rocrate extra for validation"}
    try:
        version = subprocess.run(
            [command, "--version"], capture_output=True, text=True, check=False, timeout=10
        )
        result["version_output"] = version.stdout.strip()
        if version.returncode or version.stdout.strip() != f"rocrate-validator {VALIDATOR_VERSION}":
            return {
                **result,
                "status": "error",
                "reason": "Unsupported validator version",
                "stderr": version.stderr,
            }
        args = [
            command,
            "validate",
            "--no-auto-profile",
            "--profile-identifier",
            profile,
            "--requirement-severity",
            "required",
            "--output-format",
            "json",
            "--cache-path",
            str(Path(tempfile.gettempdir()) / "waterology-rocrate-cache"),
            str(crate),
        ]
        result["command"] = args
        completed = subprocess.run(args, capture_output=True, text=True, check=False, timeout=60)
        try:
            report, _ = json.JSONDecoder().raw_decode(completed.stdout.lstrip())
            valid_report = (
                report.get("meta", {}).get("version") == VALIDATOR_VERSION
                and report.get("validation_settings", {}).get("profile_identifier") == profile
                and report.get("passed") is True
            )
        except (ValueError, AttributeError):
            valid_report = False
        return {
            **result,
            "status": "passed" if completed.returncode == 0 and valid_report else "failed",
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as error:
        return {
            **result,
            "status": "error",
            "reason": "Validator timed out",
            "stdout": _text(error.stdout),
            "stderr": _text(error.stderr),
        }
    except OSError as error:
        return {**result, "status": "error", "reason": str(error)}


def _text(value):
    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
