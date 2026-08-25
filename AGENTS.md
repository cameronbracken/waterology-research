# AGENTS.md

## Purpose

Waterology is a research workflow package for Claude Code, Codex, and OpenCode.

## Source layout

Root `skills/` and `agent-definitions/` are canonical. Runtime agent files in
`agents/`, `.codex/agents/`, and `.opencode/agents/` are generated. Do not edit
generated runtime files.

## Development

Use Pixi and run:

```bash
pixi run pytest
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
```

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

Sign commits with the personal identity. Do not add coauthor trailers. Do not
push without permission.

## Scope

Experiment storage, TORC, agent sessions, MCP, and the dashboard belong to
later plans.
