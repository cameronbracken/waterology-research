---
name: simulation-study
description: >
  Design, scaffold, run, and review a reproducible Monte Carlo study in R.
  Use for estimator bias, coverage, size, power, or finite sample comparisons.
metadata:
  claude-command:
    name: simulation-study
    argument-hint: <estimators and data generating process>
---

# Simulation Study

<!-- Adapted from pedrohcgs/claude-code-my-workflow,
.claude/skills/simulation-study/SKILL.md at commit
9d371f0bf8a8bc99569feca3210ef5133af28d33 (MIT, Copyright 2026 Pedro H. C.
Sant'Anna). DiD examples and Claude specific control flow were removed. See
ATTRIBUTION.md. -->

Read [the bundled simulation conventions](references/simulation-conventions.md)
and the project R conventions before writing code. Use an isolated worktree for
the study. Do not start a long run until the user authorizes its compute and
storage cost.

## Execute and preserve the study

Initialize project records with `waterology init`, inspect native task discovery
with `waterology workflow list`, and refresh with `waterology config refresh`.
Register the simulation command or TORC YAML with
`waterology workflow register simulate --definition workflow.nt`. Declare raw
replication outputs, metric extractors, environment files and input identities.
Keep the DGP settings in the simulation's existing configuration.

Once code and execution configuration are committed and compute is authorized,
run `waterology workflow run simulate --profile PROFILE`. TORC manages jobs and
dependencies; Waterology collects outputs, metrics and failed attempts. Resume
collection with `waterology workflow watch RUN_ID` after interruption. Use a
managed study through `autoresearch` only when iterating candidate changes under
a saved objective and budget.

Select the final run with `waterology deliverable register final definition.nt`.
Use `waterology reproduce final NEW_DIRECTORY --profile PROFILE` to restore and
validate that deliverable. Statistical acceptance must use a declared validator
workflow and retain its evidence. A process exit alone does not establish Monte
Carlo precision or scientific support. These CLI services work without skills.

## Preflight

Record the research question, target estimand, truth formula, maintained
assumptions, regime, DGP parameters, estimator grid, design grid, replication
count, random seed, outputs, and planned metrics. If truth or estimand is
ambiguous, stop for clarification.

Choose the replication count from the precision needed for the claims. Near
95% coverage, `MCSE = sqrt(0.95 * 0.05 / R)`, so about 1,900 successful
replications give an MCSE near 0.005.

## Implementation contract

- Put settings and relative paths at the top of the script.
- Call `RNGkind("L'Ecuyer-CMRG")` and `set.seed()` once. Use one stream for each replication so results do not depend on worker count.
- Implement one parameterized `generate_data(params)` function returning `list(data, truth)`. Compute truth from the DGP parameters.
- Give each estimator a common return contract: estimate, standard error, lower interval, upper interval, and convergence status.
- Store one raw row for each replication, estimator, and scenario. Include truth, seed or stream identifier, and failure status.
- Count failed replications and non-convergence. Never hide them with `na.rm = TRUE`.
- Use a progress bar or occasional milestone for a long run.

## Metrics

Compute metrics against truth:

- bias: `mean(estimate - truth)`; MCSE from the replication level deviations;
- empirical standard error: `sd(estimate)`;
- RMSE: `sqrt(mean((estimate - truth)^2))`;
- coverage: `mean(lower <= truth & truth <= upper)`;
- size or power: rejection rate under the matching null or alternative DGP.

Report MCSE beside bias, coverage, and rejection rates. Do not call one method
better when the difference is within about two MCSEs.

## Outputs and review

Save the raw result table and summary as RDS. Also save the summary in a human
readable format such as CSV. Build figures from those saved values. Ask the
`sim-reviewer` to review the script and saved output, then address critical and
high findings before presenting results. Use `r-reviewer` for the separate R
quality pass.
