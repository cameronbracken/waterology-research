import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from waterology.core.config import (
    DeliverableConfig,
    ProjectConfig,
    WorkflowConfig,
    project_config_toml,
)
from waterology.core.project import initialize_project
from waterology.core.reproduction import (
    export_deliverable,
    register_deliverable,
    reproduce_deliverable,
)
from waterology.core.workflows import run_workflow, watch_workflow
from waterology.torc.gateway import TorcLaunchRecord, TorcWorkflowObservation


class LocalFixtureGateway:
    def validate(self, workflow, *, cwd):
        assert yaml.safe_load(workflow.read_text())["jobs"]

    def version(self, *, cwd):
        return "torc test fixture"

    def launch(self, workflow, **kwargs):
        import os

        self.worktree = kwargs["cwd"]
        output = kwargs["output_dir"]
        output.mkdir(parents=True, exist_ok=True)
        for i, job in enumerate(yaml.safe_load(workflow.read_text())["jobs"]):
            completed = subprocess.run(
                job["command"],
                capture_output=True,
                text=True,
                shell=True,
                cwd=self.worktree,
                check=True,
                env={**os.environ, "TORC_WORKFLOW_SUBMISSION_DIR": str(self.worktree)},
            )
            (output / f"job_{i}.stdout.log").write_text(completed.stdout)
        return TorcLaunchRecord("42", ("1", "2"))

    def inspect(self, workflow_id, *, cwd):
        return TorcWorkflowObservation(workflow_id, "completed", ({"exit_code": 0},), {})

    def results(self, workflow_id, *, cwd):
        return {"jobs": [{"id": "1", "return_code": 0}, {"id": "2", "return_code": 0}]}


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.org")
    initialize_project(root)
    (root / ".gitignore").write_text(".waterology/\nresults/\n")
    (root / "environment.lock").write_text("fixture-v1\n")
    (root / "model.py").write_text(
        'from pathlib import Path\nPath("results").mkdir(exist_ok=True)\nPath("results/value.json").write_text(\'{"value": 2.0}\')\n'
    )
    config = ProjectConfig(
        name="fixture",
        artifact_roots=("results",),
        default_compute_profile="local",
        workflows={
            "simulate": WorkflowConfig(
                command=(sys.executable, "model.py"),
                outputs=("results/value.json",),
                environment_files=("environment.lock",),
                restore=((sys.executable, "-c", 'print("restore fixture")'),),
                environment_probe=(sys.executable, "--version"),
            )
        },
    )
    (root / "waterology.toml").write_text(project_config_toml(config))
    git(root, "add", ".")
    git(root, "-c", "commit.gpgsign=false", "commit", "-m", "fixture")
    machine = tmp_path / "machine.toml"
    machine.write_text(
        '[profiles.local]\nmode="local"\napi_url="http://localhost:8080/torc-service/v1"\n'
    )
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(machine))
    return root


def test_named_baseline_and_export_reproduce_without_original_checkout(source, tmp_path):
    gateway = LocalFixtureGateway()
    run = run_workflow(source, "simulate", gateway=gateway)
    completed = watch_workflow(source, run.run_id, gateway=gateway)
    assert completed.terminal_state == "completed"
    register_deliverable(
        source,
        "final",
        DeliverableConfig(
            workflow="simulate",
            reference_run=run.run_id,
            checks=(
                {"path": "results/value.json", "mode": "numeric", "field": "value", "atol": 0.01},
            ),
        ),
    )
    bundle = tmp_path / "export"
    export_deliverable(source, "final", bundle)
    source.rename(tmp_path / "unavailable-original")
    result = reproduce_deliverable(
        bundle, "final", tmp_path / "rerun", bundle=True, profile="local", gateway=gateway
    )
    assert result["state"] == "passed", result
    assert result["run_id"] != run.run_id
    assert json.loads((tmp_path / "rerun/reproduction.json").read_text())["checks"][0]["passed"]


def test_tampered_bundle_is_rejected(source, tmp_path):
    gateway = LocalFixtureGateway()
    run = run_workflow(source, "simulate", gateway=gateway)
    watch_workflow(source, run.run_id, gateway=gateway)
    register_deliverable(
        source,
        "final",
        DeliverableConfig(
            workflow="simulate", reference_run=run.run_id, checks=({"path": "results/value.json"},)
        ),
    )
    bundle = tmp_path / "export"
    export_deliverable(source, "final", bundle)
    (bundle / "reference/artifacts/results/value.json").write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        reproduce_deliverable(bundle, "final", tmp_path / "rerun", bundle=True, gateway=gateway)


