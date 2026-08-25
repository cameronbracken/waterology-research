# Agent Sessions and MCP Implementation Plan

**Goal:** Add durable top level agent sessions and a local MCP interface over the existing
Waterology service layer.

**Branch:** `codex/slice-5-agent-sessions-mcp`

**Worktree:** `.worktrees/slice-5-agent-sessions-mcp`

**Base:** Slice 4 TORC integration at `374df5a`

## Current runtime contracts

This plan follows the current command interfaces documented by the official
[Codex CLI reference](https://developers.openai.com/codex/cli/reference),
[Claude Code headless guide](https://code.claude.com/docs/en/headless), and
[OpenCode CLI reference](https://dev.opencode.ai/docs/cli/). Claude Code and Codex emit structured
JSONL in noninteractive mode and expose native resume commands. OpenCode emits JSON events and
resumes with an explicit session identifier. Waterology will preserve those native identifiers and
events instead of defining a transcript format.

The local server will use the stable version 2 line of the official
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk). The server will use stdio, keep
stdout reserved for protocol messages, and expose typed tools that call the same Python services as
the CLI. The SDK will remain an optional dependency.

## Scope

The slice includes:

- Process adapters for Claude Code, Codex, and OpenCode using argument arrays and structured event
  streams.
- Durable session records, task briefs, attempts, logs, native runtime identifiers, process
  metadata, and resulting commits.
- Atomic ownership that prevents two writable top level sessions from sharing one experiment
  worktree.
- Native resume, safe interruption, process reconciliation, and index repair from session records.
- `waterology agent start|list|status|logs|resume|stop` with stable JSON output.
- A local stdio MCP server for bounded experiment, run, archive, evidence, artifact, and session
  note operations.
- Runtime configuration snippets and doctor checks for the optional MCP SDK and agent binaries.

Runtime native subagents remain under runtime control. Waterology will not normalize private
transcripts, expose a shell MCP tool, manage credentials, or publish changes. The research dashboard
belongs to Slice 6.

## Task 1: Durable session and evidence records

**Files:**

- Modify `src/waterology/core/project.py` and `src/waterology/core/records.py`.
- Add `src/waterology/core/migrations/003_agent_sessions.sql`.
- Create `src/waterology/core/sessions.py` and `src/waterology/core/evidence.py`.
- Create focused tests under `tests/core/`.

**Behavior:**

1. Write failing tests for strict session manifests, attempts, notes, evidence, and artifact
   references before implementation.
2. Add `.waterology/sessions/<session-id>/session.json`, `task.md`, attempt event logs, and stderr
   logs. Write mutable session records atomically and reject symlinks or paths outside project
   state.
3. Index sessions, attempts, notes, evidence, and artifact references in SQLite. Add a partial
   unique index that permits only one active writable session for a worktree.
4. Keep durable JSON and JSONL as the recovery source. Database rows remain a coordination and
   query index.

## Task 2: Runtime adapter protocol and command builders

**Files:**

- Create `src/waterology/agents/base.py`, `claude.py`, `codex.py`, and `opencode.py`.
- Create `tests/agents/test_adapters.py`.

**Behavior:**

1. Define typed `launch -> inspect -> resume -> interrupt -> collect` records and an injectable
   process boundary.
2. Build commands as argument arrays with an explicit worktree, self contained task brief, role,
   compute profile, artifact location, and MCP guidance.
3. Parse structured events conservatively to recover native session identifiers and terminal
   results. Preserve unknown events unchanged in the attempt log.
4. Reject unsupported runtimes, missing executables, malformed events, and invalid resume state
   with stable Waterology errors. Never pass credentials or the full inherited environment into a
   stored record.

## Task 3: Background supervision and reconciliation

**Files:**

- Create `src/waterology/agents/supervisor.py` and `src/waterology/agents/worker.py`.
- Extend session and adapter tests.

**Behavior:**

1. Start a small detached Waterology supervisor that owns the runtime child, streams stdout and
   stderr to append only logs, and writes terminal observations atomically.
2. Record supervisor and runtime process identifiers, start time, exit code, native session ID, and
   commit before and after each attempt.
3. Reconcile active sessions from durable result records and process liveness. A missing process
   without a terminal result becomes `lost`; its logs, worktree, and native ID remain available.
4. Release worktree ownership only for terminal states. Process creation failure must also release
   ownership while preserving the failed session record.

## Task 4: Resume and interruption

**Files:**

- Extend `src/waterology/core/sessions.py` and the runtime adapters.
- Extend agent lifecycle tests.

**Behavior:**

1. Resume only a terminal or waiting session with a recorded native identifier and a free original
   worktree. Store each resume as a numbered attempt with its own prompt and logs.
2. Use each runtime's native resume command. Do not replay or translate transcript content.
3. Interrupt only the recorded active process group. Record request and observed outcome, make
   repeated stop requests safe, and never target an unverified or reused process identifier.
4. Collect resulting commits and retain a clean distinction between `completed`, `failed`,
   `cancelled`, and `lost`.

## Task 5: Agent command line interface and diagnostics

**Files:**

- Modify `src/waterology/cli.py` and `src/waterology/runtime/doctor.py`.
- Create `tests/agents/test_agent_cli.py` and extend doctor tests.

**Behavior:**

1. Add `agent start`, `list`, `status`, `logs`, `resume`, and `stop` with human and stable JSON
   output.
2. Accept experiment, runtime, role, compute profile, and task file or task text. Require an
   initialized experiment worktree and refuse a second active writer.
3. Show session state, ownership, attempts, native ID, timestamps, process metadata, log paths, and
   resulting commits without exposing raw environments.
4. Add doctor checks for Claude Code, Codex, OpenCode, the MCP SDK, and the installed server entry
   point. Missing optional tools must not break core commands.

## Task 6: Bounded service operations

**Files:**

- Create `src/waterology/services.py` or a small `src/waterology/services/` package.
- Extend experiment, run, archive, assessment, session, evidence, and artifact tests.

**Behavior:**

1. Expose typed functions for project status, experiment creation and inspection, run start and
   inspection, run cancellation and assessment, logs and metrics, experiment trees, archives,
   evidence, artifact references, and session notes.
2. Reuse existing validation and mutation functions. CLI and MCP wrappers must not implement
   separate research rules.
3. Validate all project relative paths and identifiers at the service boundary. Evidence and
   artifact references must resolve inside an experiment worktree or sealed run archive.
4. Return JSON serializable models with stable error codes.

## Task 7: Local stdio MCP server

**Files:**

- Add an `mcp` optional dependency and `waterology-mcp` script in `pyproject.toml`.
- Create `src/waterology/mcp/server.py` and package initialization.
- Create `tests/mcp/test_server.py` and `tests/mcp/test_stdio.py`.

**Behavior:**

1. Build the server with MCP SDK version 2 and run it over stdio. Keep protocol output free of
   application prints and route diagnostics to stderr.
2. Register bounded tools for the service operations in Task 6. Tool docstrings will state side
   effects and required identifiers.
3. Do not register arbitrary commands, unrestricted file reads, shell access, Git publication, or
   remote deletion.
4. Test tool schemas and behavior directly, then run an end to end stdio handshake and representative
   read and mutation calls with the official client.

## Task 8: Runtime MCP registration

**Files:**

- Modify canonical runtime manifest or installer inputs only.
- Modify `src/waterology/runtime/render.py`, `install.py`, or supporting assets as required.
- Extend runtime render, installer, and packaging tests.

**Behavior:**

1. Generate project scoped stdio registration for Claude Code, Codex, and OpenCode using their
   supported configuration formats.
2. Register the installed `waterology-mcp` entry point with the project root as its working
   directory. Do not embed machine paths or credentials in packaged assets.
3. Preserve generated file ownership rules. Root skills and agent definitions remain canonical;
   generated runtime files must pass the existing render check.
4. Document manual registration commands for installations that cannot safely update an existing
   user configuration.

## Task 9: Repair, documentation, and release checks

**Files:**

- Modify `src/waterology/core/repair.py`, `README.md`, and `ROADMAP.md`.
- Extend repair, documentation, and wheel tests.

**Behavior:**

1. Rebuild session, attempt, note, evidence, and artifact reference rows from durable records.
   Reject unsupported schemas or malformed locations without replacing the current database.
2. Document session lifecycle, worktree ownership, resume behavior, log locations, MCP installation,
   registration, tools, and security limits.
3. Run focused tests after each task, then run:

```bash
pixi run pytest
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
git diff --check
```

4. Build the wheel and source distribution, then run packaging and MCP tests from the built wheel.
5. Request an independent review. Resolve release blockers, repeat the full checks, and create a
   signed commit. Do not merge or push without permission.

## Completion evidence

- `pixi run pytest`: 430 passed.
- `pixi run ruff check .`: passed.
- `pixi run waterology render --check`: generated assets current.
- `python3 constraints/check-all.py .`: 3 of 3 constraints passed.
- `git diff --check`: passed.
- Wheel and source distribution built successfully from the final candidate.
- The wheel installed with its MCP extra in a clean environment. Its stdio server completed the
  official client handshake, exposed 17 bounded tools, and completed project status and experiment
  creation calls.
- Installed Codex and OpenCode accepted and discovered their project MCP registrations.
- Independent lifecycle and release review found no remaining blockers.
