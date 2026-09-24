import json
from pathlib import Path

import pytest
from test_archive import git, make_experiment

from waterology.core import archive


@pytest.fixture
def sealed_run(tmp_path, monkeypatch):
    root, experiment = make_experiment(tmp_path / "project")
    worktree = root / ".waterology/worktrees" / experiment
    (worktree / "artifacts").mkdir()
    (worktree / "artifacts/result.json").write_text('{"error": 0.0}\n')
    monkeypatch.setattr(archive.shutil, "which", lambda name: None)
    source = archive.build_run_archive(
        root,
        experiment_id=experiment,
        run_id="run-crate-test",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-09-24T10:00:00Z",
        finished_at="2026-09-24T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="",
        stderr="",
        metrics={"error": 0.0},
    )
    return root, source


def test_metadata_uses_archived_evidence_without_private_repository_uri(sealed_run):
    root, source = sealed_run
    crate = archive.export_run_crate(root, source.name, "exports/crate")
    metadata = json.loads((crate / "ro-crate-metadata.json").read_text())
    graph = {n["@id"]: n for n in metadata["@graph"]}
    assert "file://" not in json.dumps(metadata)
    assert graph["#run"]["instrument"]["@id"] in graph
    for name in ("manifest.json", "source.tar.zst", "metrics.json", "checksums.sha256"):
        assert (crate / "run" / name).read_bytes() == (source / name).read_bytes()
    assert graph["./"]["conformsTo"] == [{"@id": "https://w3id.org/ro/wfrun/process/0.5"}]


@pytest.mark.parametrize("destination", [".git/crate", ".waterology/crate", "../crate", "C:/crate"])
def test_export_refuses_control_state_and_nonportable_destinations(sealed_run, destination):
    root, source = sealed_run
    with pytest.raises(archive.ArchiveExportError):
        archive.export_run_crate(root, source.name, destination)


def test_export_refuses_symlink_parent(sealed_run, tmp_path):
    root, source = sealed_run
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(archive.ArchiveExportError):
        archive.export_run_crate(root, source.name, "escape/crate")
    assert not (outside / "crate").exists()


def test_rejected_validator_retains_diagnostics_and_original_seal(sealed_run, monkeypatch):
    root, source = sealed_run
    from waterology.core import rocrate

    monkeypatch.setattr(
        rocrate,
        "validate_crate",
        lambda *args: {
            "status": "failed",
            "exit_code": 1,
            "stderr": "invalid fixture",
            "stdout": "",
        },
    )
    with pytest.raises(archive.ArchiveExportError):
        archive.export_run_crate(root, source.name, "exports/rejected")
    result = json.loads((root / "exports/rejected/ro-crate-validation.json").read_text())
    assert result["status"] == "failed"
    assert result["stderr"] == "invalid fixture"
    assert archive.verify_archive(source).valid


def test_automatic_export_failure_does_not_erase_archive(sealed_run, monkeypatch):
    root, source = sealed_run
    from waterology.core import rocrate

    monkeypatch.setattr(
        rocrate,
        "export_crate",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            archive.ArchiveExportError("validator failure")
        ),
    )
    # Existing derived evidence must not be destroyed by a repeated automatic export.
    previous = root / ".waterology/ro-crates" / source.name / "ro-crate-metadata.json"
    original = previous.read_bytes()
    archive.auto_export_run_crate(root, source.name)
    assert previous.read_bytes() == original
    assert archive.verify_archive(source).valid


@pytest.mark.parametrize("native", [False, True])
def test_real_validator_accepts_export_and_rejects_broken_graph(sealed_run, monkeypatch, native):
    import os
    import shutil

    if os.environ.get("WATEROLOGY_TEST_ROCRATE") != "1":
        pytest.skip("Run in the pinned rocrate environment with WATEROLOGY_TEST_ROCRATE=1")
    from waterology.core.rocrate import validate_crate

    root, source = sealed_run
    executable = (
        Path(os.environ["CONDA_PREFIX"])
        / ("Scripts" if os.name == "nt" else "bin")
        / "rocrate-validator"
    )
    monkeypatch.setattr(shutil, "which", lambda name: str(executable))
    if native:
        (source / "torc-workflow.yaml").write_text(
            json.dumps({"name": "fixture", "jobs": [{"name": "evaluate", "command": "echo done"}]})
        )
        manifest = json.loads((source / "manifest.json").read_text())
        manifest.update(
            executor="torc",
            executor_reference={
                "provider": "torc",
                "compute_profile": "local",
                "api_url": "http://localhost:8080",
                "execution_mode": "local",
                "workflow_id": "1",
                "torc_version": "0.40.0",
            },
        )
        (source / "manifest.json").write_text(json.dumps(manifest))
        digest = archive._write_checksums(source)
        seal = json.loads((source / "seal.json").read_text())
        seal["checksums_sha256"] = digest
        (source / "seal.json").write_text(json.dumps(seal))
    crate = archive.export_run_crate(root, source.name, "exports/validated")
    result = json.loads((crate / "ro-crate-validation.json").read_text())
    assert result["status"] == "passed", result
    metadata_path = crate / "ro-crate-metadata.json"
    data = json.loads(metadata_path.read_text())
    data["@graph"] = [node for node in data["@graph"] if node["@id"] != "./"]
    metadata_path.write_text(json.dumps(data))
    invalid = validate_crate(crate, result["profile"])
    assert invalid["status"] == "failed", invalid


