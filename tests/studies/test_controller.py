import subprocess

import pytest

from waterology.core import studies
from waterology.core.config import ProjectConfig, project_config_toml
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.repair import repair_index
from waterology.core.studies import StudyContract
from waterology.torc.gateway import TorcLaunchRecord, TorcWorkflowObservation
from waterology.torc.runs import start_torc_run


def git(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def study_project(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.org")
    initialize_project(root)
    config = ProjectConfig(
        name="demo",
        command=("python3", "model.py"),
        default_compute_profile="local",
        artifact_roots=("results",),
        outputs=("results/metrics.json",),
        metrics=({"name": "error", "path": "results/metrics.json", "field": "error"},),
    )
    (root / "waterology.toml").write_text(project_config_toml(config))
    (root / ".gitignore").write_text(".waterology/\nresults/\n")
    (root / "model.py").write_text("print(1)\n")
    git(root, "add", ".")
    git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "base")
    exp = create_experiment(root, hypothesis="baseline", experiment_id="exp-base")
    worktree = root / exp.worktree
    (worktree / "model.py").write_text("print(2)\n")
    git(worktree, "add", "model.py")
    git(worktree, "-c", "commit.gpgsign=false", "commit", "-qm", "candidate")
    machine = tmp_path / "machine.toml"
    machine.write_text('[profiles.local]\nmode="local"\napi_url="http://localhost:8080"\n')
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(machine))
    spec = StudyContract(
        mode="engineering",
        objective="meet error target",
        baseline_experiment=exp.id,
        allowed_paths=("model.py",),
        evaluation={"input": "fixed:1", "seeds": [42]},
        acceptance=({"name": "error", "unit": "m", "threshold": 1},),
        max_iterations=3,
        max_seconds=120,
    )
    return root, worktree, machine, spec


class Gateway:
    def validate(self, *args, **kwargs):
        return {"valid": True}

    def version(self, **kwargs):
        return "torc 0.40.0"

    def launch(self, *args, **kwargs):
        return TorcLaunchRecord("42", ("9",))

    def inspect(self, workflow_id, **kwargs):
        return TorcWorkflowObservation(workflow_id, "completed", ({"exit_code": 0},), {})

    def results(self, *args, **kwargs):
        return {"items": [{"job_id": "9", "return_code": 0}]}

    def collect_logs(self, workflow_id, destination, **kwargs):
        destination.mkdir(parents=True, exist_ok=True)

    def cancel(self, *args, **kwargs):
        return {"status": "cancelled"}


def test_once_authorized_resume_collects_without_resubmitting(study_project, monkeypatch):
    from waterology import services
    from waterology.torc.runs import inspect_torc_run

    root, worktree, machine, spec = study_project
    calls = []

    def launch(*args, **kwargs):
        calls.append(kwargs["run_id"])
        return start_torc_run(*args, **kwargs, gateway=Gateway())

    monkeypatch.setattr(studies, "start_torc_run", launch)
    monkeypatch.setattr(
        services,
        "run_status",
        lambda p, r: inspect_torc_run(
            p, r, machine_config_file=machine, gateway=Gateway()
        ).model_dump(mode="json"),
    )
    record = studies.create_study(root, spec, authorized_by="user: approved bounded test")
    assert studies.advance_study(root, record.id).state == "running"
    (worktree / "results").mkdir(exist_ok=True)
    (worktree / "results/metrics.json").write_text('{"error":0.5}')
    result = studies.advance_study(root, record.id)
    assert result.state == "complete", result.reason
    assert result.best_run == calls[0]
    assert studies.advance_study(root, record.id) == result
    assert len(calls) == 1
    assert (root / ".waterology/runs" / calls[0] / "study.json").is_file()


def test_ambiguous_submission_never_retries_and_blocks_repair(study_project, monkeypatch):
    root, _, _, spec = study_project
    calls = []

    def fail(*args, **kwargs):
        calls.append(kwargs["run_id"])
        raise TimeoutError("possibly launched")

    monkeypatch.setattr(studies, "start_torc_run", fail)
    record = studies.create_study(root, spec, authorized_by="user")
    assert studies.advance_study(root, record.id).state == "blocked"
    assert studies.advance_study(root, record.id).state == "blocked"
    assert len(calls) == 1
    with pytest.raises(Exception, match="Reconcile active"):
        repair_index(root)


def test_changed_profile_blocks_without_launch(study_project, monkeypatch):
    root, _, machine, spec = study_project
    record = studies.create_study(root, spec, authorized_by="user")
    machine.write_text(machine.read_text().replace("8080", "9090"))
    monkeypatch.setattr(studies, "start_torc_run", lambda *a, **kw: pytest.fail("must not submit"))
    result = studies.advance_study(root, record.id)
    assert result.state == "blocked"
    assert "configuration changed" in result.reason


