---
name: replication
description: >
  Plan a replication of a paper, claim, or benchmark, and execute only after an
  explicit environment choice. Use when the user asks to replicate results,
  reproduce an experiment, verify a claim empirically, or build a replication
  package.
metadata:
  claude-command:
    name: replicate
    argument-hint: <paper>
---

# Replication

Use `writing-style` for the plan, evidence ledger, and report.

For an existing Waterology deliverable, use the CLI reproduction workflow after
resolving the already-authorized environment and compute profile:

```console
waterology reproduce final NEW_DIRECTORY --profile PROFILE
waterology reproduce final NEW_DIRECTORY --path EXPORTED_BUNDLE --bundle --profile PROFILE
```

The service restores the selected source, restores its environment through the
project manager, verifies supplied input identities, executes through TORC and
checks fresh outputs. Use `--resume` with the same directory after an interrupted
or blocked attempt. Inspect the saved reason before changing anything. Never
replace the selected source, reference output or tolerance to obtain a pass.

For a new replication, initialize records with `waterology init`, inspect native tasks with
`waterology config refresh --check`, and register the selected task or evaluation definition with
`waterology workflow register replicate --task TASK` or
`waterology workflow register replicate --definition workflow.nt`. Commit the
execution configuration and source before `waterology workflow run replicate`.
TORC owns compute and dependencies; Waterology automatically collects run evidence.
Select the resulting deliverable explicitly with `waterology deliverable register`
and export it with `waterology deliverable export`. These services are usable
without this skill. Output agreement and support for the paper's claims remain
separate assessments.

Read the target paper, linked code, and recent relevant `CHANGELOG.md` entries.
Delegate broad implementation extraction to the `researcher` through the
runtime's available agent mechanism.

Create a claim ledger, starting with the headline table or figure result. Unless
the user requests broader coverage, focus on the main illustrative claim. Each
row carries the paper result, observed result, assessment, downscaling or
substitutions, and compute cost.

For training or dataset heavy targets, extract a recipe before execution. Link
each claimed result to its dataset, method, hyperparameters, compute, metric,
and implementation path. Check dataset availability and schema where possible.
Mark unchecked details `unverified`.

Plan the code, data, metrics, environment, and checks that decide whether the
replication is aligned with the reported result. Separate verified facts,
inferences, and missing information.

Require an explicit environment choice before execution:

- Local work in the current directory.
- A new Git branch.
- A Pixi environment, with `rv` or `renv` for R packages when appropriate.
- Remote SSH or Slurm for GPU or long runs.
- Plan only, with no execution.

Match the existing project setup before creating an environment. Do not install
packages, run training, or execute experiments until the user confirms the
environment. Use `setup-environment` only after that choice when scaffolding is
needed.

When authorized, work claim by claim and fill the ledger as results arrive.
Record seeds, RNG kind, commands, scripts, raw outputs, and results in a
reproducible layout. State every downscaling or substitution. Do not call the
outcome replicated unless the planned checks pass.

Assess each claim with exactly one of `aligned`, `partially aligned`,
`inconclusive under this setup`, or `not attempted`. For divergence, quantify
what this run observed and its uncertainty. Do not characterize the paper's
claim as wrong or infer beyond the tested setup.

For resumable work, append concise `CHANGELOG.md` entries after meaningful
progress, failed attempts, major checks, and before stopping. Record the active
objective, changes, evidence, and next step.

Lead the report with the strongest result figure, followed by the claim ledger
and what a full scale replication still needs. Every figure and number carries
its script, seed, and exact command. End with direct paper, dataset,
documentation, and repository URLs.

Agents used: `researcher`.
Output: replication plan, scripts, raw outputs, and a `CHANGELOG.md` trail.
