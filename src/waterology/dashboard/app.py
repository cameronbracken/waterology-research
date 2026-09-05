import asyncio
import json
import secrets
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urlencode

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from waterology import services
from waterology.core.errors import WaterologyError
from waterology.core.project import discover_project
from waterology.dashboard.security import (
    DashboardAccess,
    dashboard_access,
    request_host_allowed,
    require_action,
    token_matches,
)
from waterology.dashboard.workflows import workflow_routes

_COOKIE = "waterology_dashboard"
_VIEW_TITLES = {
    "overview": "Research overview",
    "experiments": "Experiments",
    "agents": "Agents",
    "evidence": "Evidence",
    "archives": "Archives",
    "compute": "Compute",
}


def create_dashboard_app(
    start: Path,
    *,
    host: str = "127.0.0.1",
    allow_remote: bool = False,
    access_token: str | None = None,
) -> Starlette:
    project = discover_project(start)
    access = dashboard_access(
        host,
        allow_remote=allow_remote,
        access_token=access_token,
    )
    action_token = secrets.token_urlsafe(32)
    package = Path(__file__).parent
    templates = Jinja2Templates(directory=package / "templates")

    def view_page(view: str) -> Callable[[Request], Awaitable[Response]]:
        async def endpoint(request: Request) -> Response:
            return await run_in_threadpool(
                _render_dashboard, templates, request, project.root, action_token, view
            )

        return endpoint

    async def experiment_detail(request: Request) -> Response:
        return await run_in_threadpool(
            lambda: _render_dashboard(
                templates,
                request,
                project.root,
                action_token,
                "experiment_detail",
                selected=services.experiment_status(
                    project.root, request.path_params["experiment_id"]
                ),
            )
        )

    async def agent_detail(request: Request) -> Response:
        session_id = request.path_params["session_id"]
        return await run_in_threadpool(
            lambda: _render_dashboard(
                templates,
                request,
                project.root,
                action_token,
                "agent_detail",
                selected=services.session_status(project.root, session_id),
                logs=services.session_logs(project.root, session_id),
            )
        )

    async def archive_detail(request: Request) -> Response:
        run_id = request.path_params["run_id"]
        return await run_in_threadpool(
            lambda: _render_dashboard(
                templates,
                request,
                project.root,
                action_token,
                "archive_detail",
                selected=services.run_status(project.root, run_id),
                logs=services.run_logs(project.root, run_id),
                metrics=services.run_metrics(project.root, run_id),
            )
        )

    async def events(request: Request) -> Response:
        once = request.query_params.get("once") == "1"

        async def stream():
            while True:
                snapshot = await run_in_threadpool(services.dashboard_snapshot, project.root)
                counts = snapshot["counts"]
                yield f"event: summary\ndata: {json.dumps(counts, sort_keys=True)}\n\n"
                if once or await request.is_disconnected():
                    return
                await asyncio.sleep(2)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    action_routes = _action_routes(project.root, action_token)
    routes = [
        Route("/", view_page("overview")),
        Route("/experiments", view_page("experiments")),
        Route("/experiments/{experiment_id}", experiment_detail),
        Route("/agents", view_page("agents")),
        Route("/agents/{session_id}", agent_detail),
        Route("/evidence", view_page("evidence")),
        Route("/archives", view_page("archives")),
        Route("/archives/{run_id}", archive_detail),
        Route("/compute", view_page("compute")),
        Route("/events", events),
        *action_routes,
        *workflow_routes(project.root, templates),
        Mount("/static", StaticFiles(directory=package / "static"), name="static"),
    ]
    app = Starlette(routes=routes, exception_handlers={WaterologyError: _domain_error})
    app.state.action_token = action_token
    app.state.project_root = project.root
    app.state.dashboard_access = access
    if access.remote:
        app.add_middleware(RemoteTokenMiddleware, access=access)
    app.add_middleware(SecurityHeadersMiddleware, configured_host=host)
    return app


def _render_dashboard(
    templates: Jinja2Templates,
    request: Request,
    project_root: Path,
    action_token: str,
    view: str,
    **extra: object,
) -> Response:
    snapshot = services.dashboard_snapshot(project_root)
    title = _VIEW_TITLES.get(view, view.replace("_", " ").title())
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "action_token": action_token,
            "error": request.query_params.get("error"),
            "notice": request.query_params.get("notice"),
            "snapshot": snapshot,
            "title": title,
            "view": view,
            **extra,
        },
    )