def test_stop_before_launch_submits_nothing(study_project, monkeypatch):
    root, _, _, spec = study_project
    record = studies.create_study(root, spec, authorized_by="user")
    monkeypatch.setattr(studies, "start_torc_run", lambda *a, **kw: pytest.fail("must not submit"))
    assert studies.stop_study(root, record.id).state == "stopped"


def test_expired_authorization_never_submits(study_project, monkeypatch):
    root, _, _, spec = study_project
    record = studies.create_study(root, spec, authorized_by="user")
    studies._save(root, record.model_copy(update={"authorized_at": "2000-01-01T00:00:00+00:00"}))
    monkeypatch.setattr(studies, "start_torc_run", lambda *a, **kw: pytest.fail("expired"))
    assert studies.advance_study(root, record.id).state == "exhausted"


def test_sealed_failures_retry_same_commit_within_total_cap(study_project, monkeypatch):
    from waterology import services
    from waterology.torc.runs import inspect_torc_run

    class FailedGateway(Gateway):
        def inspect(self, workflow_id, **kwargs):
            return TorcWorkflowObservation(workflow_id, "failed", ({"exit_code": 1},), {})

        def results(self, *args, **kwargs):
            return {"items": [{"job_id": "9", "return_code": 1}]}

    root, _, machine, spec = study_project
    spec = spec.model_copy(update={"max_iterations": 2, "max_retries": 1})
    calls = []

    def launch(*args, **kwargs):
        calls.append(kwargs["run_id"])
        return start_torc_run(*args, **kwargs, gateway=FailedGateway())

    monkeypatch.setattr(studies, "start_torc_run", launch)
    monkeypatch.setattr(
        services,
        "run_status",
        lambda p, r: inspect_torc_run(
            p, r, machine_config_file=machine, gateway=FailedGateway()
        ).model_dump(mode="json"),
    )
    record = studies.create_study(root, spec, authorized_by="user")
    for _ in range(3):
        record = studies.advance_study(root, record.id)
    assert record.state == "exhausted", record.reason
    assert len(calls) == 2
    assert [a.retry for a in record.attempts] == [0, 1]
    assert len({a.commit_sha for a in record.attempts}) == 1


@pytest.fixture
def sealed_run(study_project, monkeypatch):
    from waterology import services
    from waterology.torc.runs import inspect_torc_run

    root, worktree, machine, spec = study_project
    monkeypatch.setattr(
        studies, "start_torc_run", lambda *a, **kw: start_torc_run(*a, **kw, gateway=Gateway())
    )
    monkeypatch.setattr(
        services,
        "run_status",
        lambda p, r: inspect_torc_run(
            p, r, machine_config_file=machine, gateway=Gateway()
        ).model_dump(mode="json"),
    )
    record = studies.create_study(root, spec, authorized_by="user")
    record = studies.advance_study(root, record.id)
    (worktree / "results").mkdir(exist_ok=True)
    (worktree / "results/metrics.json").write_text('{"error":0.5}')
    record = studies.advance_study(root, record.id)
    assert record.state == "complete", record.reason
    return root, record.attempts[0].run_id, record


def test_archive_comparison_keeps_missing_and_incompatible_runs(sealed_run):
    import json
    import shutil

    from waterology.core.archive import _write_checksums
    from waterology.core.comparison import compare_runs

    root, run_id, _ = sealed_run
    directory = root / ".waterology/runs"
    shutil.copytree(directory / run_id, directory / "run-other")
    other = directory / "run-other"
    manifest = json.loads((other / "manifest.json").read_text())
    manifest["run_id"] = "run-other"
    (other / "manifest.json").write_text(json.dumps(manifest))
    context = json.loads((other / "study.json").read_text())
    context["contract"]["acceptance"][0]["unit"] = "ft"
    context["contract_hash"] = studies.fingerprint(context["contract"])
    (other / "study.json").write_text(json.dumps(context))
    _write_checksums(other)
    result = compare_runs(root, [run_id, "run-other", "run-missing"], baseline=run_id)
    assert [r["status"] for r in result["rows"]] == ["verified", "incomparable", "unverified"]
    assert result["rows"][0]["deltas"]["error"] == 0
    assert result["rows"][1]["deltas"] == {}
    assert not result["complete"]


