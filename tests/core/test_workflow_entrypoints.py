import json
import subprocess

from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.config import (
    ProjectConfig,
    WorkflowConfig,
    load_project_config,
    project_config_toml,
)
from waterology.core.project import initialize_project


def test_cli_registration_and_schema(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "pixi.toml").write_text('[tasks]\nevaluate="echo evaluation"\n')
    runner = CliRunner()
    assert runner.invoke(app, ["init", "--path", str(tmp_path)]).exit_code == 0
    listing = runner.invoke(
        app, ["--output-format", "json", "workflow", "list", "--path", str(tmp_path)]
    )
    assert "evaluate" in json.loads(listing.stdout)
    registered = runner.invoke(
        app, ["workflow", "register", "evaluate", "--task", "evaluate", "--path", str(tmp_path)]
    )
    assert registered.exit_code == 0, registered.output
    schema = runner.invoke(app, ["--output-format", "json", "config", "schema"])
    assert "workflows" in json.loads(schema.stdout)["properties"]
    failure = runner.invoke(app, ["workflow", "run", "missing", "--path", str(tmp_path)])
    assert failure.exit_code == 1
    assert "error" in failure.stdout


def test_shared_study_creation_registers_contract_and_unchanged_baseline(tmp_path, monkeypatch):
    from waterology.core.experiments import load_experiment
    from waterology.core.workflows import create_registered_study

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    initialize_project(tmp_path)
    (tmp_path / "environment.lock").write_text("fixture\n")
    config = ProjectConfig(
        name="fixture",
        workflows={
            "evaluate": WorkflowConfig(
                command=("echo", "evaluation"), environment_files=("environment.lock",)
            )
        },
    )
    (tmp_path / "waterology.toml").write_text(project_config_toml(config))
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.org",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Fixture",
        ],
        check=True,
    )
    machine = tmp_path / "machine.toml"
    machine.write_text('[profiles.local]\nmode="local"\napi_url="http://localhost:8080"\n')
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(machine))
    contract = tmp_path / "study.nt"
    contract.write_text("""mode: engineering
objective: Meet specification
workflow: evaluate
allowed_paths:
    - model.py
evaluation:
    benchmark: fixture
acceptance:
    -
        name: error
        unit: m
        threshold: 0.1
max_iterations: 1
max_seconds: 10
""")
    record = create_registered_study(
        tmp_path, contract, profile="local", authorized_by="fixture authorization"
    )
    assert load_experiment(tmp_path, record.contract.baseline_experiment).workflow == "evaluate"
    assert load_project_config(tmp_path / "waterology.toml").study_contracts == {
        "study": "study.nt"
    }


def test_mcp_and_dashboard_expose_same_registry(tmp_path):
    import asyncio

    from starlette.testclient import TestClient

    from waterology.core.registry import register_workflow
    from waterology.dashboard.app import create_dashboard_app
    from waterology.mcp.server import create_server

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    initialize_project(tmp_path)
    register_workflow(tmp_path, "evaluate", WorkflowConfig(command=("echo", "evaluation")))
    server = create_server()
    # Registration is shared service state, visible to both interfaces.
    with TestClient(create_dashboard_app(tmp_path), base_url="http://127.0.0.1") as client:
        response = client.get("/workflows")
        assert response.status_code == 200
        assert "evaluate" in response.text
    from mcp import Client

    async def listed():
        async with Client(server, raise_exceptions=True) as client:
            return await client.list_tools()

    tools = asyncio.run(listed())
    assert {"workflow_list", "workflow_run", "deliverable_reproduce"} <= {
        tool.name for tool in tools.tools
    }
