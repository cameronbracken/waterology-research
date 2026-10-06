---
name: simulation-conventions
description: Reproducibility and evidence conventions for Monte Carlo studies
paths:
  - "**/*simulation*.*"
  - "**/*_sim.*"
  - "**/*_mc.*"
  - "scripts/**/simulations/**"
---

# Monte Carlo simulation conventions

A simulation is an experiment. State its DGP, target truth, estimand, assumptions,
regime, replication budget, metrics, failure policy, and outputs before
interpreting results. Follow project conventions for the actual languages used.

## Structure and targets

- Use a parameterized data-generation interface returning data and truth or a
  traceable reference. Function names and return types follow the language.
- Derive truth from the DGP or an established reference, not the fitted estimate
  being evaluated. Record uncertainty in numerical reference calculations.
- Match each method and metric to its declared target and regime. An assumption
  violation study needs a justified scenario design and appropriate controls.
- Do not use a violation scenario to establish validity under other assumptions.
- Preserve frozen protocols, input identities, and acceptance criteria.

## Randomness and execution

Record the RNG algorithm and master state or seed. Assign reproducible streams
to replication and scenario identities rather than worker identities. Qualify
restart and worker-count behavior with small authorized checks and a declared
comparison rule. Document any platform or library limitations. An R implementation
may use L'Ecuyer-CMRG; other languages use documented mechanisms appropriate to
their runtime. Matching seed integers across languages is not a portability test.

Use the registered workflow or managed-study controller for execution. Preserve
run identities and reconcile them before resuming. Keep coordination notes
separate from the authoritative execution records.

## Metrics and uncertainty

Use target truth for bias, RMSE, and interval coverage where those metrics apply.
Report MCSE for estimated simulation performance and comparisons under the
actual replication design. State denominators and how failures affect them.
Assess comparisons against the declared precision and decision criteria; a
computed difference without uncertainty is not sufficient evidence of superiority.
Fixed inputs and deterministic reference values do not require an MCSE.

## Failures and storage

Retain failed and non-converged attempts and the declared rule used for them.
Save raw results before summaries. Retain scenario, replication, method, status,
and randomization provenance plus the quantities needed by the chosen metrics.
Truth may live in scenario metadata if the mapping is explicit. Require standard
errors or intervals only for methods and metrics that use them.

Use documented formats with schemas and readers appropriate to the project's
languages. Provide interoperable tables when needed for handoff. Native object
formats are optional. Bind code and statistical reviews to the exact source and
output versions, and invalidate checks when those inputs change.
