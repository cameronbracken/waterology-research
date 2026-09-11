---
name: python-conventions
description: Python style and environment conventions for waterology research code
paths:
  - "**/*.py"
---

# Python conventions

Conventions, not mechanically-checked constraints. Match an existing file's
local style first.

Read the optional local context using this rule name. If the CLI is unavailable,
use the [local resolver](../skills/project-conventions/references/local-preferences.md).

## Interpreter and environments

Run `waterology config context python-conventions` for optional local guidance.
Discover the interpreter and environment from the project configuration.
Use the existing manager (such as Pixi, uv, conda, or venv) and its documented
commands. Do not mix dependency managers or assume personal shell aliases.
For remote systems, inspect their documented module/environment requirements.

## Style

- Format with **ruff** or **black**. Prefer `ruff` for lint + format.
- Type hints at public boundaries; schema-validate external/untrusted input.
- Prefer `pathlib` over string path-joining.

## Reproducibility

- Seed every stochastic path (`np.random.default_rng(<int>)` preferred over the
  legacy global `np.random.seed`); enforced by the `deterministic-seed`
  constraint.
- Project-relative paths only (`no-absolute-paths` constraint).
- Pin the environment for anything that produces a paper result — `pixi.toml` /
  `requirements.txt` / `environment.yml` with version constraints, not bare
  names.

## Model wrappers / scientific stack

- This toolchain wraps Fortran/C hydrology models (SAC-SMA/Snow-17, NWSRFS,
  VIC, `mosartwmpy`) from Python. Keep the wrapper thin; do not silently change
  a model's numerical defaults — a defaults change is an experiment, not a
  refactor, and needs an A/B comparison.
