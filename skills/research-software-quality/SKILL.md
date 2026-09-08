---
name: research-software-quality
description: Use when changing research software or agent behavior, diagnosing failures, deciding whether work needs an isolated Git worktree, reviewing a substantial change, or making a completion claim.
---

# Research Software Quality

Match the workflow to the change's risk, size, and isolation needs. Preserve
evidence, reproducibility, and user intent without imposing a fixed ceremony.

## Route the task

- For code changes, bugs, test failures, or unexpected behavior, read
  [testing-and-debugging.md](references/testing-and-debugging.md).
- Before any success claim, and when deciding whether independent review adds
  value, read [verification-and-review.md](references/verification-and-review.md).
- Before editing a repository, inspect the current isolation state and apply
  [worktrees.md](references/worktrees.md).

## Proportional workflow

| Change | Expected process |
| --- | --- |
| Read-only inspection or explanation | Gather enough evidence to support the answer. Do not create a worktree. |
| Documentation, comments, formatting, or one small non-generated file | Work in place only if every optional-worktree condition passes. Run focused checks. |
| Executable code, tests, dependencies, build, CI, schema, manifest, agent, skill, hook, or generated asset | Use an isolated worktree and test the changed behavior when practical. |
| Broad, risky, or publication-facing deliverable | Add full relevant verification and an independent review when available and authorized. |

Skills and agent instructions change behavior even when their files are
Markdown. Treat them as behavior changes.

## Verification and Validation 

Analysis should be compared against known baselines (eg. existing data, 
physical relationships, expert knowledge). Modeling decisions need to be 
similarly justified through literature citations and/or sound scientific 
reasoning.

## Persistence

For substantial work in an initialized project, use `project-learning` to
retrieve relevant verified lessons before planning. After verification or a
meaningful failure recovery, record the supported lesson and its evidence.
Keep shared workflow changes as reviewable proposals. This completes
plan -> test -> implement -> review -> verify -> remember -> improve without
requiring every phase for a trivial change.

Continue while the requested outcome and the next safe action are clear. A
failed command is evidence to investigate, not a reason to stop. Stop when
progress requires user input, new authority, external coordination, or a change
in scope. Do not invent permission or hide an unresolved failure behind a
completion claim.

## Boundaries

This skill does not require brainstorming, a specification, an implementation
plan, test driven development, a worktree, subagents, or separate reviews for
every task. It requires only the parts justified by the task and the worktree
cutoff.
