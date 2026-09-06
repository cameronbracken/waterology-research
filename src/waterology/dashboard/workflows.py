"""Read-only connected views for managed studies and sealed evidence."""

import html
import mimetypes
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, HTMLResponse
from starlette.routing import Route

from waterology.core.archive import verify_project_archive
from waterology.core.claims import _member
from waterology.core.comparison import compare_runs
from waterology.core.errors import WaterologyError
from waterology.core.studies import list_studies


def workflow_routes(root: Path, templates):
    async def studies(request):
        records = await run_in_threadpool(list_studies, root)
        return templates.TemplateResponse(
            request, "workflows.html", {"studies": records, "comparison": None}
        )

    async def comparison(request):
        run_ids = request.query_params.getlist("run")
        baseline = request.query_params.get("baseline", "")
        if baseline and baseline not in run_ids:
            run_ids.insert(0, baseline)
        try:
            result = (
                await run_in_threadpool(lambda: compare_runs(root, run_ids, baseline=baseline))
                if run_ids
                else None
            )
        except ValueError as error:
            return HTMLResponse(str(error), status_code=400)
        return templates.TemplateResponse(
            request, "workflows.html", {"studies": None, "comparison": result}
        )

    async def artifact(request):
        try:
            run_id = request.path_params["run_id"]
            path = _member(root, run_id, request.path_params["member"])
            if not verify_project_archive(root, run_id).valid:
                return HTMLResponse("Archive integrity failed", status_code=409)
        except (WaterologyError, ValueError, OSError):
            return HTMLResponse("Artifact unavailable", status_code=404)
        # Active formats are downloads. They never execute with dashboard origin privileges.
        media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        inline = path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv", ".json"}
        return FileResponse(
            path,
            media_type=media if inline else "application/octet-stream",
            filename=path.name,
            content_disposition_type="inline" if inline else "attachment",
        )

    async def changes(request):
        from waterology.core.archive import load_archive
        from waterology.core.experiments import load_experiment
        from waterology.core.git import git_output

        try:
            run = load_archive(root, request.path_params["run_id"])
            if not verify_project_archive(root, run.run_id).valid:
                return HTMLResponse("Archive integrity failed", status_code=409)
            experiment = load_experiment(root, run.experiment_id)
            diff = git_output(
                root,
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--unified=3",
                experiment.base_commit,
                run.commit_sha,
            )
            truncated = len(diff) > 50000
            body = (
                "<h1>Recorded code changes</h1><p>"
                + html.escape(run.run_id)
                + "</p><pre>"
                + html.escape(diff[:50000])
                + "</pre>"
            )
            if truncated:
                body += "<p>Diff truncated. Inspect the recorded commits locally for the complete change.</p>"
            return HTMLResponse(
                '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/static/dashboard.css"></head><body><main>'
                + body
                + "</main></body></html>"
            )
        except (WaterologyError, ValueError, OSError):
            return HTMLResponse("Recorded code changes unavailable", status_code=404)

    async def registry(request):
        from waterology.core.project import discover_project
        config = await run_in_threadpool(lambda: discover_project(root).config)
        return templates.TemplateResponse(request, "registry.html", {"config": config})

    return [
        Route("/workflows", registry),
        Route("/studies", studies),
        Route("/changes/{run_id}", changes),
        Route("/comparison", comparison),
        Route("/artifacts/{run_id}/{member:path}", artifact),
    ]
