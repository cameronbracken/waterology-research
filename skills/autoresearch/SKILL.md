---
name: autoresearch
description: >
  Run a bounded autonomous research, calibration, or software engineering/optimization
  loop over Git commits and a protected evaluation benchmark. Use when asked to
  iteratively improve a metric, tune a model, optimize runtime under correctness
  constraints, or build to an acceptance test suite.
metadata:
  claude-command:
    name: autoresearch
    argument-hint: <objective and target metric>
---

# Autoresearch and Bounded Engineering Loops

Use [research-software-quality](../research-software-quality/SKILL.md) for testing and verification and [writing-style](../writing-style/SKILL.md) for summaries. For long campaigns, read [token-discipline.md](references/token-discipline.md); for multi-decision branching studies, read [experiment-tree.md](references/experiment-tree.md).

## Core design (zero database ceremony)

Run iterative experiments directly over **Git + a pinned evaluation command + an append-only ledger** (`results.yaml` or `experiments.tsv`):

1. **Choose the mode and freeze the evaluator:**
   - _Engineering / optimization:_ Define hard correctness and regression checks plus the target metric (such as runtime, memory, or failed-test count). Every correctness check must pass before any speed win counts.
   - _Research / calibration:_ Define the estimand or skill metric (`KGE`, `CRPS`, `RMSE`, log-score), evaluation split, and uncertainty/noise margin. Negative or inconclusive findings are valid outcomes.
   - Keep the evaluation script, test suite, benchmark inputs, and lockfiles **outside** the files candidates edit.
2. **Establish the baseline:** On a clean feature/experiment branch (for example `exp/<slug>`), run the evaluation command once (`pixi run`, `uv run`, or native `torc` when distributed/Slurm execution is needed and HPC allocation is confirmed) and record the baseline commit and metrics in `results.yaml` (ignored or tracked per project preference).
3. **Iterate within explicit bounds:** Set a clear iteration cap or wall-clock limit up front. In each iteration:
   - Make one focused, hypothesis-driven or bottleneck-driven edit inside allowed source paths and commit it (`git commit`).
   - Run lightweight syntax/unit preflight first, then run the frozen evaluator.
   - Append `{iteration, commit, description, metrics, status}` (`keep`, `discard`, or `crash`) to `results.yaml`.
   - If a candidate improves beyond noise while passing all constraints, advance from that commit (`keep`). Otherwise record the failure/regression in `results.yaml` and reset source to the current best commit (`git checkout` / `git reset --hard <best-commit>`) before the next attempt.

## Autonomous continuation and stopping

Start immediately when given a concrete objective and evaluation command. Continue across iterations until hitting the target, exhausting the iteration/time budget, or encountering a blocker that requires user input or new compute authority. Summarize the baseline, best commit, full tried-candidate table (including discarded ideas), and remaining trade-offs.
