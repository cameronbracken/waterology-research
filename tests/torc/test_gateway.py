import json
import subprocess
from pathlib import Path

import pytest

from waterology.torc.gateway import (
    TorcCliGateway,
    TorcCommandError,
    TorcIncompatibleVersionError,
    TorcPartialLaunchError,
    TorcUnavailableError,
    TorcWorkflowNotFoundError,
)


def test_cli_gateway_creates_workflow_with_json_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[list[str], Path, dict[str, str]]] = []

    def fake_run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((arguments, kwargs["cwd"], kwargs["env"]))  # type: ignore[arg-type]
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout=json.dumps({"workflow": {"id": "workflow-12"}, "jobs": [{"id": "job-7"}]}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text("name: test\n", encoding="utf-8")
    gateway = TorcCliGateway("http://localhost:8080/torc-service/v1", executable="torc")

    result = gateway.create(workflow, cwd=tmp_path)

    assert result.workflow_id == "workflow-12"
    assert result.job_ids == ("job-7",)
    assert calls[0][0] == ["torc", "--format", "json", "create", str(workflow)]
    assert calls[0][1] == tmp_path
    assert calls[0][2]["TORC_CLIENT__API_URL"] == "http://localhost:8080/torc-service/v1"


def test_cli_gateway_reports_missing_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def missing(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("torc")

    monkeypatch.setattr(subprocess, "run", missing)

    with pytest.raises(TorcUnavailableError, match="TORC executable"):
        TorcCliGateway("http://localhost:8080").version(cwd=tmp_path)


@pytest.mark.parametrize("version", ["torc 0.39.0", "unknown"])
def test_cli_gateway_rejects_incompatible_or_unparseable_versions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, version: str
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout=version, stderr=""),
    )

    with pytest.raises(TorcIncompatibleVersionError):
        TorcCliGateway("http://localhost:8080").version(cwd=tmp_path)


def test_cli_gateway_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="not-json", stderr=""
        ),
    )

    with pytest.raises(TorcCommandError, match="invalid JSON"):
        TorcCliGateway("http://localhost:8080").inspect("workflow-1", cwd=tmp_path)


def test_cli_gateway_preserves_created_reference_when_local_runner_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            0,
            stdout=json.dumps({"workflow": {"id": "17"}, "jobs": [{"id": "19"}]}),
            stderr="",
        ),
    )
    monkeypatch.setattr(
        subprocess, "Popen", lambda *args, **kwargs: (_ for _ in ()).throw(OSError())
    )
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text("name: test\n", encoding="utf-8")

    with pytest.raises(TorcPartialLaunchError) as captured:
        TorcCliGateway("http://localhost:8080").launch(
            workflow,
            mode="local",
            ssh_alias=None,
            torc_profile=None,
            slurm_account=None,
            output_dir=tmp_path / "output",
            cwd=tmp_path,
        )

    assert captured.value.record.workflow_id == "17"
    assert captured.value.record.job_ids == ("19",)


def test_cli_gateway_maps_official_status_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "workflow_id": 42,
        "jobs_by_status": {
            "uninitialized": 0,
            "blocked": 0,
            "ready": 0,
            "pending": 0,
            "running": 0,
            "completed": 3,
            "failed": 0,
            "canceled": 0,
            "terminated": 0,
            "disabled": 0,
        },
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout=json.dumps(payload), stderr=""
        ),
    )

    observation = TorcCliGateway("http://localhost:8080").inspect("42", cwd=tmp_path)

    assert observation.workflow_id == "42"
    assert observation.state == "completed"


@pytest.mark.parametrize(
    ("torc_state", "expected"),
    [("terminated", "failed"), ("disabled", "completed")],
)
def test_cli_gateway_maps_terminal_status_counts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    torc_state: str,
    expected: str,
) -> None:
    payload = {"workflow_id": 42, "jobs_by_status": {torc_state: 1}}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout=json.dumps(payload), stderr=""
        ),
    )

    assert TorcCliGateway("http://localhost:8080").inspect("42", cwd=tmp_path).state == expected


@pytest.mark.parametrize(
    "counts",
    [
        {"pending_failed": 1},
        {"future_state": 1},
        {"completed": 1, "pending_failed": 1},
        {"completed": 1, "future_state": 1},
    ],
)
def test_cli_gateway_preserves_unknown_status_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, counts: dict[str, int]
) -> None:
    payload = {"workflow_id": 42, "jobs_by_status": counts}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout=json.dumps(payload), stderr=""
        ),
    )

    observation = TorcCliGateway("http://localhost:8080").inspect("42", cwd=tmp_path)

    assert observation.state == "unknown"


