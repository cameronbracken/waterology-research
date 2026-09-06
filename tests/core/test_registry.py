import subprocess
from pathlib import Path

import pytest

from waterology.core.config import WorkflowConfig, load_project_config
from waterology.core.project import initialize_project
from waterology.core.registry import (
    discover_configuration,
    refresh_configuration,
    register_workflow,
)


def project(path):
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    initialize_project(path)
    return path


def test_discover_pixi_and_refresh_preserves_manual_values(tmp_path: Path):
    root = project(tmp_path)
    (root / "pixi.toml").write_text('[tasks]\nevaluate = "python model.py"\n')
    (root / "pixi.lock").write_text("version: 6\n")
    proposal = discover_configuration(root)
    assert proposal["workflows"]["evaluate"]["command"] == ["pixi", "run", "--locked", "evaluate"]
    refresh_configuration(root)
    path = root / "waterology.toml"
    path.write_text(
        "# researcher comment\n" + path.read_text().replace("max_runs = 1", "max_runs = 3")
    )
    before = path.read_text()
    assert refresh_configuration(root)["changed"] is False
    assert path.read_text() == before
    assert load_project_config(path).concurrency.max_runs == 3


def test_registration_is_idempotent_and_rejects_conflicts(tmp_path: Path):
    root = project(tmp_path)
    workflow = WorkflowConfig(command=("pixi", "run", "evaluate"))
    register_workflow(root, "evaluate", workflow)
    register_workflow(root, "evaluate", workflow)
    with pytest.raises(ValueError, match="already registered"):
        register_workflow(root, "evaluate", WorkflowConfig(command=("false",)))


def test_refresh_check_does_not_mutate(tmp_path: Path):
    root = project(tmp_path)
    (root / "pixi.toml").write_text('[tasks]\ntest = "pytest"\n')
    before = (root / "waterology.toml").read_bytes()
    assert refresh_configuration(root, check=True)["changed"]
    assert (root / "waterology.toml").read_bytes() == before


def test_equivalent_manual_registration(tmp_path):
    root = project(tmp_path)
    path = root / "waterology.toml"
    path.write_text(
        path.read_text() + '\n[workflows.evaluate]\ncommand=["pixi", "run", "evaluate"]\n'
    )
    assert (
        register_workflow(root, "evaluate", WorkflowConfig(command=("pixi", "run", "evaluate")))[
            "changed"
        ]
        is False
    )


def test_parallel_registration_does_not_lose_entries(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    root = project(tmp_path)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(
            pool.map(
                lambda name: register_workflow(root, name, WorkflowConfig(command=("echo", name))),
                ["a", "b", "c"],
            )
        )
    assert all(result["changed"] for result in results)
    assert set(load_project_config(root / "waterology.toml").workflows) == {"a", "b", "c"}


def test_root_output_has_artifact_root_and_is_not_created_as_directory(tmp_path):
    root = project(tmp_path)
    (root / "pixi.toml").write_text(
        '[tasks]\nevaluate={cmd="python model.py",outputs=["result.json"]}\n'
    )
    refresh_configuration(root)
    assert "result.json" in load_project_config(root / "waterology.toml").artifact_roots
    initialize_project(root)
    assert not (root / "result.json").exists()


def test_uv_rv_environment_discovery(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="mixed"\n')
    (tmp_path / "uv.lock").write_text("version=1\n")
    (tmp_path / "rproject.toml").write_text('[project]\nname="mixed"\n')
    (tmp_path / "rv.lock").write_text("fixture\n")
    detected = discover_configuration(tmp_path)
    assert set(detected["environment_files"]) == {
        "pyproject.toml",
        "uv.lock",
        "rproject.toml",
        "rv.lock",
    }
    assert not detected["workflows"]
    assert any("Multiple" in note for note in detected["notes"])


def test_ambiguous_native_tasks_are_not_selected(tmp_path):
    (tmp_path / "pixi.toml").write_text('[tasks]\nevaluate="python evaluate.py"\n')
    (tmp_path / "workflows").mkdir()
    (tmp_path / "workflows/evaluate.yaml").write_text("""jobs:
  - name: evaluate
    command: echo evaluation
""")
    detected = discover_configuration(tmp_path)
    assert "evaluate" not in detected["workflows"]
    assert any("Ambiguous" in note for note in detected["notes"])


def test_removed_discovered_workflow_is_blocked(tmp_path):
    from waterology.core.registry import resolve_workflow

    root = project(tmp_path)
    (root / "pixi.toml").write_text('[tasks]\nevaluate="echo evaluation"\n')
    refresh_configuration(root)
    (root / "pixi.toml").write_text('[tasks]\nother="echo other"\n')
    with pytest.raises(ValueError, match="changed or became ambiguous"):
        resolve_workflow(root, "evaluate")