def test_claims_preserve_conflicts_and_detect_archive_changes(sealed_run):
    from waterology.core.claims import list_claims, register_claim, verify_claim

    root, run_id, _ = sealed_run
    first = register_claim(root, claim="Observed error", run_id=run_id, selector="/error")
    conflict = register_claim(
        root,
        claim="A competing interpretation",
        run_id=run_id,
        selector="/error",
        kind="inference",
        relation="contradicts",
        related_claim=first.id,
    )
    assert verify_claim(root, first)["reference_status"] == "PASS"
    assert verify_claim(root, first)["status"] == "UNVERIFIED"
    assert verify_claim(root, conflict)["status"] == "UNVERIFIED"
    assert len(list_claims(root)) == 2
    with pytest.raises(KeyError):
        register_claim(root, claim="Missing", run_id=run_id, selector="/absent")
    with pytest.raises(ValueError):
        register_claim(root, claim="Escape", run_id=run_id, member="../metrics.json")
    (root / ".waterology/runs" / run_id / "metrics.json").write_text('{"error":99}')
    assert verify_claim(root, first)["status"] == "STALE"


def test_report_retains_incomplete_run_and_reproduces_table(sealed_run):
    import json

    from waterology.core.reports import export_report

    root, run_id, _ = sealed_run
    result = export_report(
        root, [run_id, "run-missing"], baseline=run_id, destination="reports/test"
    )
    assert not result["complete"]
    report = root / "reports/test"
    assert "run-missing" in (report / "measurements.csv").read_text()
    assert "0.5" in (report / "measurements.csv").read_text()
    report_source = (report / "report.qmd").read_text()
    assert "embed-resources: true" in report_source
    assert report_source.index("dark: darkly") < report_source.index("light: flatly")
    palette = json.loads((report / "palette.json").read_text())
    assert palette["default_mode"] == "dark"
    assert palette["algorithm"]["name"] == "Chameleon"
    assert (report / "theme-sync.html").is_file()
    theme_sync = (report / "theme-sync.html").read_text()
    assert "quarto-light" in theme_sync
    assert "Plotly.restyle" in theme_sync
    assert "Plotly.relayout" in theme_sync
    render_script = (report / "render.py").read_text()
    assert "plotly_dark" in render_script
    assert "customdata=color_indices" in render_script
    manifest = json.loads((report / "provenance.json").read_text())
    assert manifest["sources"][0]["archive_hash"]
    with pytest.raises(ValueError):
        export_report(root, [run_id], baseline=run_id, destination="reports/test")


def test_recorded_search_preserves_query_failure_and_doi_provenance(study_project):
    from waterology.core.literature import record_source_decision, search_literature

    root, *_ = study_project

    def provider(query, **kwargs):
        assert query == "reservoir operations"
        assert kwargs["after"] == "2020-01-01"
        return {
            "results": [
                {"id": "W1", "doi": "https://doi.org/10.1/ABC", "display_name": "A"},
                {"id": "W2", "doi": "https://doi.org/10.1/abc", "display_name": "A second source"},
            ]
        }

    result = search_literature(root, "reservoir operations", after="2020-01-01", fetcher=provider)
    assert len(result["sources"]) == 1
    assert len(result["sources"][0]["provenance"]) == 2
    assert not result["sources"][0]["full_text_read"]
    decision = record_source_decision(
        root, result["id"], "W1", decision="include", note="Relevant method"
    )
    assert decision["decision"] == "include"

    def fail(*args, **kwargs):
        raise OSError("secret-in-url")

    failed = search_literature(root, "query", fetcher=fail)
    assert failed["status"] == "unverified"
    assert "secret" not in str(failed)


def test_completed_study_stop_preserves_outcome(sealed_run):
    root, _, record = sealed_run
    assert studies.stop_study(root, record.id) == record


def test_stale_outputs_cannot_satisfy_acceptance(study_project, monkeypatch):
    from waterology import services
    from waterology.torc.runs import inspect_torc_run

    root, worktree, machine, spec = study_project
    (worktree / "results").mkdir(exist_ok=True)
    (worktree / "results/metrics.json").write_text('{"error":0.5}')
    monkeypatch.setattr(
        studies, "start_torc_run", lambda *a, **kw: start_torc_run(*a, **kw, gateway=Gateway())
    )
    monkeypatch.setattr(
        services,
        "run_status",
        lambda p, r: inspect_torc_run(
            p, r, machine_config_file=machine, gateway=Gateway()
        ).model_dump(mode="json"),
    )
    record = studies.create_study(root, spec, authorized_by="user")
    assert studies.advance_study(root, record.id).state == "running"
    result = studies.advance_study(root, record.id)
    assert result.state == "blocked"
    assert result.best_run is None


