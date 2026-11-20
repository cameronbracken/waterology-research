---
name: research-software-quality
description: Use when changing research software or agent behavior, diagnosing failures, deciding whether work needs an isolated Git worktree, reviewing a substantial change, or making a completion claim.
---

# Research Software Quality

Match testing, verification, and isolation to the size and risk of the change. Follow the project's reproducibility mode (`light` by default, `strict` when requested) as defined in [project-conventions](../project-conventions/SKILL.md).

## Route the task

- Code changes, bugs, test failures, or unexpected behavior: read [testing-and-debugging.md](references/testing-and-debugging.md).
- Before any completion claim, or when deciding whether an independent `reviewer` pass adds value: read [verification-and-review.md](references/verification-and-review.md).
- Before editing a repository with concurrent writers, dirty unrelated state, or `strict` isolation: read [worktrees.md](references/worktrees.md).

## Proportional workflow

| Change | Expected process |
| --- | --- |
| Read-only inspection or explanation | Gather direct evidence from files/commands. No worktree. |
| Documentation, comments, formatting, or small isolated edit | Work on a branch in the current checkout; run focused checks. |
| Executable code, tests, dependencies, schemas, skills, or agents | Write or update focused tests where practical; use a worktree when concurrent sessions share the checkout or in `strict` mode. |
| Broad, risky, or publication-facing deliverable | Run full validation, deterministic constraints, and an independent `reviewer` pass when authorized. |

Skills and agent definitions change runtime behavior even though they are Markdown; validate them after edits.

## Scientific validation and persistence

- Compare model and analysis outputs against known baselines, conservation/physical relationships, and domain expectations. Justify modeling choices with literature citations or explicit physical/statistical reasoning.
- Continue autonomously while the objective and next safe step are clear. Investigate command failures as evidence rather than stopping immediately; pause when progress requires user input, compute/remote authority, or a scope change.
- Record durable repository-specific lessons directly in the project's `AGENTS.md` when asked or after resolving a recurring project pitfall.