def _action_routes(project_root: Path, action_token: str) -> list[Route]:
    async def create_experiment(request: Request) -> Response:
        form = await require_action(
            request, action_token=action_token, confirmation="create"
        )
        return await run_in_threadpool(
            _run_action,
            "/experiments",
            "Experiment created",
            lambda: services.create_experiment_record(
                project_root,
                hypothesis=form.get("hypothesis", ""),
                parent_ref=form.get("parent_ref", "HEAD") or "HEAD",
                parent_experiment_id=form.get("parent_experiment_id") or None,
                owner=form.get("owner") or None,
                experiment_id=form.get("experiment_id") or None,
            ),
        )

    async def start_agent(request: Request) -> Response:
        form = await require_action(request, action_token=action_token, confirmation="start")
        return await run_in_threadpool(
            _run_action,
            "/agents",
            "Agent started",
            lambda: services.start_agent_session(
                project_root,
                form.get("experiment_id", ""),
                task=form.get("task", ""),
                runtime=form.get("runtime", "codex") or "codex",
                role=form.get("role", "researcher") or "researcher",
                profile=form.get("profile", "local") or "local",
            ),
        )

    async def resume_agent(request: Request) -> Response:
        form = await require_action(request, action_token=action_token, confirmation="resume")
        return await run_in_threadpool(
            _run_action,
            "/agents",
            "Agent resumed",
            lambda: services.resume_agent_session(
                project_root,
                form.get("session_id", ""),
                prompt=form.get("prompt", ""),
            ),
        )

    async def start_run(request: Request) -> Response:
        form = await require_action(request, action_token=action_token, confirmation="start")
        return await run_in_threadpool(
            _run_action,
            "/compute",
            "Run started",
            lambda: services.start_run(
                project_root,
                form.get("experiment_id", ""),
                profile=form.get("profile") or None,
                confirm_remote=form.get("confirm_remote") == "yes",
            ),
        )

    async def cancel_run(request: Request) -> Response:
        form = await require_action(request, action_token=action_token, confirmation="cancel")
        return await run_in_threadpool(
            _run_action,
            "/compute",
            "Run cancellation requested",
            lambda: services.cancel_run(project_root, form.get("run_id", "")),
        )

    async def assess(request: Request) -> Response:
        form = await require_action(request, action_token=action_token, confirmation="assess")
        evidence = tuple(
            item.strip() for item in form.get("evidence", "").splitlines() if item.strip()
        )
        return await run_in_threadpool(
            _run_action,
            "/archives",
            "Assessment recorded",
            lambda: services.assess_run_record(
                project_root,
                form.get("run_id", ""),
                kind=form.get("kind", ""),
                conclusion=form.get("conclusion", ""),
                author=form.get("author", ""),
                evidence=evidence,
                note=form.get("note") or None,
            ),
        )

    async def export_archive(request: Request) -> Response:
        form = await require_action(request, action_token=action_token, confirmation="export")
        return await run_in_threadpool(
            _run_action,
            "/archives",
            "Archive exported",
            lambda: services.export_archive(
                project_root,
                form.get("run_id", ""),
                form.get("destination", ""),
            ),
        )

    return [
        Route("/actions/experiments", create_experiment, methods=["POST"]),
        Route("/actions/agents/start", start_agent, methods=["POST"]),
        Route("/actions/agents/resume", resume_agent, methods=["POST"]),
        Route("/actions/runs/start", start_run, methods=["POST"]),
        Route("/actions/runs/cancel", cancel_run, methods=["POST"]),
        Route("/actions/assessments", assess, methods=["POST"]),
        Route("/actions/archives/export", export_archive, methods=["POST"]),
    ]


def _run_action(
    destination: str,
    notice: str,
    action: Callable[[], object],
) -> RedirectResponse:
    try:
        action()
    except (OSError, TypeError, ValueError, WaterologyError) as error:
        query = urlencode({"error": str(error)})
    else:
        query = urlencode({"notice": notice})
    return RedirectResponse(f"{destination}?{query}", status_code=303)


async def _domain_error(request: Request, error: Exception) -> HTMLResponse:
    del request
    return HTMLResponse(
        "<!doctype html><title>Waterology dashboard error</title>"
        "<h1>Dashboard request failed</h1>"
        f"<p>{_escape(str(error))}</p>",
        status_code=400,
    )


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class RemoteTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, access: DashboardAccess) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        assert access.access_token is not None
        self.access_token = access.access_token

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        query_token = request.query_params.get("token")
        if query_token is not None:
            if not token_matches(query_token, self.access_token):
                return HTMLResponse("Dashboard access token is invalid", status_code=401)
            query = urlencode(
                [(name, value) for name, value in request.query_params.multi_items() if name != "token"]
            )
            location = request.url.path + (f"?{query}" if query else "")
            response = RedirectResponse(location, status_code=303)
            response.set_cookie(
                _COOKIE,
                self.access_token,
                httponly=True,
                samesite="strict",
                secure=request.url.scheme == "https",
            )
            return response
        if not token_matches(request.cookies.get(_COOKIE), self.access_token):
            return HTMLResponse("Dashboard access token is required", status_code=401)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, configured_host: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.configured_host = configured_host

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not request_host_allowed(request.headers.get("host"), self.configured_host):
            response = HTMLResponse("Dashboard request host is invalid", status_code=400)
        else:
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response