def select_final(source, *, checks=None):
    gateway = LocalFixtureGateway()
    run = run_workflow(source, "simulate", gateway=gateway)
    watch_workflow(source, run.run_id, gateway=gateway)
    register_deliverable(
        source,
        "final",
        DeliverableConfig(
            workflow="simulate",
            reference_run=run.run_id,
            checks=checks or ({"path": "results/value.json", "mode": "numeric", "field": "value"},),
        ),
    )
    return gateway


def test_statistical_validator_uses_fresh_output_and_reference(source, tmp_path):
    from waterology.core.config import load_project_config

    config = load_project_config(source / "waterology.toml")
    validator = WorkflowConfig(command=(sys.executable, "validate.py"))
    config = config.model_copy(update={"workflows": {**config.workflows, "validate": validator}})
    (source / "waterology.toml").write_text(project_config_toml(config))
    (source / "validate.py").write_text(
        'from pathlib import Path\nassert Path("results/value.json").read_bytes() == Path(".waterology-reference/results/value.json").read_bytes()\n'
    )
    git(source, "add", ".")
    git(source, "-c", "commit.gpgsign=false", "commit", "-m", "Add statistical validator fixture")
    gateway = select_final(
        source,
        checks=({"path": "results/value.json", "mode": "statistical", "validator": "validate"},),
    )
    result = reproduce_deliverable(
        source, "final", tmp_path / "reproduction", profile="local", gateway=gateway
    )
    assert result["state"] == "passed", result
    assert result["validator_runs"]["validate"] != result["run_id"]


def test_preflight_failure_can_resume_same_unsubmitted_id(source, tmp_path):
    import os

    gateway = select_final(source)
    destination = tmp_path / "reproduction"
    blocked = reproduce_deliverable(source, "final", destination, profile="later", gateway=gateway)
    assert blocked["state"] == "blocked"
    assert blocked["run_id"]
    machine = Path(os.environ["WATEROLOGY_CONFIG"])
    machine.write_text(machine.read_text().replace("profiles.local", "profiles.later"))
    resumed = reproduce_deliverable(source, "final", destination, resume=True, gateway=gateway)
    assert resumed["state"] == "passed", resumed
    assert resumed["run_id"] == blocked["run_id"]


@pytest.mark.parametrize("changed_file", ["model.py", "environment.lock", "waterology.toml"])
def test_resume_rejects_committed_source_change(source, tmp_path, changed_file):
    from waterology.core.experiments import load_worktree

    gateway = select_final(source)
    destination = tmp_path / "reproduction"
    blocked = reproduce_deliverable(
        source, "final", destination, profile="missing", gateway=gateway
    )
    worktree = Path(load_worktree(destination / "project", blocked["experiment_id"]).path)
    (worktree / changed_file).write_text(
        (worktree / changed_file).read_text() + "\n# changed source\n"
    )
    git(worktree, "add", ".")
    git(
        worktree,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.org",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "Altered reproduction",
    )
    result = reproduce_deliverable(source, "final", destination, resume=True, gateway=gateway)
    assert result["state"] == "blocked"
    assert "source changed" in result["reason"]


def test_numerical_disagreement_fails(source, tmp_path):
    select_final(source)

    class ChangedGateway(LocalFixtureGateway):
        def launch(self, workflow, **kwargs):
            result = super().launch(workflow, **kwargs)
            (self.worktree / "results/value.json").write_text('{"value": 3.0}')
            return result

    result = reproduce_deliverable(
        source, "final", tmp_path / "reproduction", profile="local", gateway=ChangedGateway()
    )
    assert result["state"] == "failed", result
    assert result["checks"][0]["passed"] is False