def test_automatic_error_record_failure_does_not_invalidate_execution(
    sealed_run, monkeypatch, caplog
):
    import shutil

    from waterology.core import rocrate

    root, source = sealed_run
    shutil.rmtree(root / ".waterology/ro-crates" / source.name)

    def fail(*args, **kwargs):
        raise OSError("fixture disk full")

    monkeypatch.setattr(rocrate, "export_crate", fail)
    monkeypatch.setattr(rocrate, "write_json", fail)
    archive.auto_export_run_crate(root, source.name)
    assert archive.verify_archive(source).valid
    assert "could not be saved" in caplog.text


def test_slurm_metadata_identifies_submitted_definition(sealed_run):
    from waterology.core.records import ExecutorReference
    from waterology.core.rocrate import run_metadata

    root, source = sealed_run
    for name in ("torc-workflow.yaml", "torc-slurm-workflow.yaml"):
        (source / name).write_text("jobs: []")
    manifest = archive.load_archive(root, source.name).model_copy(
        update={
            "executor": "torc",
            "executor_reference": ExecutorReference(
                compute_profile="cluster",
                api_url="http://localhost:8080",
                execution_mode="slurm",
                workflow_id="1",
                torc_version="0.40.0",
            ),
        }
    )
    metadata, _profile = run_metadata(source, manifest, archive.verify_archive(source))
    graph = {n["@id"]: n for n in metadata["@graph"]}
    assert graph["#run"]["instrument"] == {"@id": "run/torc-slurm-workflow.yaml"}
    assert graph["./"]["mainEntity"] == graph["#run"]["instrument"]
    assert "run/torc-workflow.yaml" in graph


@pytest.mark.parametrize("outcome", ["timeout", "rejected", "version", "invalid-report"])
def test_validator_records_bounded_failures(tmp_path, monkeypatch, outcome):
    import subprocess

    from waterology.core import rocrate

    calls = []
    monkeypatch.setattr(rocrate.shutil, "which", lambda name: "validator")

    def run(args, **kwargs):
        calls.append((args, kwargs))
        assert kwargs["timeout"] <= 60
        if args[-1] == "--version":
            return subprocess.CompletedProcess(
                args, 0, "wrong" if outcome == "version" else "rocrate-validator 0.11.4\n", ""
            )
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(args, 60, output=b"partial output", stderr=b"fixture")
        return subprocess.CompletedProcess(
            args, 1 if outcome == "rejected" else 0, "invalid", "fixture"
        )

    monkeypatch.setattr(rocrate.subprocess, "run", run)
    result = rocrate.validate_crate(tmp_path, "process-run-crate-0.5")
    assert result["status"] != "passed"
    if outcome != "version":
        assert "--profile-identifier" in calls[-1][0]
        assert "--requirement-severity" in calls[-1][0]
    if outcome == "timeout":
        assert result["stdout"] == "partial output"


def test_automatic_failure_does_not_follow_diagnostic_symlink(
    sealed_run, monkeypatch, tmp_path, caplog
):
    import shutil

    from waterology.core import rocrate

    root, source = sealed_run
    shutil.rmtree(root / ".waterology/ro-crates" / source.name)
    outside = tmp_path / "outside-errors"
    outside.mkdir()
    (root / ".waterology/ro-crate-errors").symlink_to(outside, target_is_directory=True)

    def fail(*args, **kwargs):
        raise OSError("fixture failure")

    monkeypatch.setattr(rocrate, "export_crate", fail)
    archive.auto_export_run_crate(root, source.name)
    assert not list(outside.iterdir())
    assert "could not be saved" in caplog.text
    assert archive.verify_archive(source).valid