def test_candidate_driver_uses_owned_session_and_queues_committed_change(
    study_project, monkeypatch
):
    from types import SimpleNamespace

    from waterology import services
    from waterology.agents import supervisor
    from waterology.core.sessions import load_session
    from waterology.core.study_driver import configure_driver, drive_study
    from waterology.torc.runs import inspect_torc_run

    root, worktree, machine, spec = study_project
    spec = spec.model_copy(update={"mode": "research", "max_iterations": 2})
    monkeypatch.setattr(
        studies, "start_torc_run", lambda *a, **kw: start_torc_run(*a, **kw, gateway=Gateway())
    )
    monkeypatch.setattr(
        services,
        "run_status",
        lambda p, r: inspect_torc_run(
            p, r, machine_config_file=machine, gateway=Gateway()
        ).model_dump(mode="json"),
    )
    record = studies.create_study(root, spec, authorized_by="user authorized bounded fixture")
    studies.advance_study(root, record.id)
    (worktree / "results").mkdir(exist_ok=True)
    (worktree / "results/metrics.json").write_text('{"error":0.5}')
    assert studies.advance_study(root, record.id).state == "ready"
    launches = []

    def launch(path, session_id, *, prompt):
        session = load_session(path, session_id)
        candidate = root / session.worktree
        (candidate / "model.py").write_text("print(3)\n")
        git(candidate, "add", "model.py")
        git(candidate, "-c", "commit.gpgsign=false", "commit", "-qm", "agent fixture")
        launches.append(session_id)
        assert "Do not launch evaluations" in prompt
        return session

    monkeypatch.setattr(supervisor, "launch_session", launch)
    monkeypatch.setattr(
        supervisor, "reconcile_session", lambda *args: SimpleNamespace(state="completed")
    )
    configure_driver(root, record.id, runtime="codex", max_proposals=1)
    result = drive_study(root, record.id)
    assert result["driver"]["proposals"][0]["state"] == "running"
    result = drive_study(root, record.id)
    assert result["driver"]["proposals"][0]["state"] == "evaluating"
    assert len(result["study"]["queue"]) == 1
    assert len(launches) == 1


def test_reports_reject_control_state_and_symlink_destinations(sealed_run):
    from waterology.core.reports import export_report

    root, run_id, _ = sealed_run
    for destination in [".git/report", ".waterology/report", f".waterology/runs/{run_id}/report"]:
        with pytest.raises(ValueError):
            export_report(root, [run_id], baseline=run_id, destination=destination)
    (root / "linked").symlink_to(root / ".waterology", target_is_directory=True)
    with pytest.raises(ValueError):
        export_report(root, [run_id], baseline=run_id, destination="linked/report")


def test_explicit_claim_assessment_is_separate_from_reference_integrity(sealed_run):
    from waterology.core.claims import assess_claim, register_claim, verify_claim

    root, run_id, _ = sealed_run
    claim = register_claim(
        root, claim="The measured fixture error is 0.5 m", run_id=run_id, selector="/error"
    )
    assert verify_claim(root, claim)["status"] == "UNVERIFIED"
    assess_claim(
        root,
        claim.id,
        status="PASS",
        author="review fixture",
        note="The stated value and units match the declared measurement",
    )
    assert verify_claim(root, claim)["status"] == "PASS"
    assert verify_claim(root, claim)["reference_status"] == "PASS"


def test_missing_claim_archive_is_unverified(sealed_run):
    import shutil

    from waterology.core.claims import register_claim, verify_claim

    root, run_id, _ = sealed_run
    claim = register_claim(root, claim="Value", run_id=run_id, selector="/error")
    shutil.rmtree(root / ".waterology/runs" / run_id)
    assert verify_claim(root, claim)["status"] == "UNVERIFIED"


def test_generic_execution_cannot_bypass_managed_routing(study_project):
    from waterology import services

    root, _, _, spec = study_project
    studies.create_study(root, spec, authorized_by="user")
    with pytest.raises(studies.StudyError, match="managed study"):
        services.start_run(root, spec.baseline_experiment, profile="direct")


def test_generation_candidate_is_owned_before_enqueue(study_project):
    from waterology.core.study_driver import _save_driver, configure_driver

    root, _, _, spec = study_project
    record = studies.create_study(root, spec, authorized_by="user")
    driver = configure_driver(root, record.id, runtime="codex", max_proposals=1)
    driver["proposals"] = [
        {"experiment_id": "exp-proposal", "session_id": "session-" + "a" * 16, "state": "reserved"}
    ]
    _save_driver(root, record.id, driver)
    with pytest.raises(studies.StudyError, match="managed study"):
        studies.guard_submission(root, "exp-proposal")


