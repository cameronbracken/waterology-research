---
name: waterology-simulation-study
description: >
  Design, implement, run, and evaluate a Monte Carlo simulation study using the
  project's language and toolchain. Use for estimator bias, coverage, size,
  power, or finite-sample comparisons.
metadata:
  claude-command:
    name: simulation-study
    argument-hint: <estimators and data-generating process>
---

<!-- Generated from skills/simulation-study/SKILL.md. Do not edit. -->

# Simulation Study

Read [simulation-conventions.md](references/simulation-conventions.md) and the project's language rules before writing code, and use [writing-style](../waterology-writing-style/SKILL.md) for the summary or report. Reuse the project's existing language and environment.

## 1. Design before running

Establish the study design ([Morris, White, and Crowther, 2019](https://doi.org/10.1002/sim.8086)) before launching long compute:

- **Estimands and truth:** Define the exact target parameter or predictive quantity and its analytical or high-precision reference truth. Never substitute an estimator's fitted value for the true target.
- **Scenario grid and replication budget:** Choose sample sizes, regimes, and replication count `N` to achieve target Monte Carlo precision (for example, coverage `MCSE = sqrt(p * (1 - p) / N)`). Confirm compute runtime and HPC allocation before starting large runs.
- **Parallel RNG streams:** Record the RNG algorithm, master seed, and deterministic per-replication stream assignment (`RNGkind("L'Ecuyer-CMRG")` in R, `SeedSequence` in NumPy) so results do not depend on worker count or scheduling order.

## 2. Implementation and failure accounting

- Return raw replication-level records (scenario, replication ID, method, estimate, standard error / interval bounds, convergence status, runtime) to disk (`.parquet`, `.rds`, or `.csv`).
- **Never silently drop failed or non-converged replicates** during aggregation. State exact denominators, failure counts, and handling rules for every method.

## 3. Metrics and reporting

Compute performance measures from saved raw records and always pair headline estimates with **Monte Carlo standard errors (`MCSE`)** (enforced by `constraints/mc-has-mcse.py`):

- Bias: mean of `estimate - truth` (with `MCSE`)
- Empirical SE and model-based SE ratio
- RMSE: `sqrt(mean((estimate - truth)^2))`
- Coverage: fraction of intervals containing truth
- Type I error size or power under the null/alternative DGP

Record the commit, lockfile, seed, and exact run command in `docs/<slug>-simulation.md` (or a [reports](../waterology-reports/SKILL.md) bundle). In `strict` mode, run `constraints/check-all.py --only mc-has-mcse,deterministic-seed` and an independent `reviewer` check.
