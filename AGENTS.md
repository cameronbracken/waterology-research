# AGENTS.md

## Purpose

Waterology is a research workflow package for Claude Code, Codex, OpenCode, and Pi.

## Source layout

Root `skills/` and `agent-definitions/` are canonical. Runtime agent files in
`agents/`, `.codex/agents/`, `.opencode/agents/`, and `pi-agents/` are generated.
Do not edit generated runtime files.

## Development

Use Pixi and run:

```bash
pixi run pytest
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
```

These commands form the full validation suite for new development. Run
Waterology constraints only for applicable files changed since their last
successful check. Skip them for read only work and unchanged validated content.
Use the whole repository target when a constraint changes or full repository
validation is required.

## Quality

Use `research-software-quality` for testing, debugging, verification, review,
and worktree decisions. Prefer a failing test first for clear behavior changes.
Match completion claims to fresh evidence.

## Skill edits

Use `writing-style` for prose. Treat skill and agent instruction edits as
behavior changes that require an isolated worktree. Edit and validate one skill
at a time.

## Attribution

For adapted work, update the file header and `ATTRIBUTION.md`.

## Git

Sign commits with the personal identity on personal machine. Do not add coauthor trailers. Do not
push without permission.

Create descriptive branchnames eg. `feature/my-feature`, `bug/my-bug`, NOT `codex/my-feature`.

## Scope

Experiment storage, TORC, agent sessions, MCP, and the dashboard are implemented.
Extend their shared service and durable record layers. See docs/managed-studies.md
for bounded autonomous execution and its validation boundaries.
