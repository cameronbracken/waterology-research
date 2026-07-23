---
description: Plan a replication workflow for a paper, claim, or benchmark; execute only after an explicit environment choice.
argument-hint: <paper>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Design a replication plan for: $ARGUMENTS

Tools: `WebSearch`/`WebFetch` and paper search for the target; `gh`, `Bash`, `Read` to inspect code; the `Task` tool to launch the `researcher` agent for extraction.

## Workflow

1. **Extract** — Use the `researcher` subagent to pull implementation details from the target paper and any linked code. If `CHANGELOG.md` exists, read the most recent relevant entries before planning or resuming.
2. **Recipe pass** — For training, fine-tuning, benchmark, or dataset-heavy targets, do a recipe extraction before execution planning. Link each claimed result to the exact dataset, method, hyperparameters, compute assumptions, metric, and code path that produced it. Validate dataset availability and schema when possible; mark unchecked details `unverified` rather than assuming they are usable.
3. **Plan** — Determine the code, datasets, metrics, and environment needed. Be explicit about what is verified, inferred, and still missing, and which checks or oracles decide whether the replication succeeded.
4. **Environment** — Before running anything, ask the user where to execute:
   - **Local** — run in the current working directory.
   - **New git branch** — branch first so the working tree stays clean.
   - **Pixi environment** — create or use a `pixi.toml` environment for reproducible Python and system tools (`pixi run ...`); use `rv`/`renv` for R packages. Match an existing project's setup before imposing one.
   - **Remote (SSH / Slurm)** — for GPU or long jobs, run on a lab or HPC host over SSH, submitting through Slurm where available. Sync inputs and harvest logs and artifacts back.
   - **Plan only** — produce the replication plan without executing.
5. **Execute** — If an execution environment was chosen, implement and run the steps there. Save notes, scripts, raw outputs, and results to disk in a reproducible layout, with a seed and RNG kind recorded. Do not call the outcome replicated unless the planned checks actually passed.
6. **Log** — For multi-step or resumable work, append concise entries to `CHANGELOG.md` after meaningful progress, failed attempts, major verification outcomes, and before stopping: the active objective, what changed, what was checked, and the next step.
7. **Report** — End with a `Sources` section of paper, dataset, documentation, and repository URLs.

Do not install packages, run training, or execute experiments without confirming the execution environment first.
