# Slice 2 Research Methods Implementation Plan

Date: 2026-08-25

Status: Complete

## Outcome

Move each research workflow into a canonical, runtime neutral skill. Keep the
Claude slash commands as generated compatibility shims. Finish the portable
OpenResearch delegation guidance, file headers, and repository attribution.

The slice is complete when Claude Code, Codex, and OpenCode receive the same
workflow from `skills/`, while Claude users can still invoke the existing
commands.

## Starting evidence

- Branch: `codex/slice-2-research-methods`
- Base revision: `1440eb7`
- Baseline: `pixi run pytest`, 147 passed on 2026-08-25
- Root `skills/` and `agent-definitions/` are canonical.
- Eleven skills still defer to Claude slash commands.
- `/summarize` has no portable skill and needs a new `source-summarization`
  skill.

## Progress

- [x] Task 1: Generate Claude command shims from skills.
- [x] Task 2: Migrate the short workflows.
- [x] Task 3: Migrate writing and review workflows.
- [x] Task 4: Migrate execution workflows.
- [x] Task 5: Migrate deep research.
- [x] Task 6: Add portable source summarization.
- [x] Task 7: Adapt delegation guidance.
- [x] Task 8: Complete attribution and documentation.

## Migration contract

Migrate one skill at a time. For each migration:

1. Define the observable cross runtime behavior in a focused test.
2. Run the test against the command backed skill and confirm the expected
   failure.
3. Move the durable workflow into `skills/<name>/SKILL.md` or a focused
   reference under that skill.
4. Replace the Claude command body with a generated shim that invokes the
   skill with `$ARGUMENTS`.
5. Render generated assets and run the focused skill, renderer, validation,
   and packaging checks.
6. Finish the skill before editing the next one.

Tests should exercise portable invariants, metadata parsing, rendering, and
artifact contracts. They should not freeze headings or long passages of prose.

## Command mapping

| Claude command | Canonical skill | Change |
| --- | --- | --- |
| `/log` | `session-log` | Migrate |
| `/audit` | `paper-code-audit` | Migrate |
| `/compare` | `source-comparison` | Migrate |
| `/watch` | `watch` | Migrate |
| `/draft` | `paper-writing` | Migrate |
| `/lit` | `literature-review` | Migrate |
| `/review` | `research-review` | Migrate |
| `/recipe` | `ml-training-recipe` | Migrate |
| `/replicate` | `replication` | Migrate |
| `/autoresearch` | `autoresearch` | Migrate |
| `/deepresearch` | `deep-research` | Migrate |
| `/summarize` | `source-summarization` | Create |

The order starts with small workflows so the renderer and validation contract
can settle before the larger research protocols move.

## Task 1: Generate Claude command shims from skills

Extend skill metadata with an optional Claude command block containing the
command name, argument hint, and any justified tool restriction. Add a parser
and renderer that produces `commands/*.md` from the canonical skill. The shim
must name the skill, pass `$ARGUMENTS`, carry a generated file marker, and avoid
copying the workflow body.

`waterology render` and `waterology render --check` must cover commands and
agents together. Validation must report malformed command metadata, duplicate
command names, and orphaned or stale generated shims.

Start Task 1 with `session-log` so the feature is implemented against a real,
small migration rather than a synthetic example.

## Task 2: Migrate the short workflows

Migrate `session-log`, `paper-code-audit`, `source-comparison`, and `watch` in
that order. Preserve their artifact paths, source checks, agent use, and
authorization boundaries. Remove every instruction to run a slash command
from the canonical skills.

## Task 3: Migrate writing and review workflows

Migrate `paper-writing`, `literature-review`, and `research-review`. Preserve
the evidence first writing contract, multi-hop literature search, severity
graded review, and the existing use of `writing-style`.

## Task 4: Migrate execution workflows

Migrate `ml-training-recipe`, `replication`, and `autoresearch`. Preserve the
explicit environment choice before replication execution, fixed assessment
vocabulary, benchmark evidence, experiment logs, and stopping conditions.

## Task 5: Migrate deep research

Move the full deep research protocol into the canonical skill. Keep detailed
procedures in focused references when that reduces the default context load.
Preserve scale based delegation, source verification, degraded output, review,
provenance, and the requirement to leave a final artifact on disk.

## Task 6: Add portable source summarization

Create `source-summarization` from `/summarize`. Keep the bounded read design,
input guards, three size tiers, checkpoint files, coverage reporting, and
single source citation rule. Replace Claude `Task` terminology with capability
based delegation. Update `eli5` to route long sources to the new skill.

## Task 7: Adapt delegation guidance

Review the canonical researcher, writer, verifier, and reviewer definitions
against the portable OpenResearch guidance at pinned commit
`13049867497de8fd5e15253cd818462629edd690`. Keep task briefs, file ownership,
compute authorization, and return contracts. Remove `orx`, hosted service,
provider API, and product assumptions. Render all runtime agents after each
canonical change.

## Task 8: Complete attribution and documentation

Add a source header to every adapted skill, reference, agent definition, and
generated command template. Update `ATTRIBUTION.md` with original paths,
license, pinned revision, and substantive adaptations. Mark Slice 2 complete in
`ROADMAP.md` only after all acceptance checks pass. Update the README to state
that research workflows are runtime neutral and commands are Claude
compatibility shims.

## Acceptance checks

Run these commands after the final edit:

```bash
pixi run pytest
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
```

Also build and inspect the wheel. Confirm that it contains canonical skills,
generated commands, generated agents, attribution, and no local state or
secrets.

Request an independent review before integration because this slice changes
all research workflow behavior and generated runtime assets.
