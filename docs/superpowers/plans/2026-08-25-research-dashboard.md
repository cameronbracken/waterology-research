# Slice 6 research dashboard implementation plan

## Goal

Add a local research dashboard that presents the state already owned by Waterology. The dashboard
will use the shared service layer so CLI, MCP, and browser views apply the same reconciliation and
validation rules. It will remain a local project tool and will not add hosted services, accounts, or
remote persistence.

## Boundaries

- Bind to `127.0.0.1` by default.
- Require both an explicit remote flag and an access token for a non-loopback bind.
- Keep durable records in the existing project files and SQLite index.
- Use Starlette, Jinja2, and Uvicorn as an optional package extra.
- Use server rendered HTML and a small checked in JavaScript module. Do not add a Node build.
- Keep TORC execution details in TORC. Show summaries and supported inspection links.
- Do not publish, push Git state, or delete remote data.

## Task 1: Dashboard package and optional dependencies

**Files:**

- Modify `pyproject.toml`, `pixi.toml`, and `pixi.lock`.
- Add `src/waterology/dashboard/` with package initialization.
- Extend packaging and doctor tests.

**Behavior:**

1. Add a `dashboard` extra for Starlette, Jinja2, and Uvicorn.
2. Keep imports lazy so core commands work without dashboard dependencies.
3. Package templates and static files in wheels and source distributions.
4. Report missing dashboard dependencies through `waterology doctor` without failing unrelated
   checks.

## Task 2: Shared dashboard queries and archive export

**Files:**

- Extend `src/waterology/services.py`.
- Add a bounded archive export helper in `src/waterology/core/archive.py` if no existing helper
  provides it.
- Add service and archive tests.

**Behavior:**

1. Build one dashboard snapshot containing project counts, experiments, reconciled sessions,
   evidence, artifact references, archives, assessments, and managed compute summaries.
2. Add shared wrappers for agent start and resume so browser actions do not duplicate CLI rules.
3. Export one sealed archive to an explicit destination with path, symlink, and overwrite checks.
4. Keep all returned values JSON serializable and reuse existing stable domain errors.

## Task 3: Application security and request handling

**Files:**

- Add `src/waterology/dashboard/app.py`, `security.py`, and focused tests.

**Behavior:**

1. Provide an application factory bound to one discovered Waterology project.
2. Allow loopback access without an access token. Reject non-loopback configuration unless the
   caller passes `allow_remote=True` and a nonblank token.
3. Authenticate remote requests with a constant time token comparison. Accept a token bootstrap
   query once, store it in an HTTP only same site cookie, and redirect to a clean URL.
4. Require same origin form posts, a dashboard action token, and an explicit confirmation value for
   state changing requests.
5. Return useful HTML error pages without exposing tracebacks or secrets.

## Task 4: Research views and live events

**Files:**

- Add Jinja templates, `static/dashboard.css`, and `static/dashboard.js`.
- Add route, theme, accessibility, and event tests.

**Behavior:**

1. Add Overview, Experiments, Agents, Evidence, Archives, and Compute views.
2. Put the experiment tree, active agents, recent evidence, and compute state in the first viewport.
3. Show hypotheses, parents, commits, assessments, run manifests, logs, artifacts, ownership, and
   resume context on their relevant pages.
4. Use earth tones, light and dark themes, visible text status labels, accessible landmarks, and
   responsive layouts.
5. Render useful pages without JavaScript. Add an event stream that sends updated summary counts and
   lets the small JavaScript module refresh visible state.

## Task 5: Guarded research actions

**Files:**

- Add POST routes and action tests.
- Extend shared services where an action is not already exposed.

**Behavior:**

1. Support experiment creation, agent start and resume, run start and cancellation, run assessment,
   and sealed archive export.
2. Call only shared service functions. Preserve their validation and event recording.
3. Use POST then redirect. Show a concise success or error notice on the destination view.
4. Require explicit confirmation for cancellation and archive export.

## Task 6: CLI launch and lifecycle

**Files:**

- Add `src/waterology/dashboard/server.py`.
- Modify `src/waterology/cli.py` and CLI tests.

**Behavior:**

1. Add `waterology dashboard` with project path, host, port, browser, remote, and token options.
2. Open the browser only after the selected loopback server is ready. Support `--no-open` for SSH,
   tests, and headless use.
3. Refuse an unsafe host or missing token before starting Uvicorn.
4. Print the local URL and stop cleanly on interruption.

## Task 7: Documentation, browser review, and release checks

**Files:**

- Update `README.md` and `ROADMAP.md`.
- Add dashboard wheel and documentation tests.

**Behavior:**

1. Document installation, local launch, SSH forwarding, remote token rules, views, actions, and the
   JavaScript free fallback.
2. Exercise a representative project through route, permission, action, event, and CLI tests.
3. When an interactive browser is available, start the local server with representative research
   records and inspect every view at desktop and narrow widths. Check keyboard navigation, theme
   behavior, empty states, forms, and error notices. If the browser backend is unavailable, record
   that limitation and substitute installed live route checks plus automated responsive, keyboard,
   theme, form, empty state, notice, and contrast checks. Manual visual inspection remains a release
   follow-up and does not block the local code slice.
4. Run:

```bash
pixi run pytest
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
git diff --check
```

5. Build the wheel and source distribution, install the dashboard extra in a clean environment, and
   run a server and route smoke test from the installed wheel.
6. Request an independent review, resolve release blockers, repeat the required checks, and create a
   signed commit. Do not merge, push, or deploy without permission.

## Completion evidence

- Repository checks passed on 2026-08-25: 457 tests, Ruff, generated asset comparison, all three
  constraints, and `git diff --check`.
- Built `waterology_research-0.3.0.tar.gz` and `waterology_research-0.3.0-py3-none-any.whl` from the
  final candidate. Installed the wheel with its dashboard extra in a clean Python 3.14 environment.
- Started the installed CLI against a representative project. Overview, Experiments, Agents,
  Evidence, Archives, Compute, the stylesheet, and a one-shot event stream all returned HTTP 200.
- The in-app browser backend was unavailable. Browser screenshots at desktop and narrow widths
  could not be recorded. Automated checks cover server rendered content, skip navigation,
  responsive CSS, theme controls, guarded forms, representative detail pages, and WCAG AA button
  contrast.
- The first independent review returned no-go with eight blocker groups. The candidate now includes
  regressions and fixes for Host validation, event loop blocking, browser readiness, export
  integrity, direct and TORC state reconciliation, missing view content, remote confirmation, and
  dark theme contrast. The final independent re-review returned go with no remaining release
  blockers.
