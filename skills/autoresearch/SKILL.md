---
name: autoresearch
description: >
  Bounded research experiment loop that tries hypotheses, measures benchmark
  evidence, keeps what works, and records what fails. Use when the user asks to
  optimize a research metric, run an experiment loop, or iteratively improve
  model, retrieval, or forecast performance.
---

# Autoresearch

Run the `/autoresearch` workflow. It collects the optimization target, benchmark
command, metric, files in scope, and iteration cap; confirms the plan and the
execution environment; then loops edit -> run benchmark -> log result and
decision -> keep, revert, or record the failed hypothesis. A seed is set so runs
are reproducible, and progress is logged to `autoresearch.jsonl` and `CHANGELOG.md`.

Two loop shapes: **linear** (default, one working branch, keep or revert each
edit) and **tree** (for studies spanning several design decisions: a frozen
baseline, one git branch for each hypothesis, fan the options of one decision,
descend onto the winner). Tree mode follows
`${CLAUDE_PLUGIN_ROOT}/rules/experiment-tree.md`.

Environments: Local, a new git branch, a Pixi environment, or remote SSH/Slurm.

Output: `autoresearch.md`, `autoresearch.jsonl`, `autoresearch.sh`.

---
*Adapted from Feynman (companion-inc/feynman, MIT); tree mode from
openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See
`${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