def test_declared_ignored_input_is_copied_and_reproduction_requires_it(source, tmp_path):
    import hashlib

    from waterology.core.config import load_project_config

    input_path = source / "input.dat"
    input_path.write_text("fixed input\n")
    with (source / ".gitignore").open("a") as stream:
        stream.write("input.dat\n")
    config = load_project_config(source / "waterology.toml")
    workflow = config.workflows["simulate"].model_copy(
        update={"input_files": {"input.dat": hashlib.sha256(input_path.read_bytes()).hexdigest()}}
    )
    config = config.model_copy(update={"workflows": {"simulate": workflow}})
    (source / "waterology.toml").write_text(project_config_toml(config))
    git(source, "add", ".")
    git(source, "-c", "commit.gpgsign=false", "commit", "-m", "Declare input")
    gateway = select_final(source)
    destination = tmp_path / "reproduction"
    blocked = reproduce_deliverable(source, "final", destination, profile="local", gateway=gateway)
    assert blocked["state"] == "blocked"
    assert "input" in blocked["reason"].lower()
    resumed = reproduce_deliverable(
        source, "final", destination, resume=True, inputs=source, gateway=gateway
    )
    assert resumed["state"] == "passed", resumed


def test_unsubmitted_resume_rejects_preexisting_output(source, tmp_path):
    from waterology.core.experiments import load_worktree

    gateway = select_final(source)
    destination = tmp_path / "reproduction"
    blocked = reproduce_deliverable(
        source, "final", destination, profile="missing", gateway=gateway
    )
    worktree = Path(load_worktree(destination / "project", blocked["experiment_id"]).path)
    (worktree / "results").mkdir()
    (worktree / "results/value.json").write_text('{"value": 2.0}')
    result = reproduce_deliverable(
        source, "final", destination, resume=True, profile="local", gateway=gateway
    )
    assert result["state"] == "blocked"
    assert "already exists" in result["reason"]


def test_failed_preparation_is_not_reported_running(source, tmp_path):
    select_final(source)

    class InvalidGateway(LocalFixtureGateway):
        def validate(self, workflow, *, cwd):
            raise ValueError("Invalid workflow fixture")

    destination = tmp_path / "reproduction"
    blocked = reproduce_deliverable(
        source, "final", destination, profile="local", gateway=InvalidGateway()
    )
    assert blocked["state"] == "failed"
    resumed = reproduce_deliverable(
        source, "final", destination, resume=True, gateway=LocalFixtureGateway()
    )
    assert resumed["state"] == "failed", resumed


def test_named_workflow_cannot_use_legacy_direct_executor(source):
    from waterology.core.execution import RunPreparationError, start_direct_run
    from waterology.core.experiments import create_experiment

    experiment = create_experiment(source, hypothesis="Named baseline", workflow="simulate")
    with pytest.raises(RunPreparationError, match="require TORC"):
        start_direct_run(source, experiment.id)


@pytest.mark.parametrize("mutated", ["reference", "actual"])
def test_paused_statistical_validation_rejects_changed_inputs(source, tmp_path, mutated):
    from waterology.core.config import load_project_config
    from waterology.core.experiments import load_worktree

    config = load_project_config(source / "waterology.toml")
    validator = WorkflowConfig(command=(sys.executable, "validate.py"))
    config = config.model_copy(update={"workflows": {**config.workflows, "validate": validator}})
    (source / "waterology.toml").write_text(project_config_toml(config))
    (source / "validate.py").write_text(
        'from pathlib import Path\nassert Path("results/value.json").read_bytes() == Path(".waterology-reference/results/value.json").read_bytes()\n'
    )
    git(source, "add", ".")
    git(source, "-c", "commit.gpgsign=false", "commit", "-m", "Validator fixture")
    select_final(
        source,
        checks=({"path": "results/value.json", "mode": "statistical", "validator": "validate"},),
    )

    class PausedValidatorGateway(LocalFixtureGateway):
        validator_running = False

        def launch(self, workflow, **kwargs):
            result = super().launch(workflow, **kwargs)
            self.validator_running = "validate.py" in workflow.read_text()
            return result

        def inspect(self, workflow_id, *, cwd):
            if self.validator_running:
                return TorcWorkflowObservation(workflow_id, "running", (), {})
            return super().inspect(workflow_id, cwd=cwd)

    destination = tmp_path / "reproduction"
    gateway = PausedValidatorGateway()
    running = reproduce_deliverable(
        source, "final", destination, profile="local", gateway=gateway, wait=False
    )
    assert running["state"] == "validating", running
    worktree = Path(load_worktree(destination / "project", running["experiment_id"]).path)
    root = worktree / ".waterology-reference" if mutated == "reference" else worktree
    (root / "results/value.json").write_text('{"value": 3}')
    result = reproduce_deliverable(
        source, "final", destination, resume=True, gateway=gateway, wait=False
    )
    assert result["state"] == "blocked", result
    assert "differs from archived evidence" in result["reason"]
