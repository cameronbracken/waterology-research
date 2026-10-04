---
name: simulation-study
description: >
  Design, scaffold, run, and review a reproducible Monte Carlo study using the
  project's language and toolchain. Use for estimator bias, coverage, size,
  power, or finite sample comparisons.
metadata:
  claude-command:
    name: simulation-study
    argument-hint: <estimators and data generating process>
---

# Simulation Study

Read [the bundled simulation conventions](references/simulation-conventions.md)
and the project conventions for its actual languages before writing code. Use
an isolated worktree. Reuse the project's toolchain and environment; do not
translate existing code or install another language merely to follow this skill.
Use `writing-style` for the plan and report.

For a complete delegated study, use `simulation-coordinator`. Supply the study
scope, existing protocol and run identities, worktree, allowed files, environment,
compute and storage limits, and delegation authority. The coordinator follows
this skill; it does not delegate the same study to another coordinator. Direct
execution remains valid when delegation adds no value or is unavailable.

## Preflight and durable plan

Write `docs/.plans/<slug>-simulation.md`, or update the assigned existing plan.
Record the question, estimands or targets, truth derivation or reference,
assumptions, regimes, DGP parameters, methods, scenario grid, replication budget,
randomization design, output schema, metrics, precision requirements, failure
policy, and acceptance criteria. Identify which checks and outputs apply to the
study. If a target or consequential criterion is ambiguous, resolve it before
execution. Do not change a frozen protocol to make a result pass.

Record the chosen language and toolchain, environment, compute profile, allowed
checks, runtime and storage budgets, and authority already granted. Continue
within existing authorization without requesting it again. Missing authorization
for execution permits planning and inspection, not a compute launch. Do not
start a long run until its compute and storage cost are authorized.

Choose replication counts to meet the precision needed for the intended claims.
For independent Bernoulli coverage indicators, the planning approximation is
`MCSE = sqrt(p * (1 - p) / N)`, where `N` uses the declared analysis denominator.
Record how failures affect that denominator; do not silently count only successful
fits. Report Monte Carlo uncertainty with estimated performance measures and
method comparisons. See [Morris, White, and Crowther (2019)](https://doi.org/10.1002/sim.8086)
for simulation design and performance-measure uncertainty.

## Implementation contract

- Keep settings, inputs, output paths, and the canonical entry point explicit.
- Use a parameterized data-generation interface returning data and the target
  truth or a reference to its derivation. `generate_data(params)` is pseudocode,
  not a required function name or language-specific return type. Never substitute
  an estimator's fitted value for its target truth.
- Define a common method-result schema with status and quantities needed by the
  chosen metrics. Standard errors and interval bounds apply to methods that
  produce them; do not invent placeholders that appear to be observed results.
- Record the RNG algorithm, master seed or state, and deterministic stream
  assignment to scenario and replication identities. Use the language's supported
  stream mechanism. Qualify restart and worker-count behavior under a declared
  comparison rule using authorized small checks. Identical seeds alone do not
  establish identical sequences across different languages or RNG libraries.
- For R implementations, `RNGkind("L'Ecuyer-CMRG")` is one stream option; its use
  requires a replication-to-stream mapping, not repeated reseeding of workers.
  Other languages use their own documented mechanisms under the same contract.
- Retain raw records for every attempted replication, method, and scenario,
  including randomization provenance and failed or non-converged status.
- Handle missing and nonfinite values explicitly. Never hide failures by dropping
  them during aggregation. Save partial outputs and useful progress milestones.
- Store raw data and summaries in documented formats appropriate to the project,
  with a schema and reader. Provide interoperable tables when needed for handoff;
  native serialization such as RDS is optional, not a universal requirement.

## Execute and preserve the study

Initialize project records with `waterology init` when needed, inspect native
tasks with `waterology config refresh --check`, and register the simulation with
`waterology workflow register simulate --task TASK` or
`waterology workflow register simulate --definition workflow.yaml`. Declare raw
outputs, metric extractors, environment files, and input identities. Keep DGP
settings in the study's existing configuration.

Once code and execution configuration are committed and compute is authorized,
run `waterology workflow run simulate --profile PROFILE`. TORC manages jobs and
dependencies; Waterology collects outputs, metrics, and failed attempts. Record
the actual run identity in the plan. After interruption, inspect that run and
resume collection with `waterology workflow watch RUN_ID`. Unknown status is a
reconciliation task, not permission to submit a replacement run.

Use a managed study through `autoresearch` only when candidate iteration under
a saved objective and budget is authorized. The existing controller owns its
execution, retries, budgets, and records. Do not introduce a coordinator-owned
execution loop or alternate launcher. A failed check permits investigation,
not an unbudgeted retry or a changed acceptance rule.

## Metrics

Compute applicable metrics against the declared truth using the saved raw records:

- bias: mean of `estimate - truth`, with MCSE from replication-level deviations;
- empirical standard error: standard deviation of the estimates;
- RMSE: square root of the mean squared `estimate - truth`;
- coverage: proportion of intervals containing truth;
- size or power: rejection rate under the matching null or alternative DGP.

State denominators, exclusions, and failure counts. Use a Monte Carlo uncertainty
calculation appropriate to the replication and comparison design, including any
pairing. Apply the declared precision and comparison criteria, and report unmet
criteria rather than inventing an after-the-fact threshold. Build figures and
summaries from saved values. A successful process exit is not statistical acceptance.

## Review, corrections, and handoff

Use `simulation-code-reviewer` for implementation quality and
`simulation-reviewer` for statistical design and evidence. Supply immutable
input snapshots or content fingerprints, source revision, run identities,
protocol, saved outputs, and separate report paths. Require each reviewer to
identify the input versions inspected. Their reviews may run independently
against the same stable inputs; compare returned versions before accepting them.
If independent review is unavailable, perform the checks directly and state that
limitation. Do not claim independent review occurred.

Resolve critical and high findings within the authorized scope. If source,
inputs, or protocol change, preserve earlier evidence and determine which runs,
metrics, and reviews are invalidated. New required runs use the existing workflow
and remaining authority. Re-review affected findings against the corrected
artifacts. Keep unresolved limitations visible in the final report.

Write `docs/<slug>-simulation.md`, or the assigned report, with the protocol,
source and run identities, outputs, metrics and MCSEs, failures, review evidence,
acceptance status, and outstanding checks. When required statistical acceptance
and review conditions are met, register the selected run with
`waterology deliverable register final definition.yaml`. Use
`waterology reproduce final NEW_DIRECTORY --profile PROFILE` only within the
reproduction authority and environment already chosen. An unperformed required
reproduction remains unverified. These CLI services remain the source of run
and deliverable state, independent of the coordination ledger.

Return the plan, report, raw output and review paths, run identities, and actual
check results. A blocked or exhausted study still gets a report with partial
results and remaining requirements. Never present partial execution or unresolved
acceptance as a completed study.
