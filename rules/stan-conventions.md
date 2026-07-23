---
name: stan-conventions
description: >
  Stan / cmdstanr conventions for Bayesian model development: diagnostics in
  order, honest cost measurement, reparameterization levers, and the
  exploration-script pattern.
paths:
  - "**/*.stan"
---

# Stan conventions

For `.stan` files and the R scripts that drive them (cmdstanr). Grown out of
the grid-hydro-data melding work; the warmup lesson alone was worth 48x.

## Fitting protocol

- Derive the seed deterministically per unit (per plant, per site, per
  fixture) so any single fit replays exactly.
- Reuse the pipeline's own functions (`prep_*`, `fit_*`, `summarize_*`) in
  exploration scripts instead of duplicating the calls. Save fits as `rds`.
- cmdstanr/posterior/bayesplot install from their r-universe repositories
  (declared in `rproject.toml`), not from git pins.

## Diagnostics, in order

Run the cheap checks first and stop at the first failure:

1. `fit$diagnostic_summary()`: divergences (investigate any; worry above 1%),
   treedepth saturation, E-BFMI (bad below 0.2).
2. `posterior::summarise_draws()`: `rhat < 1.05` (aim for < 1.01),
   `ess_bulk`/`ess_tail` adequate for the quantiles you report.
3. Visual, for the worst-rhat parameters: `mcmc_trace` + `mcmc_rank_overlay`,
   `mcmc_nuts_energy`, and a pairs plot with divergences highlighted.
4. Model adequacy: posterior predictive against held-out or observed series,
   interval calibration (empirical coverage of the 50%/90% intervals, PIT
   histogram).

## Judge cost only from the full adaptation schedule

Stan's mass-matrix adaptation completes in the terminal windows of warmup. The
adapted tail of a truncated warmup measures a metric-starved sampler, not the
model: the melding model's "16 h/chain, 100% treedepth-saturated" verdict from
truncated probes was really ~20 min/chain under the full 1000+1000 protocol.
So:

- Benchmark with the full protocol (wall clock + ESS/s), never a shortened
  warmup.
- Use truncated probe runs only as pre-adaptation conditioning indicators.

## Reparameterization levers

When a model is slow or saturating, work through these in order; each fixed a
real bottleneck:

1. Center/non-center hierarchical terms (mind the data regime).
2. Marginalize latent states analytically where possible (Kalman for linear
   Gaussian sub-models) instead of sampling them.
3. Anchor weakly identified parameters (a bias term with an informative prior
   beats a free one).
4. Replace a sampled quantity with a deterministic transform when the data
   cannot inform it separately.

## Exploration scripts

One standalone script per question, cell-structured (`# %%`): a settings cell
first (unit id, chains, iterations, output dir; CLI arg with interactive
override), `tar_load()` the pipeline inputs, fit, then the diagnostics above
in order. Write tables and figures to an exploration output area, keep the
fit object in the session for follow-up, and use earth-toned colorblind-safe
palettes (`color_scheme_set`, brewer BrBG family) per the R conventions.
