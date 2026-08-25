import asyncio
import subprocess
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

import waterology.dashboard.app as dashboard_module
from waterology.core.project import initialize_project
from waterology.dashboard.app import create_dashboard_app
from waterology.dashboard.security import DashboardSecurityError


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "study"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.org"], check=True
    )
    initialize_project(root)
    (root / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(root), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "commit", "--quiet", "-m", "base"], check=True)
    return root


@pytest.mark.parametrize(
    ("path", "heading"),
    (
        ("/", "Research overview"),
        ("/experiments", "Experiments"),
        ("/agents", "Agents"),
        ("/evidence", "Evidence"),
        ("/archives", "Archives"),
        ("/compute", "Compute"),
    ),
)
def test_research_views_render_without_javascript(
    tmp_path: Path, path: str, heading: str
) -> None:
    app = create_dashboard_app(make_project(tmp_path))

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(path)

    assert response.status_code == 200
    assert heading in response.text
    assert '<main id="main-content" tabindex="-1">' in response.text
    assert 'data-theme="system"' in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_non_loopback_configuration_requires_explicit_token(tmp_path: Path) -> None:
    root = make_project(tmp_path)

    with pytest.raises(DashboardSecurityError, match="explicit remote access"):
        create_dashboard_app(root, host="0.0.0.0")
    with pytest.raises(DashboardSecurityError, match="access token"):
        create_dashboard_app(root, host="0.0.0.0", allow_remote=True)


def test_remote_token_bootstrap_sets_cookie_and_cleans_url(tmp_path: Path) -> None:
    app = create_dashboard_app(
        make_project(tmp_path),
        host="0.0.0.0",
        allow_remote=True,
        access_token="secret-token",
    )

    with TestClient(app, base_url="http://192.0.2.10") as client:
        denied = client.get("/")
        bootstrap = client.get("/?token=secret-token", follow_redirects=False)
        allowed = client.get("/")

    assert denied.status_code == 401
    assert denied.headers["x-frame-options"] == "DENY"
    assert bootstrap.status_code == 303
    assert bootstrap.headers["location"] == "/"
    assert "waterology_dashboard=" in bootstrap.headers["set-cookie"]
    assert "HttpOnly" in bootstrap.headers["set-cookie"]
    assert allowed.status_code == 200


