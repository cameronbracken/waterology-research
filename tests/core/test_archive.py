import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest
import zstandard
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.archive import (
    ArchiveArtifactMissingError,
    ArchiveConflictError,
    ArchiveError,
    ArchivePathError,
    build_run_archive,
    load_archive,
    verify_archive,
)
from waterology.core.config import (
    ArchiveConfig,
    ProjectConfig,
    load_project_config,
    project_config_toml,
)
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.records import ExecutorReference

runner = CliRunner()


def make_experiment(path: Path, *, output: str = "artifacts/result.json") -> tuple[Path, str]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Researcher"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    config = ProjectConfig(
        name="archive-study",
        artifact_roots=("artifacts",),
        command=("python3", "model.py"),
        outputs=(output,),
        environment_files=("waterology.toml",),
    )
    (path / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    (path / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "Add baseline"], check=True)
    experiment = create_experiment(
        path,
        hypothesis="Archive this run.",
        experiment_id="exp-archive",
    )
    return path, experiment.id


def git(path: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_build_and_verify_run_archive(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text('{"rmse": 1.25}\n', encoding="utf-8")
    commit = git(worktree, "rev-parse", "HEAD")

    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-success",
        commit_sha=commit,
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="baseline\n",
        stderr="",
        metrics={"rmse": 1.25},
    )

    assert archive.name == "run-success"
    assert (archive / "source.tar.zst").stat().st_size > 0
    source_tar = zstandard.ZstdDecompressor().decompress((archive / "source.tar.zst").read_bytes())
    with tarfile.open(fileobj=io.BytesIO(source_tar)) as source:
        assert {"model.py", "waterology.toml"} <= set(source.getnames())
    assert (archive / "artifacts" / "artifacts" / "result.json").is_file()
    environment = json.loads((archive / "environment.json").read_text(encoding="utf-8"))
    assert environment["tool_versions"]["git"].startswith("git version ")
    assert environment["tool_versions"]["waterology"]
    verification = verify_archive(archive)
    assert verification.valid is True
    assert verification.missing == verification.changed == verification.unexpected == ()


def test_torc_archive_preserves_executor_reference_and_workflow(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    staging = root / ".waterology" / "staging" / "run-torc"
    staging.mkdir()
    (staging / "torc-workflow.yaml").write_text("name: managed\n", encoding="utf-8")
    reference = ExecutorReference(
        compute_profile="cluster",
        api_url="http://localhost:8085/torc-service/v1",
        execution_mode="slurm",
        workflow_id="42",
        job_ids=("9",),
        torc_version="torc 0.39.0",
        workflow_spec_sha256="a" * 64,
    )

    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-torc",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:01:00Z",
        terminal_state="completed",
        exit_code=0,
        stdout="managed\n",
        stderr="",
        metrics={},
        executor_reference=reference,
        compute_profile="cluster",
    )

    manifest = load_archive(root, "run-torc")
    environment = json.loads((archive / "environment.json").read_text(encoding="utf-8"))
    assert manifest.executor == "torc"
    assert manifest.executor_reference == reference
    assert environment["compute_profile"] == "cluster"
    assert (archive / "torc-workflow.yaml").read_text(encoding="utf-8") == "name: managed\n"
    assert verify_archive(archive).valid is True


def test_verify_archive_reports_changed_payload(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-changed",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="original\n",
        stderr="",
        metrics={},
    )
    (archive / "stdout.log").write_text("changed\n", encoding="utf-8")

    verification = verify_archive(archive)

    assert verification.valid is False
    assert verification.changed == ("stdout.log",)


def test_archive_redacts_configured_log_patterns_before_sealing(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    config = load_project_config(worktree / "waterology.toml").model_copy(
        update={"archive": ArchiveConfig(log_redactions=(r"token=[^\s]+",))}
    )
    (worktree / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    subprocess.run(["git", "-C", str(worktree), "add", "waterology.toml"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "Configure redaction"],
        check=True,
    )
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")

    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-redacted",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="token=stdout-secret\n",
        stderr="token=stderr-secret\n",
        metrics={},
    )

    assert (archive / "stdout.log").read_text(encoding="utf-8") == "[REDACTED]\n"
    assert (archive / "stderr.log").read_text(encoding="utf-8") == "[REDACTED]\n"
    assert verify_archive(archive).valid is True


def test_verify_archive_reports_missing_and_unexpected_payloads(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-files",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="",
        stderr="",
        metrics={},
    )
    (archive / "stderr.log").unlink()
    (archive / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")

    verification = verify_archive(archive)

    assert verification.valid is False
    assert verification.missing == ("stderr.log",)
    assert verification.unexpected == ("unexpected.txt",)


def test_verify_archive_rejects_checksum_path_traversal(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-traversal",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="",
        stderr="",
        metrics={},
    )
    (archive / "checksums.sha256").write_text(f"{'0' * 64}  ../../outside.txt\n", encoding="utf-8")

    with pytest.raises(ArchivePathError, match="unsafe path"):
        verify_archive(archive)


def test_verify_archive_does_not_follow_inserted_symlink(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-symlink",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="",
        stderr="",
        metrics={},
    )
    outside = tmp_path / "outside.log"
    outside.write_text("outside\n", encoding="utf-8")
    (archive / "stdout.log").unlink()
    (archive / "stdout.log").symlink_to(outside)

    verification = verify_archive(archive)

    assert verification.valid is False
    assert verification.changed == ("stdout.log",)


def test_load_archive_rejects_manifest_identifier_mismatch(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-correct",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="",
        stderr="",
        metrics={},
    )
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    manifest["run_id"] = "run-other"
    (archive / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(ArchiveError, match="does not match directory"):
        load_archive(root, "run-correct")


def test_archive_rejects_declared_artifact_symlink_escape(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    artifacts = worktree / "artifacts"
    artifacts.mkdir()
    (artifacts / "result.json").symlink_to(outside)

    with pytest.raises(ArchivePathError, match="escapes the experiment worktree"):
        build_run_archive(
            root,
            experiment_id=experiment_id,
            run_id="run-escape",
            commit_sha=git(worktree, "rev-parse", "HEAD"),
            command=("python3", "model.py"),
            started_at="2026-08-25T10:00:00Z",
            finished_at="2026-08-25T10:00:01Z",
            terminal_state="failed",
            exit_code=1,
            stdout="",
            stderr="failed\n",
            metrics={},
        )

    assert not (root / ".waterology" / "runs" / "run-escape").exists()


def test_archive_rejects_nested_symlink_escape_in_declared_directory(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study", output="artifacts")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    artifacts = worktree / "artifacts"
    artifacts.mkdir()
    (artifacts / "inside.json").write_text("{}\n", encoding="utf-8")
    (artifacts / "escaped.json").symlink_to(outside)

    with pytest.raises(ArchivePathError, match="nested path escapes"):
        build_run_archive(
            root,
            experiment_id=experiment_id,
            run_id="run-nested-escape",
            commit_sha=git(worktree, "rev-parse", "HEAD"),
            command=("python3", "model.py"),
            started_at="2026-08-25T10:00:00Z",
            finished_at="2026-08-25T10:00:01Z",
            terminal_state="completed",
            exit_code=0,
            stdout="",
            stderr="",
            metrics={},
        )


def test_archive_hashes_artifacts_named_like_internal_staging_files(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study", output="artifacts")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    artifacts = worktree / "artifacts"
    artifacts.mkdir()
    for name in ("execution.json", ".execution.json.tmp", "checksums.sha256"):
        (artifacts / name).write_text(f"artifact {name}\n", encoding="utf-8")

    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-internal-names",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="",
        stderr="",
        metrics={},
    )

    checksums = (archive / "checksums.sha256").read_text(encoding="utf-8")
    assert "artifacts/artifacts/execution.json" in checksums
    assert "artifacts/artifacts/.execution.json.tmp" in checksums
    assert "artifacts/artifacts/checksums.sha256" in checksums
    assert verify_archive(archive).valid is True


def test_archive_replaces_staged_log_symlink_without_writing_target(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    outside = tmp_path / "outside.log"
    outside.write_text("outside stays unchanged\n", encoding="utf-8")
    staging = root / ".waterology" / "staging" / "run-staged-log-link"
    staging.mkdir()
    (staging / "stdout.log").symlink_to(outside)

    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-staged-log-link",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="safe log\n",
        stderr="",
        metrics={},
    )

    assert outside.read_text(encoding="utf-8") == "outside stays unchanged\n"
    assert (archive / "stdout.log").read_text(encoding="utf-8") == "safe log\n"
    assert verify_archive(archive).valid is True


def test_archive_cli_lists_shows_and_verifies_sealed_run(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-cli",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="done\n",
        stderr="",
        metrics={},
    )

    listed = runner.invoke(app, ["archive", "list", "--path", str(root), "--json"])
    shown = runner.invoke(app, ["archive", "show", "run-cli", "--path", str(root), "--json"])
    verified = runner.invoke(app, ["archive", "verify", "run-cli", "--path", str(root), "--json"])

    assert listed.exit_code == shown.exit_code == verified.exit_code == 0
    assert [item["run_id"] for item in json.loads(listed.stdout)["archives"]] == ["run-cli"]
    assert json.loads(shown.stdout)["archive"]["experiment_id"] == experiment_id
    assert json.loads(verified.stdout)["verification"]["valid"] is True


def test_completed_archive_requires_declared_artifacts_before_staging(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id

    with pytest.raises(ArchiveArtifactMissingError, match="artifacts/result.json"):
        build_run_archive(
            root,
            experiment_id=experiment_id,
            run_id="run-missing",
            commit_sha=git(worktree, "rev-parse", "HEAD"),
            command=("python3", "model.py"),
            started_at="2026-08-25T10:00:00Z",
            finished_at="2026-08-25T10:00:01Z",
            terminal_state="completed",
            exit_code=0,
            stdout="",
            stderr="",
            metrics={},
        )

    assert not (root / ".waterology" / "staging" / "run-missing").exists()


def test_archive_resumes_known_incomplete_staging_payloads(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    staging = root / ".waterology" / "staging" / "run-resume"
    staging.mkdir()
    (staging / "stdout.log").write_text("partial\n", encoding="utf-8")
    stale = staging / "artifacts"
    stale.mkdir()
    (stale / "stale.txt").write_text("stale\n", encoding="utf-8")

    archive = build_run_archive(
        root,
        experiment_id=experiment_id,
        run_id="run-resume",
        commit_sha=git(worktree, "rev-parse", "HEAD"),
        command=("python3", "model.py"),
        started_at="2026-08-25T10:00:00Z",
        finished_at="2026-08-25T10:00:01Z",
        terminal_state="completed",
        exit_code=0,
        stdout="complete\n",
        stderr="",
        metrics={},
    )

    assert (archive / "stdout.log").read_text(encoding="utf-8") == "complete\n"
    assert not (archive / "artifacts" / "stale.txt").exists()
    assert verify_archive(archive).valid is True


def test_sealed_archive_is_never_overwritten(tmp_path: Path) -> None:
    root, experiment_id = make_experiment(tmp_path / "study")
    worktree = root / ".waterology" / "worktrees" / experiment_id
    output = worktree / "artifacts" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    arguments = {
        "experiment_id": experiment_id,
        "run_id": "run-sealed",
        "commit_sha": git(worktree, "rev-parse", "HEAD"),
        "command": ("python3", "model.py"),
        "started_at": "2026-08-25T10:00:00Z",
        "finished_at": "2026-08-25T10:00:01Z",
        "terminal_state": "completed",
        "exit_code": 0,
        "stdout": "first\n",
        "stderr": "",
        "metrics": {},
    }
    archive = build_run_archive(root, **arguments)

    with pytest.raises(ArchiveConflictError, match="already exists"):
        build_run_archive(root, **arguments)

    assert (archive / "stdout.log").read_text(encoding="utf-8") == "first\n"
