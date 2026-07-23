---
description: Bounded research experiment loop — try hypotheses, measure benchmark evidence, keep what works, discard what doesn't, repeat.
argument-hint: <idea>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT); tree mode from openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See ATTRIBUTION.md. -->

Start an autoresearch optimization loop for: $ARGUMENTS

This runs a bounded foreground experiment loop using `Bash` to run the benchmark and `Read`/`Edit` to change the code in scope.

## Step 1: Gather

If `autoresearch.md` and `autoresearch.jsonl` already exist, ask whether to resume or start fresh. If `CHANGELOG.md` exists, read the most recent relevant entries before resuming.

Otherwise collect from the user before doing anything else:
- What to optimize (model skill, forecast error, retrieval quality, training loss, runtime, etc.)
- The benchmark command to run
- The metric name, unit, and direction (lower or higher is better)
- Files in scope for changes
- Maximum number of iterations (default: 20)
- Loop shape: **linear** (default) or **tree**. Linear works one branch,
  keeping or reverting each edit. Tree is for studies spanning several design
  decisions: a frozen baseline, one branch for each hypothesis, fan the
  options of one decision, then descend onto the winner. Suggest tree mode
  when the idea names more than one decision to resolve; on tree mode, read
  `${CLAUDE_PLUGIN_ROOT}/rules/experiment-tree.md` and follow its cardinal
  rules for the whole run.

## Step 2: Environment

Ask where to run:
- **Local** — run in the current working directory.
- **New git branch** — branch so main stays clean.
- **Pixi environment** — an isolated `pixi.toml` environment (`pixi run ...`); `rv`/`renv` for R.
- **Remote (SSH / Slurm)** — a lab or HPC host for GPU-heavy or long benchmarks, submitting through Slurm where available.

Do not proceed without a clear answer.

## Step 3: Confirm

Present the full plan before starting:

```
Optimization target: [metric] ([direction])
Benchmark command:   [command]
Files in scope:      [files]
Environment:         [chosen environment]
Max iterations:      [N]
```

Ask the user to confirm. Do not start the loop without explicit approval.

## Step 4: Run

Initialize the session: create `autoresearch.md`, `autoresearch.jsonl`, and `autoresearch.sh`; run the baseline; start looping.

Each iteration: edit -> run the benchmark -> log the result, evidence, and decision to `autoresearch.jsonl` -> compare against the baseline -> keep the change, revert it, or record the failed hypothesis -> repeat. Set and record a seed so each run is reproducible. Do not stop unless interrupted or the iteration cap is reached. After the baseline and after meaningful milestones, append a concise `CHANGELOG.md` entry: what changed, the metric observed, what failed, the next step.

In tree mode the iteration unit is a round, not an edit: branch one child for each option of the current decision, run the fixed benchmark command on each, log every node to `autoresearch.jsonl` with its branch and parent, then refill, promote, or stop as the rule file describes. The baseline stays frozen and the run command never changes; only committed code varies between branches. The iteration cap counts benchmark runs, not rounds.

## Subcommands

- `/autoresearch <text>` — start or resume the loop
- `/autoresearch off` — stop the loop, keep data
- `/autoresearch clear` — delete all state and start fresh
