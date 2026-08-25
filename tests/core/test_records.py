import json

import pytest
from pydantic import ValidationError

from waterology.core.records import AgentAttemptRecord, ExecutorReference, RunManifest


def _manifest_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "run-one",
        "project_id": "study",
        "experiment_id": "exp-one",
        "commit_sha": "a" * 40,
        "command": ["python", "run.py"],
        "started_at": "2026-08-25T00:00:00Z",
        "finished_at": "2026-08-25T00:01:00Z",
        "terminal_state": "completed",
        "exit_code": 0,
        "declared_artifacts": [],
        "collected_artifacts": [],
        "missing_artifacts": [],
    }


def test_slice_three_manifest_remains_valid() -> None:
    manifest = RunManifest.model_validate(_manifest_payload())

    assert manifest.executor == "direct"
    assert manifest.executor_reference is None


def test_torc_manifest_records_managed_executor_reference() -> None:
    payload = _manifest_payload()
    payload.update(
        {
            "executor": "torc",
            "executor_reference": {
                "provider": "torc",
                "compute_profile": "cluster",
                "api_url": "http://localhost:8085/torc-service/v1",
                "execution_mode": "slurm",
                "workflow_id": "42",
                "job_ids": ["8"],
                "torc_version": "torc 0.39.0",
            },
        }
    )

    manifest = RunManifest.model_validate_json(json.dumps(payload))

    assert manifest.executor_reference == ExecutorReference(
        provider="torc",
        compute_profile="cluster",
        api_url="http://localhost:8085/torc-service/v1",
        execution_mode="slurm",
        workflow_id="42",
        job_ids=("8",),
        torc_version="torc 0.39.0",
    )


def test_agent_attempt_rejects_nonportable_log_paths() -> None:
    with pytest.raises(ValidationError, match="relative project paths"):
        AgentAttemptRecord(
            number=1,
            state="running",
            prompt_path=".waterology/sessions/session-1111111111111111/attempt-001/prompt.md",
            events_path="../outside.jsonl",
            stderr_path=".waterology/sessions/session-1111111111111111/attempt-001/stderr.log",
            initial_commit="a" * 40,
        )
