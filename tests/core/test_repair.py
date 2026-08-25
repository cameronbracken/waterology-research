import json
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from typer.testing import CliRunner

import waterology.core.repair as repair_module
from waterology.cli import app
from waterology.core.archive import ArchiveError, verify_project_archive
from waterology.core.assessments import assess_run
from waterology.core.config import ProjectConfig, project_config_toml
from waterology.core.database import DatabasePathError, open_database
from waterology.core.evidence import (
    EvidenceRelationshipError,
    register_artifact_reference,
    register_evidence,
)
from waterology.core.execution import start_direct_run
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.repair import RepairRecordError, repair_index
from waterology.core.sessions import add_session_note, create_session, transition_session

runner = CliRunner()


def make_assessed_run(path: Path) -> tuple[Path, str, str]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Researcher"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    config = ProjectConfig(
        name="repair-study",
        artifact_roots=("artifacts",),
        command=("python3", "model.py"),
        outputs=("artifacts/result.txt",),
    )
    (path / "waterology.toml").write_text(project_config_toml(config), encoding="utf-8")
    (path / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "Add baseline"], check=True)
    experiment = create_experiment(
        path,
        hypothesis="Repair this experiment index.",
        experiment_id="exp-repair",
    )
    worktree = path / experiment.worktree
    (worktree / "model.py").write_text(
        """\
from pathlib import Path

Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/result.txt").write_text("result\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(worktree), "add", "model.py"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "Add variant"],
        check=True,
    )
    run = start_direct_run(path, experiment.id, run_id="run-repair")
    assess_run(
        path,
        run.run_id,
        kind="answer",
        conclusion="The archived result answers the hypothesis.",
        author="cam",
        evidence=(f".waterology/runs/{run.run_id}/artifacts/artifacts/result.txt",),
    )
    return path, experiment.id, run.run_id


def test_repair_index_rebuilds_experiment_run_assessment_and_artifact(tmp_path: Path) -> None:
    root, experiment_id, run_id = make_assessed_run(tmp_path / "study")
    database_path = root / ".waterology" / "state.sqlite"
    assert verify_project_archive(root, run_id).valid is True
    database_path.unlink()

    result = repair_index(root)

    assert result.experiments == 1
    assert result.runs == 1
    assert result.assessments == 1
    assert result.artifacts == 1
    with open_database(database_path) as database:
        experiment = database.connection.execute(
            "SELECT status FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
        run = database.connection.execute(
            "SELECT operational_state, process_id FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        assessment_count = database.connection.execute(
            "SELECT COUNT(*) FROM assessments"
        ).fetchone()[0]
        integrity = database.connection.execute("PRAGMA integrity_check").fetchone()[0]
    assert experiment[0] == "frozen"
    assert run[0] == "completed"
    assert run[1] is not None
    assert assessment_count == 1
    assert integrity == "ok"


def test_repair_index_keeps_existing_database_when_archive_is_invalid(tmp_path: Path) -> None:
    root, _, run_id = make_assessed_run(tmp_path / "study")
    database_path = root / ".waterology" / "state.sqlite"
    before = database_path.read_bytes()
    (root / ".waterology" / "runs" / run_id / "stdout.log").write_text(
        "tampered\n", encoding="utf-8"
    )

    with pytest.raises(ArchiveError, match="failed checksum verification"):
        repair_index(root)

    assert database_path.read_bytes() == before


def test_repair_rejects_symlinked_sealed_run_without_reading_target(tmp_path: Path) -> None:
    root, _, run_id = make_assessed_run(tmp_path / "study")
    archive = root / ".waterology" / "runs" / run_id
    outside = tmp_path / "outside-archive"
    archive.rename(outside)
    archive.symlink_to(outside, target_is_directory=True)
    marker = outside / "stdout.log"
    before = marker.read_bytes()

    with pytest.raises(RepairRecordError, match="malformed durable record"):
        repair_index(root)

    assert marker.read_bytes() == before


def test_repair_rejects_symlinked_database_without_modifying_target(tmp_path: Path) -> None:
    root, _, _ = make_assessed_run(tmp_path / "study")
    database = root / ".waterology" / "state.sqlite"
    outside = tmp_path / "outside.sqlite"
    database.rename(outside)
    database.symlink_to(outside)
    before = outside.read_bytes()

    with pytest.raises(DatabasePathError, match="must not be a symlink"):
        repair_index(root)

    assert outside.read_bytes() == before


def test_repair_rejects_assessment_that_does_not_match_run_manifest(tmp_path: Path) -> None:
    root, _, run_id = make_assessed_run(tmp_path / "study")
    database_path = root / ".waterology" / "state.sqlite"
    before = database_path.read_bytes()
    assessment_path = next(
        (root / ".waterology" / "assessments" / run_id).glob("assessment-*.json")
    )
    payload = json.loads(assessment_path.read_text(encoding="utf-8"))
    payload["commit_sha"] = "0" * 40
    assessment_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match its run manifest"):
        repair_index(root)

    assert database_path.read_bytes() == before


def test_repair_restores_database_sidecars_when_atomic_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = make_assessed_run(tmp_path / "study")
    database_path = root / ".waterology" / "state.sqlite"
    before = {
        path.name: path.read_bytes()
        for path in database_path.parent.glob("state.sqlite*")
        if path.is_file()
    }
    original_replace = Path.replace

    def fail_database_replace(source: Path, target: Path) -> Path:
        if source.name.startswith(".state.sqlite.repair-") and target == database_path:
            raise OSError("injected replacement failure")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_database_replace)

    with pytest.raises(OSError, match="injected replacement failure"):
        repair_index(root)

    after = {
        path.name: path.read_bytes()
        for path in database_path.parent.glob("state.sqlite*")
        if path.is_file()
    }
    assert after == before


@pytest.mark.parametrize(
    ("area", "directory", "record"),
    [
        ("experiments", "invalid-experiment", "experiment.json"),
        ("runs", "invalid-run", "manifest.json"),
        ("assessments", "invalid-assessment", "assessment-0000000000000000.json"),
    ],
)
def test_repair_rejects_malformed_durable_record_locations(
    tmp_path: Path,
    area: str,
    directory: str,
    record: str,
) -> None:
    root, _, _ = make_assessed_run(tmp_path / "study")
    database_path = root / ".waterology" / "state.sqlite"
    before = database_path.read_bytes()
    invalid = root / ".waterology" / area / directory
    invalid.mkdir()
    (invalid / record).write_text("{}\n", encoding="utf-8")

    with pytest.raises(RepairRecordError) as raised:
        repair_index(root)

    assert raised.value.details["rejected_records"] == 1
    assert raised.value.details["paths"] == [invalid.relative_to(root).as_posix()]
    assert database_path.read_bytes() == before


def test_repair_index_cli_reports_import_counts(tmp_path: Path) -> None:
    root, _, _ = make_assessed_run(tmp_path / "study")
    (root / ".waterology" / "state.sqlite").unlink()

    result = runner.invoke(app, ["repair-index", "--path", str(root), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "result": {
            "artifacts": 1,
            "artifact_references": 0,
            "assessments": 1,
            "evidence": 0,
            "experiments": 1,
            "projects": 1,
            "rejected_records": 0,
            "runs": 1,
            "session_notes": 0,
            "sessions": 0,
            "warnings": [],
        },
        "status": "pass",
    }


def test_repair_index_rebuilds_sessions_notes_evidence_and_references(tmp_path: Path) -> None:
    root, experiment_id, run_id = make_assessed_run(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="reviewer",
        task="Review the archived evidence.",
        session_id="session-9999999999999999",
    )
    add_session_note(root, session.id, "The archive is internally consistent.", author="cam")
    register_evidence(
        root,
        experiment_id=experiment_id,
        claim="The archived result answers the hypothesis.",
        run_id=run_id,
        evidence_id="evidence-9999999999999999",
    )
    register_artifact_reference(
        root,
        experiment_id=experiment_id,
        path=f".waterology/runs/{run_id}/artifacts/artifacts/result.txt",
        run_id=run_id,
        artifact_id="artifact-9999999999999999",
    )
    database_path = root / ".waterology" / "state.sqlite"
    database_path.unlink()

    result = repair_index(root)

    assert result.sessions == 1
    assert result.session_notes == 1
    assert result.evidence == 1
    assert result.artifact_references == 1
    with open_database(database_path) as database:
        counts = {
            table: database.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("sessions", "session_notes", "evidence", "artifact_references")
        }
    assert counts == {
        "sessions": 1,
        "session_notes": 1,
        "evidence": 1,
        "artifact_references": 1,
    }


def test_repair_rejects_session_directory_that_does_not_match_record(tmp_path: Path) -> None:
    root, experiment_id, _ = make_assessed_run(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="reviewer",
        task="Check the durable layout.",
        session_id="session-8888888888888888",
    )
    source = root / ".waterology" / "sessions" / session.id
    source.rename(source.with_name("session-7777777777777777"))

    with pytest.raises(RepairRecordError, match="malformed durable record"):
        repair_index(root)


def test_repair_rejects_unrecognized_note_and_symlink_below_session(tmp_path: Path) -> None:
    root, experiment_id, _ = make_assessed_run(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="reviewer",
        task="Check nested records.",
        session_id="session-6666666666666666",
    )
    notes = root / ".waterology" / "sessions" / session.id / "notes"
    notes.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    (notes / "unexpected.json").symlink_to(outside)

    with pytest.raises(RepairRecordError, match="malformed durable record"):
        repair_index(root)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("project_id", "another-project", "project does not match"),
        ("worktree", ".waterology/worktrees/exp-other", "worktree does not match"),
        ("task_path", "task.md", "task path does not match"),
    ],
)
def test_repair_rejects_inconsistent_session_relationships(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    root, experiment_id, _ = make_assessed_run(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="reviewer",
        task="Check relationships.",
        session_id="session-5555555555555555",
    )
    record = root / ".waterology" / "sessions" / session.id / "session.json"
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload[field] = value
    record.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(RepairRecordError, match=message):
        repair_index(root)


def test_repair_ignores_regular_atomic_write_crash_remnants(tmp_path: Path) -> None:
    root, experiment_id, _ = make_assessed_run(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="reviewer",
        task="Recover around staged writes.",
        session_id="session-4444444444444444",
    )
    session_directory = root / ".waterology" / "sessions" / session.id
    (session_directory / ".session.json.waterology-stage-ab12").write_text(
        "partial\n", encoding="utf-8"
    )
    (root / ".waterology/evidence/.evidence-x.json.waterology-stage-cd34").write_text(
        "partial\n", encoding="utf-8"
    )

    result = repair_index(root)

    assert result.sessions == 1


def test_evidence_archive_path_must_match_record_experiment_and_run(tmp_path: Path) -> None:
    root, experiment_id, run_id = make_assessed_run(tmp_path / "study")
    assessment = next((root / ".waterology/assessments" / run_id).glob("assessment-*.json"))
    assessment.unlink()
    worktree = root / ".waterology/worktrees" / experiment_id
    subprocess.run(["git", "-C", str(worktree), "add", "artifacts"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "--quiet", "-m", "Record first result"],
        check=True,
    )
    second_run = start_direct_run(root, experiment_id, run_id="run-repair-two")
    other = create_experiment(
        root,
        hypothesis="Do not borrow another experiment's archive.",
        experiment_id="exp-other",
    )
    archived = f".waterology/runs/{run_id}/artifacts/artifacts/result.txt"

    with pytest.raises(EvidenceRelationshipError, match="another experiment"):
        register_artifact_reference(root, experiment_id=other.id, path=archived)

    with pytest.raises(EvidenceRelationshipError, match="declared run"):
        register_artifact_reference(
            root,
            experiment_id=experiment_id,
            path=archived,
            run_id=second_run.run_id,
        )


def test_repair_and_session_mutation_share_project_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, experiment_id, _ = make_assessed_run(tmp_path / "study")
    session = create_session(
        root,
        experiment_id=experiment_id,
        runtime="codex",
        role="reviewer",
        task="Serialize repair and ownership updates.",
        session_id="session-3333333333333333",
    )
    scan_started = threading.Event()
    continue_scan = threading.Event()
    original_validate = repair_module._validate_durable_layout

    def pause_scan(project: object) -> None:
        scan_started.set()
        assert continue_scan.wait(timeout=5)
        original_validate(project)  # type: ignore[arg-type]

    monkeypatch.setattr(repair_module, "_validate_durable_layout", pause_scan)

    with ThreadPoolExecutor(max_workers=2) as executor:
        repair_future = executor.submit(repair_index, root)
        assert scan_started.wait(timeout=5)
        transition_future = executor.submit(
            transition_session,
            root,
            session.id,
            state="failed",
            exit_code=1,
        )
        assert transition_future.done() is False
        continue_scan.set()
        repair_future.result(timeout=10)
        transition_future.result(timeout=10)

    with open_database(root / ".waterology/state.sqlite") as database:
        state = database.connection.execute(
            "SELECT state FROM sessions WHERE id = ?", (session.id,)
        ).fetchone()[0]
    assert state == "failed"