def test_cli_gateway_collects_remote_logs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(arguments, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    TorcCliGateway("http://localhost:8080").collect_logs("42", tmp_path / "logs", cwd=tmp_path)

    assert calls == [
        [
            "torc",
            "remote",
            "collect-logs",
            "42",
            "--local-output-dir",
            str(tmp_path / "logs"),
        ]
    ]


def test_cli_gateway_cancels_without_an_interactive_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def fake_run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout=json.dumps({"workflow_id": 42, "status": "success"}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    TorcCliGateway("http://localhost:8080").cancel("42", cwd=tmp_path)

    assert calls == [["torc", "--format", "json", "cancel", "42", "--no-prompts"]]


def test_cli_gateway_rejects_partial_cancellation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            0,
            stdout=json.dumps({"status": "partial_success", "errors": ["allocation 7"]}),
            stderr="",
        ),
    )

    with pytest.raises(TorcCommandError, match="not completed"):
        TorcCliGateway("http://localhost:8080").cancel("42", cwd=tmp_path)


def test_cli_gateway_does_not_infer_lost_from_unrelated_not_found_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="", stderr="Configuration file not found"
        ),
    )

    with pytest.raises(TorcCommandError) as captured:
        TorcCliGateway("http://localhost:8080").inspect("42", cwd=tmp_path)

    assert captured.type is TorcCommandError


def test_cli_gateway_confirms_missing_workflow_from_status_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="", stderr="HTTP 404: Workflow 42 not found"
        ),
    )

    with pytest.raises(TorcWorkflowNotFoundError):
        TorcCliGateway("http://localhost:8080").inspect("42", cwd=tmp_path)


@pytest.mark.parametrize(
    ("mode", "ssh_alias", "expected"),
    [
        ("local", None, ["run"]),
        ("slurm", None, ["submit"]),
        ("remote", "worker-a", ["remote", "run", "17"]),
    ],
)
def test_cli_gateway_launches_each_supported_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
    ssh_alias: str | None,
    expected: list[str],
) -> None:
    calls: list[list[str]] = []
    spawned: list[list[str]] = []

    def fake_run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        if "create" in arguments:
            payload = {"workflow": {"id": "17"}, "jobs": [{"id": "19"}]}
        else:
            payload = {"workflow": {"id": "17"}, "jobs": [{"id": "19"}]}
        return subprocess.CompletedProcess(arguments, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    class FakeProcess:
        pid = 314

    def fake_popen(arguments: list[str], **kwargs: object) -> FakeProcess:
        spawned.append(arguments)
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text("name: test\n", encoding="utf-8")
    gateway = TorcCliGateway("http://localhost:8080")

    result = gateway.launch(
        workflow,
        mode=mode,  # type: ignore[arg-type]
        ssh_alias=ssh_alias,
        torc_profile="kestrel" if mode == "slurm" else None,
        slurm_account="project-123" if mode == "slurm" else None,
        access_group_id=2 if mode == "remote" else None,
        output_dir=tmp_path / "output",
        cwd=tmp_path,
    )

    assert result.workflow_id == "17"
    inspected_call = spawned[-1] if mode == "local" else calls[-1]
    assert (
        expected
        == [part for part in inspected_call if part not in {"torc", "--format", "json"}][
            : len(expected)
        ]
    )
    if mode == "local":
        assert result.process_id == 314
        assert inspected_call[:3] == ["torc", "run", "17"]
    if mode == "slurm":
        assert str(tmp_path / "torc-slurm-workflow.yaml") in calls[-1]
        assert calls[-1][-3:] == ["--output-dir", str(tmp_path / "output"), "--no-prompts"]
        assert calls[-2][-7:] == [
            "--profile",
            "kestrel",
            "--account",
            "project-123",
            "--output",
            str(tmp_path / "torc-slurm-workflow.yaml"),
            str(workflow),
        ]
    if mode == "remote":
        assert calls[-3] == ["torc", "access-groups", "add-workflow", "17", "2"]
        assert calls[-2] == ["torc", "remote", "add-workers", "17", "worker-a"]
        assert calls[-1] == ["torc", "remote", "run", "17"]