def test_public_stop_cancels_ambiguous_candidate_session(study_project, monkeypatch):
    from types import SimpleNamespace

    from waterology.agents import supervisor
    from waterology.core.study_driver import _save_driver, configure_driver

    root, _, _, spec = study_project
    spec = spec.model_copy(update={"stop_behavior": "cancel"})
    record = studies.create_study(root, spec, authorized_by="user")
    driver = configure_driver(root, record.id, runtime="codex", max_proposals=1)
    driver["proposals"] = [
        {"experiment_id": "exp-proposal", "session_id": "session-" + "a" * 16, "state": "launching"}
    ]
    _save_driver(root, record.id, driver)
    monkeypatch.setattr(
        supervisor,
        "reconcile_session",
        lambda *args: SimpleNamespace(state="running", id="session-" + "a" * 16),
    )
    cancelled = []
    monkeypatch.setattr(supervisor, "interrupt_session", lambda p, s: cancelled.append(s))
    result = studies.stop_study(root, record.id)
    assert cancelled == ["session-" + "a" * 16]
    assert result.state == "stopped"


def test_stop_retains_unresolved_candidate_ownership(study_project, monkeypatch):
    from waterology.agents import supervisor
    from waterology.core.errors import WaterologyError
    from waterology.core.study_driver import _save_driver, configure_driver

    root, _, _, spec = study_project
    record = studies.create_study(root, spec, authorized_by="user")
    driver = configure_driver(root, record.id, runtime="codex", max_proposals=1)
    driver["proposals"] = [
        {"experiment_id": "exp-proposal", "session_id": "session-" + "a" * 16, "state": "launching"}
    ]
    _save_driver(root, record.id, driver)

    def unavailable(*args):
        raise WaterologyError("session unavailable")

    monkeypatch.setattr(supervisor, "reconcile_session", unavailable)
    result = studies.stop_study(root, record.id)
    assert result.state == "blocked"
    assert "cancellation unresolved" in result.reason


def test_accepted_outcome_survives_candidate_drain(sealed_run, monkeypatch):
    from types import SimpleNamespace

    from waterology.agents import supervisor
    from waterology.core.study_driver import _save_driver

    root, _, record = sealed_run
    _save_driver(
        root,
        record.id,
        {
            "study_id": record.id,
            "proposals": [
                {
                    "experiment_id": "exp-proposal",
                    "session_id": "session-" + "a" * 16,
                    "state": "running",
                }
            ],
            "reason": None,
        },
    )
    monkeypatch.setattr(
        supervisor,
        "reconcile_session",
        lambda *a: SimpleNamespace(state="running", id="session-" + "a" * 16),
    )
    assert studies.stop_study(root, record.id).state == "stopping"
    monkeypatch.setattr(
        supervisor,
        "reconcile_session",
        lambda *a: SimpleNamespace(state="completed", id="session-" + "a" * 16),
    )
    assert studies.stop_study(root, record.id).state == "complete"


def test_research_conclusion_after_budget_needs_assessed_evidence(study_project, monkeypatch):
    from waterology import services
    from waterology.core.claims import assess_claim, register_claim
    from waterology.torc.runs import inspect_torc_run

    root, worktree, machine, spec = study_project
    spec = spec.model_copy(update={"mode": "research", "max_iterations": 1})
    monkeypatch.setattr(
        studies, "start_torc_run", lambda *a, **kw: start_torc_run(*a, **kw, gateway=Gateway())
    )
    monkeypatch.setattr(
        services,
        "run_status",
        lambda p, r: inspect_torc_run(
            p, r, machine_config_file=machine, gateway=Gateway()
        ).model_dump(mode="json"),
    )
    record = studies.create_study(root, spec, authorized_by="user")
    record = studies.advance_study(root, record.id)
    (worktree / "results").mkdir(exist_ok=True)
    (worktree / "results/metrics.json").write_text('{"error":0.5}')
    record = studies.advance_study(root, record.id)
    assert record.state == "exhausted"  # Numerical success is not a research conclusion.
    claim = register_claim(
        root, claim="Fixture error is 0.5 m", run_id=record.attempts[0].run_id, selector="/error"
    )
    with pytest.raises(studies.StudyError, match="assessed claims"):
        studies.conclude_study(
            root,
            record.id,
            conclusion="Synthetic observation only",
            evidence=[claim.id],
            author="reviewer",
        )
    assess_claim(
        root, claim.id, status="PASS", author="reviewer", note="Checked the declared fixture metric"
    )
    monkeypatch.setattr(
        studies, "start_torc_run", lambda *a, **kw: pytest.fail("budget cannot reopen")
    )
    result = studies.conclude_study(
        root,
        record.id,
        conclusion="Synthetic observation only",
        evidence=[claim.id],
        author="reviewer",
    )
    assert result.state == "complete"
    assert result.conclusion["evidence"] == [claim.id]
    studies._save(root, result.model_copy(update={"state": "stopping"}))
    with pytest.raises(studies.StudyError, match="without a completed conclusion"):
        studies.conclude_study(
            root,
            record.id,
            conclusion="Replacement",
            evidence=[claim.id],
            author="another reviewer",
        )


