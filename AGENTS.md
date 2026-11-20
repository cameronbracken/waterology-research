# AGENTS.md

## Purpose

Waterology is a lightweight research workflow, deliverable, and reference package for Antigravity, Claude Code, Codex, OpenCode, and Pi.

## Source layout

Root `skills/` and `agent-definitions/` are canonical. Runtime agent files in
`.agent/agents/`, `agents/`, `.codex/agents/`, `.opencode/agents/`, and `pi-agents/`
(along with `commands/`, `pi-skills/`, and `pi-prompts/`) are generated.
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

## File formats

Follow the format table in `skills/project-conventions/SKILL.md`. Hand-edited
settings (such as `.zotero.toml` and `~/.config/waterology/config.toml`) are TOML.
Structured records Waterology writes (under `.waterology/literature/` and
`.waterology/references/`) are YAML through `waterology.core.atomic` and
`waterology.core.formats`. Use JSON only where another tool or specification
requires it.

## Skill edits

Use `writing-style` for prose. Treat skill and agent instruction edits as
behavior changes. Make them on a named branch, and use a worktree when another
session may edit this checkout. Validate each changed skill with `pixi run waterology validate`.

## Reproducibility mode

`skills/project-conventions/SKILL.md` defines `light` (the default) and `strict`
modes. Other skills and agents point to that definition rather than restating it.

## Attribution

For adapted work, update the agent header (for canonical agents) and `ATTRIBUTION.md`.
Skills and rules keep upstream attribution in `ATTRIBUTION.md` rather than inline comments.

## Git

Sign commits with the personal identity on personal machine. Do not add coauthor trailers. Do not
push without permission.

Create descriptive branchnames eg. `feature/my-feature`, `fix/my-bug`, NOT `codex/my-feature`.

## Scope

Keep Waterology focused on conventions, deliverable templates, deterministic verifiers,
and bounded scholarly/Zotero/Hugging Face reference tools (`waterology.core` and
`waterology.mcp`). Avoid adding heavy state databases, process supervisors, or
shell round-trips to routine skill execution.
