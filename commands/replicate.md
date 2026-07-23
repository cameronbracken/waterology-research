---
description: Plan a replication workflow for a paper, claim, or benchmark; execute only after an explicit environment choice.
argument-hint: <paper>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT); claim ledger and assessment language from openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See ATTRIBUTION.md. -->

Design a replication plan for: $ARGUMENTS

Tools: `WebSearch`/`WebFetch` and paper search for the target; `gh`, `Bash`, `Read` to inspect code; the `Task` tool to launch the `researcher` agent for extraction.

## Workflow

1. **Extract** — Use the `researcher` subagent to pull implementation details from the target paper and any linked code. If `CHANGELOG.md` exists, read the most recent relevant entries before planning or resuming.
2. **Claims** — Enumerate the paper's main empirical claims, headline table or figure results first. Unless the user asks for broader coverage, focus on the main illustrative claim. Each claim becomes a row in a ledger carrying: the paper's reported result, the observed result, an assessment, any downscaling or substitutions, and the compute cost.
3. **Recipe pass** — For training, fine-tuning, benchmark, or dataset-heavy targets, do a recipe extraction before execution planning. Link each claimed result to the exact dataset, method, hyperparameters, compute assumptions, metric, and code path that produced it. Validate dataset availability and schema when possible; mark unchecked details `unverified` rather than assuming they are usable.
4. **Plan** — Determine the code, datasets, metrics, and environment needed. Be explicit about what is verified, inferred, and still missing, and which checks or oracles decide whether the replication succeeded.
5. **Environment** — Before running anything, ask the user where to execute:
   - **Local** — run in the current working directory.
   - **New git branch** — branch first so the working tree stays clean.
   - **Pixi environment** — create or use a `pixi.toml` environment for reproducible Python and system tools (`pixi run ...`); use `rv`/`renv` for R packages. Match an existing project's setup before imposing one.
   - **Remote (SSH / Slurm)** — for GPU or long jobs, run on a lab or HPC host over SSH, submitting through Slurm where available. Sync inputs and harvest logs and artifacts back.
   - **Plan only** — produce the replication plan without executing.
6. **Execute** — If an execution environment was chosen, work claim by claim, filling the ledger as each result lands. Simplified setups and toy-scale runs are fine when full scale is out of budget; state the downscaling explicitly in the ledger. Save notes, scripts, raw outputs, and results to disk in a reproducible layout, with a seed and RNG kind recorded. Do not call the outcome replicated unless the planned checks actually passed.
7. **Assess** — Rate each claim from a fixed vocabulary: `aligned`, `partially aligned`, `inconclusive under this setup`, or `not attempted`. When results diverge, say this run did not show the reported effect, quantify the difference, and explain relevant uncertainty or substitutions. Do not characterize the claim as wrong, failed, or "not replicated", and do not infer beyond the tested setup.
8. **Log** — For multi-step or resumable work, append concise entries to `CHANGELOG.md` after meaningful progress, failed attempts, major verification outcomes, and before stopping: the active objective, what changed, what was checked, and the next step.
9. **Report** — Lead with the strongest result figure, then the claim ledger, then what a full-scale replication would still need. Keep the write-up implementation-led rather than a run log: the consequential code paths, design choices, and the smallest changes used to test them. Every figure and number carries provenance (script, seed, exact command, copied verbatim). End with a `Sources` section of paper, dataset, documentation, and repository URLs.

Do not install packages, run training, or execute experiments without confirming the execution environment first.
