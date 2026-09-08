"""Explicit recovery of a rejected create, called only by the study controller."""

import hashlib
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from waterology.core.atomic import write_json
from waterology.core.database import open_database
from waterology.core.execution import _transition, prepare_run_inputs
from waterology.core.experiments import load_worktree
from waterology.core.profiles import load_machine_config, machine_config_path
from waterology.core.project import discover_project
from waterology.torc.gateway import TorcCliGateway
from waterology.torc.provider import TorcProvider
from waterology.torc.runs import (
    _managed_run_row,
    _prepared_from_row,
    _record_reference,
    _redact_text,
    _utc_now,
    _write_torc_metadata,
)
from waterology.torc.study_snapshot import load_snapshot, output_signatures
from waterology.torc.workflow import TorcWorkflowFile, TorcWorkflowRequest, write_workflow


def retry_rejected_submission(start, study, attempt, *, gateway=None):
    """Caller holds the project lock and has checked the study and candidate."""
    from waterology.core.studies import StudyError

    project = discover_project(start)
    staging = project.paths.staging / attempt.run_id
    evidence_path = staging / "submission-recovery.json"
    if evidence_path.exists() or evidence_path.is_symlink():
        raise StudyError("Submission recovery already attempted; reconcile before further action")
    metadata_path = staging / "torc.json"
    if metadata_path.is_symlink():
        raise StudyError("Submission metadata must not be a symlink")
    metadata = json.loads(metadata_path.read_text())
    # Recognize the TORC create endpoint's typed rejection, never a bare status
    # number in arbitrary logs or a failure after a workflow was created.
    error = metadata.get("error") or ""
    if (
        metadata.get("state") != "unknown"
        or metadata.get("executor_reference") is not None
        or not re.fullmatch(
            r"Error creating workflow from spec: Failed to create workflow: "
            r"ResponseError\(ResponseContent \{ status: (?:401|403), "
            r'content: "(?:Unauthorized|Forbidden)", entity: None \}\)',
            error,
        )
    ):
        raise StudyError("Saved submission is not a definitive create authorization rejection")
    snapshot = load_snapshot(staging)
    if snapshot is None:
        raise StudyError("Submission recovery requires the original execution snapshot")
    config, profile = snapshot
    current_inputs = prepare_run_inputs(start, attempt.experiment_id)
    current_profile = load_machine_config(machine_config_path()).profile(study.profile)
    if (
        config != current_inputs.config
        or profile.model_dump(exclude={"trusted"})
        != current_profile.model_dump(exclude={"trusted"})
        or metadata.get("profile") != study.profile
    ):
        raise StudyError(
            "Saved execution configuration or profile differs from the authorized candidate"
        )
    context = json.loads((staging / "study.json").read_text())
    if any(
        context.get(key) != value
        for key, value in {
            "study_id": study.id,
            "contract_hash": study.contract_hash,
            "execution_hash": study.execution_hash,
            "evaluation_hash": study.evaluation_hash,
        }.items()
    ):
        raise StudyError("Saved run belongs to a different study contract")
    if profile.mode == "slurm":
        raise StudyError("Slurm submission recovery is not supported")
    worktree = Path(load_worktree(project.root, attempt.experiment_id).path)
    saved = json.loads((staging / "execution-config.json").read_text())
    if saved["commit_sha"] != attempt.commit_sha:
        raise StudyError("Saved execution commit differs from the study attempt")
    if output_signatures(worktree, config) != saved["outputs_before"]:
        raise StudyError("Outputs changed since submission; reconcile before retry")
    request = TorcWorkflowRequest(
        run_id=attempt.run_id,
        experiment_id=attempt.experiment_id,
        commit_sha=attempt.commit_sha,
        mode=profile.mode,
        target_shell=profile.target_shell,
        torc_profile=profile.torc_profile,
    )
    workflow = staging / "torc-workflow.yaml"
    if workflow.is_symlink():
        raise StudyError("Saved workflow must not be a symlink")
    original = workflow.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        regenerated = write_workflow(
            Path(directory) / "workflow.yaml", config, request, worktree=worktree
        )
        if regenerated.path.read_bytes() != original:
            raise StudyError("Saved workflow differs from the committed execution snapshot")
    selected_gateway = gateway or TorcCliGateway(profile.api_url)
    with open_database(project.paths.database) as database:
        row = _managed_run_row(database, attempt.run_id)
        if (
            row["workflow_id"] is not None
            or row["operational_state"] != "unknown"
            or row["experiment_id"] != attempt.experiment_id
            or row["commit_sha"] != attempt.commit_sha
            or row["compute_profile"] != study.profile
        ):
            raise StudyError("Run identity or submission state is not eligible for recovery")
        inventory = selected_gateway.workflow_inventory(cwd=worktree)
        items = inventory.get("items")
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise StudyError("TORC inventory is incomplete or malformed")
        for item in items:
            if not isinstance(item.get("id"), (int, str)):
                raise StudyError("TORC inventory contains an unidentified workflow")
            workflow_metadata = item.get("metadata") or {}
            if not isinstance(workflow_metadata, dict):
                raise StudyError("TORC inventory metadata is malformed")
            if (
                workflow_metadata.get("waterology_run_id") == attempt.run_id
                or item.get("name") == f"waterology-{attempt.run_id}"
            ):
                raise StudyError(
                    "TORC already contains this run; reconcile its identity before retry"
                )
        provider = TorcProvider(
            config=config,
            request=request,
            profile_name=study.profile,
            profile=profile,
            worktree=worktree,
            staging=staging,
            gateway=selected_gateway,
        )
        provider.workflow_file = TorcWorkflowFile(workflow, hashlib.sha256(original).hexdigest())
        selected_gateway.validate(workflow, cwd=worktree)
        from waterology.core.studies import _stop_path

        if (
            _stop_path(start, study.id).exists()
            or (datetime.now(UTC) - datetime.fromisoformat(study.authorized_at)).total_seconds()
            >= study.contract.max_seconds
        ):
            raise StudyError("Study stopped or expired during recovery preflight")
        # The durable marker precedes any launch. A crash from here onward is
        # ambiguous and must never allow this explicit recovery to replay.
        evidence = {
            "state": "launching",
            "recorded_at": _utc_now(),
            "api_url": profile.api_url,
            "run_id": attempt.run_id,
            "original_torc_metadata": metadata,
            "inventory": inventory,
            "workflow_sha256": provider.workflow_file.sha256,
        }
        write_json(evidence_path, evidence)
        intent = database.append_intent(
            kind="run.submission_recovery",
            entity_type="run",
            entity_id=attempt.run_id,
            payload={
                "evidence": str(evidence_path),
                "workflow_sha256": provider.workflow_file.sha256,
            },
        )
        try:
            launched = provider.launch(_prepared_from_row(staging, worktree, row))
            if launched.reference is None:
                raise RuntimeError("TORC recovery returned no reference")
        except Exception as failure:
            message = _redact_text(str(failure), config.archive.log_redactions)
            if provider.reference is not None:
                _record_reference(
                    database, attempt.run_id, provider.reference, _utc_now(), process_id=None
                )
            _write_torc_metadata(
                staging,
                state="unknown",
                profile_name=study.profile,
                reference=provider.reference,
                error=message,
            )
            database.append_observation(intent.id, payload={"outcome": "unknown", "error": message})
            raise StudyError(
                "Recovery submission unresolved; inspect saved identity before further action"
            ) from failure
        _record_reference(
            database, attempt.run_id, launched.reference, _utc_now(), process_id=launched.process_id
        )
        _write_torc_metadata(
            staging, state="running", profile_name=study.profile, reference=launched.reference
        )
        _transition(database, attempt.run_id, "unknown", "running")
        database.append_observation(
            intent.id, payload={"outcome": "started", "workflow_id": launched.reference.workflow_id}
        )
        return launched.reference