def test_mutation_requires_origin_action_token_and_confirmation(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = create_dashboard_app(root)
    form = {
        "action_token": app.state.action_token,
        "confirm": "create",
        "experiment_id": "exp-browser",
        "hypothesis": "The guarded dashboard uses shared services.",
    }

    with TestClient(app, base_url="http://127.0.0.1") as client:
        missing_origin = client.post("/actions/experiments", data=form)
        missing_confirmation = client.post(
            "/actions/experiments",
            data={**form, "confirm": ""},
            headers={"origin": "http://127.0.0.1"},
        )
        created = client.post(
            "/actions/experiments",
            data=form,
            headers={"origin": "http://127.0.0.1"},
            follow_redirects=False,
        )
        experiments = client.get("/experiments")
        detail = client.get("/experiments/exp-browser")

    assert missing_origin.status_code == 403
    assert missing_confirmation.status_code == 400
    assert created.status_code == 303
    assert created.headers["location"].startswith("/experiments?")
    assert "exp-browser" in experiments.text
    assert detail.status_code == 200
    assert "The guarded dashboard uses shared services." in detail.text


def test_event_stream_returns_json_summary(tmp_path: Path) -> None:
    app = create_dashboard_app(make_project(tmp_path))

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/events?once=1")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: summary" in response.text
    assert '"experiments": 0' in response.text


@pytest.mark.parametrize(
    ("route", "service_name", "confirmation", "form"),
    (
        (
            "/actions/agents/start",
            "start_agent_session",
            "start",
            {"experiment_id": "exp-one", "task": "Compare results."},
        ),
        (
            "/actions/agents/resume",
            "resume_agent_session",
            "resume",
            {"session_id": "session-1111111111111111", "prompt": "Continue."},
        ),
        (
            "/actions/runs/start",
            "start_run",
            "start",
            {"experiment_id": "exp-one", "profile": "cluster", "confirm_remote": "yes"},
        ),
        (
            "/actions/runs/cancel",
            "cancel_run",
            "cancel",
            {"run_id": "run-one"},
        ),
        (
            "/actions/assessments",
            "assess_run_record",
            "assess",
            {
                "run_id": "run-one",
                "kind": "no_answer",
                "conclusion": "The run does not answer the hypothesis.",
                "author": "Test",
            },
        ),
        (
            "/actions/archives/export",
            "export_archive",
            "export",
            {"run_id": "run-one", "destination": "exports/run-one.tar.gz"},
        ),
    ),
)
def test_guarded_action_routes_call_shared_services(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    service_name: str,
    confirmation: str,
    form: dict[str, str],
) -> None:
    app = create_dashboard_app(make_project(tmp_path))
    calls: list[tuple[object, ...]] = []

    def record(*args: object, **kwargs: object) -> dict[str, str]:
        calls.append((*args, kwargs))
        return {"status": "pass"}

    monkeypatch.setattr(dashboard_module.services, service_name, record)
    payload = {**form, "action_token": app.state.action_token, "confirm": confirmation}

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            route,
            data=payload,
            headers={"origin": "http://127.0.0.1"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert calls
    if service_name == "start_run":
        assert calls[0][-1]["confirm_remote"] is True  # type: ignore[index]


def test_views_include_planned_research_context(tmp_path: Path) -> None:
    app = create_dashboard_app(make_project(tmp_path))
    expected = {
        "/": ("Experiment tree", "Active agents", "Recent evidence", "Compute state"),
        "/evidence": ("Run metrics", "Experiment notes"),
        "/compute": ("TORC profiles", 'name="confirm_remote"'),
    }

    with TestClient(app, base_url="http://127.0.0.1") as client:
        responses = {path: client.get(path) for path in expected}

    for path, phrases in expected.items():
        assert responses[path].status_code == 200
        assert all(phrase in responses[path].text for phrase in phrases)


def test_confirmation_prompt_stays_on_one_label_line(tmp_path: Path) -> None:
    app = create_dashboard_app(make_project(tmp_path))

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/experiments")

    assert '<span>Type <code>create</code> to confirm</span>' in response.text


def test_detail_views_include_resume_and_archive_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_dashboard_app(make_project(tmp_path))
    monkeypatch.setattr(
        dashboard_module.services,
        "session_status",
        lambda _path, _session_id: {
            "id": "session-1111111111111111",
            "state": "waiting",
            "runtime": "codex",
            "role": "researcher",
            "compute_profile": "local",
            "native_session_id": "native-42",
            "worktree": ".waterology/worktrees/exp-one",
            "task": "Compare the candidate metrics.",
        },
    )
    monkeypatch.setattr(dashboard_module.services, "session_logs", lambda *_args: [])
    monkeypatch.setattr(
        dashboard_module.services,
        "run_status",
        lambda _path, _run_id: {
            "run_id": "run-one",
            "terminal_state": "completed",
            "experiment_id": "exp-one",
            "commit_sha": "a" * 40,
            "executor": "direct",
            "collected_artifacts": ["artifacts/figure.svg"],
        },
    )
    monkeypatch.setattr(
        dashboard_module.services,
        "run_logs",
        lambda *_args: {"stdout": "finished", "stderr": ""},
    )
    monkeypatch.setattr(dashboard_module.services, "run_metrics", lambda *_args: {"rmse": 1.2})

    with TestClient(app, base_url="http://127.0.0.1") as client:
        agent = client.get("/agents/session-1111111111111111")
        archive = client.get("/archives/run-one")

    assert agent.status_code == 200
    assert "Task and resume context" in agent.text
    assert "Compare the candidate metrics." in agent.text
    assert archive.status_code == 200
    assert "Run manifest" in archive.text
    assert "source.tar.zst" in archive.text
    assert "figure.svg" in archive.text


def test_untrusted_host_cannot_read_token_or_reach_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_dashboard_app(make_project(tmp_path))
    called = False

    def record(*args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(dashboard_module.services, "create_experiment_record", record)
    form = {
        "action_token": app.state.action_token,
        "confirm": "create",
        "hypothesis": "Host validation blocks this request.",
    }
    with TestClient(app, base_url="http://127.0.0.1") as client:
        page = client.get("/experiments", headers={"host": "attacker.example:8139"})
        action = client.post(
            "/actions/experiments",
            data=form,
            headers={"host": "attacker.example:8139", "origin": "http://attacker.example:8139"},
        )

    assert page.status_code == 400
    assert app.state.action_token not in page.text
    assert action.status_code == 400
    assert called is False


def test_blocking_snapshot_does_not_hold_event_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_dashboard_app(make_project(tmp_path))
    original = dashboard_module.services.dashboard_snapshot
    started = False

    def slow_snapshot(path: Path) -> dict[str, object]:
        nonlocal started
        started = True
        time.sleep(0.25)
        return original(path)

    monkeypatch.setattr(dashboard_module.services, "dashboard_snapshot", slow_snapshot)

    async def exercise() -> tuple[int, float]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            page = asyncio.create_task(client.get("/"))
            while not started:
                await asyncio.sleep(0.005)
            before = time.monotonic()
            static = await client.get("/static/dashboard.css")
            elapsed = time.monotonic() - before
            await page
            return static.status_code, elapsed

    status_code, elapsed = asyncio.run(exercise())
    assert status_code == 200
    assert elapsed < 0.15
