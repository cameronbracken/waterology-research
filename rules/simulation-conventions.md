---
name: simulation-conventions
description: Reproducibility and evidence conventions for Monte Carlo studies
paths:
  - "**/*simulation*.R"
  - "**/*_sim.R"
  - "**/*_mc.R"
  - "scripts/**/simulations/**"
---

# Monte Carlo simulation conventions

A simulation is an experiment. State its DGP, truth, estimand, assumptions,
regime, replication budget, and outputs before interpreting a result.

## Required structure

- Use one parameterized `generate_data()` function that returns data and truth.
- Derive truth from DGP parameters, never from a fitted estimate.
- Match each estimator to the truth for its stated estimand.
- For an assumption violation, change one assumption over a severity grid and include the zero dose as a control.
- Do not use an out of assumption run to support nominal coverage, valid standard errors, consistency, or a default method.

## Randomness

Set `RNGkind("L'Ecuyer-CMRG")` and one master seed. Assign a reproducible stream
to each replication, not each worker. Qualify a parallel harness by running a
small fixed set at two worker counts and requiring identical results.

## Metrics and uncertainty

Coverage is `mean(lower <= truth & truth <= upper)`. Bias and RMSE also use
truth. Every reported bias, coverage, size, power, or method comparison needs
an MCSE. If a difference is smaller than about twice its MCSE, describe it as
unresolved at the current replication budget.

## Failures and storage

Record failed and non-converged replications and state the rule used for them.
Save raw rows before summaries. Each raw row carries replication, scenario,
estimator, truth, estimate, standard error, interval bounds, and status. Save
the summary in both a machine readable and human readable form.
