# Constraint: stochastic code sets a seed

**Type:** constraint (deterministic, scriptable pass/fail)
**Check:** `deterministic-seed.py`
**Applies to:** `.R .r .py` analysis/simulation scripts

## Rule

Any script that draws random numbers must set a seed, so a result is
reproducible run-to-run. A figure, table, or simulation summary that silently
changes every time it runs cannot be defended in a paper or a review.

The check flags a file that **uses** randomness but **never** sets a seed:

- **R** — uses `rnorm` / `runif` / `sample` / `rbinom` / `rpois` / `rgamma` /
  `rbeta` / `rexp` / `mvrnorm` / `simulate` / a `boot()` call, but contains no
  `set.seed(`.
- **Python** — uses `np.random` / `random.` / `default_rng` / `torch.rand` /
  `sample(` but sets no seed (`np.random.seed`, `seed(`, `default_rng(<int>)`,
  `manual_seed`).

For parallel Monte Carlo work, a single `set.seed()` is not enough — use a
parallel-safe RNG (`RNGkind("L'Ecuyer-CMRG")` in R, an explicit
`SeedSequence`/per-worker stream in Python). That nuance is a *convention*
(see the simulation rules) rather than something this check enforces.

## Why this is a constraint, not a convention

Presence of an RNG call and absence of a seed call are both mechanically
detectable — a script returns pass/fail.

## Escape hatch

Add `# waterology: allow-unseeded` to the file (anywhere) when randomness is
intentionally non-reproducible — for example a one-off interactive draw.

---
*Numerical-discipline checks adapted from the `r-reviewer` / simulation
tooling in pedrohcgs/claude-code-my-workflow (MIT, © 2026 Pedro H. C. Sant'Anna).*
