import shlex
from pathlib import Path

import yaml

from waterology.core.config import ProjectConfig, ResourceConfig
from waterology.torc.workflow import TorcWorkflowRequest, render_workflow


def test_render_workflow_is_stable_and_quotes_fixed_command(tmp_path: Path) -> None:
    config = ProjectConfig(
        name="flood-study",
        command=("python", "run model.py", "--label", "wet year's case"),
        outputs=("artifacts/metrics.json",),
        resources=ResourceConfig(cpus=4, memory_mb=8192, walltime_minutes=90, gpus=1),
    )
    request = TorcWorkflowRequest(
        run_id="run-trial",
        experiment_id="exp-trial",
        commit_sha="a" * 40,
        mode="slurm",
        torc_profile="eagle",
    )

    first = render_workflow(config, request)
    second = render_workflow(config, request)
    document = yaml.safe_load(first)

    assert first == second
    assert document["name"] == "waterology-run-trial"
    assert document["metadata"]["waterology_commit"] == "a" * 40
    assert document["execution_config"]["mode"] == "slurm"
    assert document["resource_monitor"] == {
        "sample_interval_seconds": 5,
        "jobs": {"enabled": True, "granularity": "time_series"},
    }
    assert document["jobs"][0]["command"] == (
        f'cd "$TORC_WORKFLOW_SUBMISSION_DIR" && exec {shlex.join(config.command)}'
    )
    assert document["resource_requirements"] == [
        {
            "name": "waterology-resources",
            "num_cpus": 4,
            "num_gpus": 1,
            "memory": "8192m",
            "runtime": "PT90M",
        }
    ]
    assert document["jobs"][0]["resource_requirements"] == "waterology-resources"
    assert document["metadata"]["waterology_declared_outputs"] == ["artifacts/metrics.json"]
    assert "metadata" not in document["jobs"][0]


def test_write_workflow_uses_atomic_destination(tmp_path: Path) -> None:
    from waterology.torc.workflow import write_workflow

    config = ProjectConfig(name="study", command=("python", "run.py"))
    request = TorcWorkflowRequest(
        run_id="run-one",
        experiment_id="exp-one",
        commit_sha="b" * 40,
        mode="local",
    )

    record = write_workflow(tmp_path / "workflow.yaml", config, request)

    assert record.path == tmp_path / "workflow.yaml"
    assert len(record.sha256) == 64
    assert yaml.safe_load(record.path.read_text(encoding="utf-8"))["name"] == ("waterology-run-one")
    assert yaml.safe_load(record.path.read_text(encoding="utf-8"))["execution_config"] == {
        "mode": "direct"
    }
    document = yaml.safe_load(record.path.read_text(encoding="utf-8"))
    assert "resource_requirements" not in document
    assert "resource_requirements" not in document["jobs"][0]


def test_render_workflow_uses_cmd_quoting_for_windows_targets() -> None:
    config = ProjectConfig(name="study", command=("python", "run model.py", "label value"))
    request = TorcWorkflowRequest(
        run_id="run-windows",
        experiment_id="exp-windows",
        commit_sha="c" * 40,
        mode="local",
        target_shell="windows",
    )

    document = yaml.safe_load(render_workflow(config, request))

    assert document["jobs"][0]["command"] == (
        'cd /d "%TORC_WORKFLOW_SUBMISSION_DIR%" && python "run model.py" "label value"'
    )