def test_comparison_cli_mcp_and_dashboard_share_sealed_evidence(sealed_run):
    import asyncio
    import json

    from mcp import Client
    from starlette.testclient import TestClient
    from typer.testing import CliRunner

    from waterology.cli import app
    from waterology.core.comparison import compare_runs
    from waterology.dashboard.app import create_dashboard_app
    from waterology.mcp.server import create_server

    root, run_id, record = sealed_run
    expected = compare_runs(root, [run_id], baseline=run_id)
    result = CliRunner().invoke(
        app,
        [
            "--output-format",
            "json",
            "compare-runs",
            run_id,
            "--baseline",
            run_id,
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == expected

    async def exercise():
        async with Client(create_server(), raise_exceptions=True) as client:
            result = await client.call_tool(
                "compare_archived_runs",
                {"run_ids": [run_id], "baseline": run_id, "project_path": str(root)},
            )
            assert result.structured_content == {"ok": True, "result": expected}

    asyncio.run(exercise())
    with TestClient(create_dashboard_app(root), base_url="http://127.0.0.1") as client:
        listing = client.get("/studies")
        assert listing.status_code == 200
        assert record.id in listing.text
        comparison = client.get("/comparison", params=[("baseline", run_id), ("run", run_id)])
        assert comparison.status_code == 200
        assert "0.5" in comparison.text
        assert "0.5" in client.get("/comparison", params={"baseline": run_id}).text
        changes = client.get(f"/changes/{run_id}")
        assert changes.status_code == 200
        assert "print(2)" in changes.text
        artifact = client.get(f"/artifacts/{run_id}/metrics.json")
        assert artifact.status_code == 200
        assert artifact.json()["error"] == 0.5
        assert client.get(f"/artifacts/{run_id}/missing.json").status_code == 404


@pytest.mark.parametrize("changes", [
    {"claim": "The measured fixture error is 500 m"},
    {"kind": "inference"},
    {"relation": "contradicts"},
])
def test_claim_content_change_invalidates_assessment(sealed_run, changes):
    import json

    from waterology.core.claims import assess_claim, list_claims, register_claim, verify_claim

    root, run_id, _ = sealed_run
    claim = register_claim(root, claim="The measured fixture error is 0.5 m",
                           run_id=run_id, selector="/error")
    assess_claim(root, claim.id, status="PASS", author="reviewer", note="Checked claim")
    path = root / ".waterology/claims" / f"{claim.id}.json"
    path.write_text(json.dumps({**claim.model_dump(mode="json"), **changes}))
    changed = next(c for c in list_claims(root) if c.id == claim.id)
    result = verify_claim(root, changed)
    assert result["reference_status"] == "PASS"
    assert result["status"] == "STALE"
    assess_claim(root, claim.id, status="FAIL", author="reviewer", note="Changed claim is unsupported")
    assert verify_claim(root, changed)["status"] == "FAIL"


def test_legacy_claim_assessment_requires_fresh_review(sealed_run):
    import json

    from waterology.core.claims import assess_claim, register_claim, verify_claim

    root, run_id, _ = sealed_run
    claim = register_claim(root, claim="Observed value", run_id=run_id, selector="/error")
    assessment = assess_claim(root, claim.id, status="PASS", author="reviewer", note="Checked")
    assessment.pop("claim_sha256")
    path = root / ".waterology/claims" / f"{assessment['id']}.json"
    path.write_text(json.dumps(assessment))
    assert verify_claim(root, claim)["status"] == "STALE"


class RejectedGateway(Gateway):
    def launch(self, *args, **kwargs):
        from waterology.torc.gateway import TorcCommandError
        raise TorcCommandError(
            'Error creating workflow from spec: Failed to create workflow: '
            'ResponseError(ResponseContent { status: 401, content: "Unauthorized", entity: None })'
        )


def blocked_submission(study_project, monkeypatch):
    root, _, _, spec = study_project
    monkeypatch.setattr(
        studies, "start_torc_run",
        lambda *a, **kw: start_torc_run(*a, **kw, gateway=RejectedGateway()),
    )
    record = studies.create_study(root, spec, authorized_by="user: bounded test")
    return studies.advance_study(root, record.id)


class RecoveryGateway(Gateway):
    def __init__(self, items=()):
        self.items = items
        self.launches = 0

    def workflow_inventory(self, *, cwd):
        return {"items": list(self.items)}

    def launch(self, *args, **kwargs):
        self.launches += 1
        return super().launch(*args, **kwargs)


def test_recover_rejected_submission_preserves_attempt(study_project, monkeypatch):
    root, _, _, _ = study_project
    blocked = blocked_submission(study_project, monkeypatch)
    attempt = blocked.attempts[0]
    staging = root / ".waterology/staging" / attempt.run_id
    originals = {name: (staging / name).read_bytes() for name in ("execution-config.json", "torc-workflow.yaml", "study.json")}
    gateway = RecoveryGateway()
    recovered = studies.retry_submission(root, blocked.id, attempt.run_id, gateway=gateway)
    assert all((staging / name).read_bytes() == content for name, content in originals.items())
    assert (staging / "submission-recovery.json").is_file()
    assert recovered.state == "running"
    assert len(recovered.attempts) == 1
    assert recovered.attempts[0].run_id == attempt.run_id
    assert recovered.attempts[0].retry == 0
    assert recovered.attempts[0].commit_sha == attempt.commit_sha
    assert gateway.launches == 1
    with pytest.raises(studies.StudyError):
        studies.retry_submission(root, blocked.id, attempt.run_id, gateway=gateway)
    assert gateway.launches == 1

    # A recovered submission must complete the ordinary collection path while
    # preserving the original rejection and recovery evidence in its archive.
    from waterology import services
    from waterology.core.archive import verify_archive
    from waterology.torc.runs import inspect_torc_run

    evidence = (staging / "submission-recovery.json").read_bytes()
    _, worktree, machine, _ = study_project
    (worktree / "results").mkdir(exist_ok=True)
    (worktree / "results/metrics.json").write_text('{"error":0.5}')
    monkeypatch.setattr(
        services,
        "run_status",
        lambda p, r: inspect_torc_run(
            p, r, machine_config_file=machine, gateway=gateway
        ).model_dump(mode="json"),
    )
    completed = studies.advance_study(root, blocked.id)
    assert completed.state == "complete", completed.reason
    assert completed.best_run == attempt.run_id
    assert gateway.launches == 1
    archive = root / ".waterology/runs" / attempt.run_id
    assert (archive / "submission-recovery.json").read_bytes() == evidence
    assert verify_archive(archive).valid
    (archive / "submission-recovery.json").write_text("tampered")
    assert "submission-recovery.json" in verify_archive(archive).changed


@pytest.mark.parametrize("reason", ["found", "ambiguous", "inventory_error", "interrupted"])
def test_recovery_refuses_uncertain_submission(study_project, monkeypatch, reason):
    import json

    from waterology.torc.gateway import TorcUnavailableError

    root, _, _, _ = study_project
    blocked = blocked_submission(study_project, monkeypatch)
    attempt = blocked.attempts[0]
    staging = root / ".waterology/staging" / attempt.run_id
    gateway = RecoveryGateway()
    if reason == "found":
        gateway.items = ({"id": 42, "metadata": {"waterology_run_id": attempt.run_id}},)
    elif reason == "ambiguous":
        path = staging / "torc.json"
        payload = json.loads(path.read_text())
        payload["error"] = "connection timed out after 401 retries"
        path.write_text(json.dumps(payload))
    elif reason == "inventory_error":
        def unavailable(**kwargs):
            raise TorcUnavailableError("401 unauthorized")
        gateway.workflow_inventory = unavailable
    else:
        (staging / "submission-recovery.json").write_text('{"state":"launching"}')
    with pytest.raises((studies.StudyError, TorcUnavailableError)):
        studies.retry_submission(root, blocked.id, attempt.run_id, gateway=gateway)
    assert gateway.launches == 0


@pytest.mark.parametrize("change", ["commit", "profile", "workflow", "outputs", "stop"])
def test_recovery_keeps_execution_contract(study_project, monkeypatch, change):
    root, worktree, machine, _ = study_project
    blocked = blocked_submission(study_project, monkeypatch)
    attempt = blocked.attempts[0]
    staging = root / ".waterology/staging" / attempt.run_id
    if change == "commit":
        (worktree / "model.py").write_text("print(3)\n")
        git(worktree, "add", "model.py")
        git(worktree, "-c", "commit.gpgsign=false", "commit", "-qm", "changed")
    elif change == "profile":
        machine.write_text('[profiles.local]\nmode="local"\napi_url="http://other:8080"\n')
    elif change == "workflow":
        with (staging / "torc-workflow.yaml").open("a") as stream:
            stream.write("# changed\n")
    elif change == "outputs":
        (worktree / "results").mkdir()
        (worktree / "results/metrics.json").write_text('{"error":0.5}')
    else:
        studies._stop_path(root, blocked.id).write_text("{}")
    gateway = RecoveryGateway()
    with pytest.raises(studies.StudyError):
        studies.retry_submission(root, blocked.id, attempt.run_id, gateway=gateway)
    assert gateway.launches == 0


def test_failed_recovery_cannot_replay(study_project, monkeypatch):
    from waterology.torc.gateway import TorcUnavailableError

    root, _, _, _ = study_project
    blocked = blocked_submission(study_project, monkeypatch)
    attempt = blocked.attempts[0]

    class TimeoutGateway(RecoveryGateway):
        def launch(self, *args, **kwargs):
            self.launches += 1
            raise TorcUnavailableError("timed out")

    gateway = TimeoutGateway()
    for _ in range(2):
        with pytest.raises(studies.StudyError):
            studies.retry_submission(root, blocked.id, attempt.run_id, gateway=gateway)
    assert gateway.launches == 1


def test_concurrent_submission_recovery_launches_once(study_project, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    root, _, _, _ = study_project
    blocked = blocked_submission(study_project, monkeypatch)
    attempt = blocked.attempts[0]
    gateway = RecoveryGateway()
    barrier = Barrier(2)

    def retry():
        barrier.wait(timeout=10)
        try:
            return studies.retry_submission(root, blocked.id, attempt.run_id, gateway=gateway).state
        except studies.StudyError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: retry(), range(2)))
    assert sorted(results) == ["refused", "running"]
    assert gateway.launches == 1


def test_recovery_cli_does_not_print_credentials(study_project, monkeypatch):
    from typer.testing import CliRunner

    from waterology.cli import app
    from waterology.torc import submission_recovery

    root, _, _, _ = study_project
    blocked = blocked_submission(study_project, monkeypatch)
    gateway = RecoveryGateway()
    monkeypatch.setenv("TORC_PASSWORD", "private-test-password")
    monkeypatch.setattr(submission_recovery, "TorcCliGateway", lambda url: gateway)
    result = CliRunner().invoke(app, [
        "study", "retry-submission", blocked.id, blocked.attempts[0].run_id,
        "--path", str(root),
    ])
    assert result.exit_code == 0, result.output
    assert "private-test-password" not in result.output
    assert gateway.launches == 1


def test_stop_during_inventory_prevents_recovery(study_project, monkeypatch):
    root, _, _, _ = study_project
    blocked = blocked_submission(study_project, monkeypatch)
    gateway = RecoveryGateway()

    def inventory(**kwargs):
        studies._stop_path(root, blocked.id).write_text("{}")
        return {"items": []}

    gateway.workflow_inventory = inventory
    with pytest.raises(studies.StudyError, match="stopped"):
        studies.retry_submission(root, blocked.id, blocked.attempts[0].run_id, gateway=gateway)
    assert gateway.launches == 0


def test_recovery_accepts_explicit_forbidden_create(study_project, monkeypatch):
    import json

    root, _, _, _ = study_project
    blocked = blocked_submission(study_project, monkeypatch)
    attempt = blocked.attempts[0]
    metadata = root / ".waterology/staging" / attempt.run_id / "torc.json"
    payload = json.loads(metadata.read_text())
    payload["error"] = payload["error"].replace("401", "403").replace("Unauthorized", "Forbidden")
    metadata.write_text(json.dumps(payload))
    gateway = RecoveryGateway()
    assert studies.retry_submission(root, blocked.id, attempt.run_id, gateway=gateway).state == "running"
    assert gateway.launches == 1


def test_recovery_rechecks_pinned_input_bytes(study_project, monkeypatch):
    import hashlib

    root, worktree, machine, spec = study_project
    (worktree / "results").mkdir()
    source = worktree / "results/input.txt"
    source.write_text("original input")
    spec = spec.model_copy(update={"input_files": {"results/input.txt": hashlib.sha256(source.read_bytes()).hexdigest()}})
    blocked = blocked_submission((root, worktree, machine, spec), monkeypatch)
    source.write_text("changed input")
    gateway = RecoveryGateway()
    with pytest.raises(studies.StudyError, match="Input identity mismatch"):
        studies.retry_submission(root, blocked.id, blocked.attempts[0].run_id, gateway=gateway)
    assert gateway.launches == 0
