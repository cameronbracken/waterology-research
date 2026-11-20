---
name: python-conventions
description: Python style and environment conventions for waterology research code
paths:
  - "**/*.py"
---

# Python conventions

Conventions, not mechanically-checked constraints. Match an existing file's local style first.

## Interpreter and environments

Discover the interpreter and environment from the project configuration. Use the existing manager (Pixi, uv, conda, or venv) and its documented commands. Do not mix dependency managers or assume personal shell aliases.

For new work, use Pixi for mixed-language or system dependencies and uv for pure Python. In a Pixi project, run through `pixi run` and declare dependencies with `pixi add`; do not mutate the environment with ad hoc `pip install` calls.

## Style

- Format and lint with **ruff**.
- Add type hints at public boundaries and schema-validate external or untrusted input.
- Prefer `pathlib` over string path joining.

## Reproducibility

- Seed every stochastic path (`np.random.default_rng(<int>)` preferred over legacy global `np.random.seed`), enforced by the `deterministic-seed` constraint.
- Use project-relative paths only (`no-absolute-paths` constraint).
- Pin dependencies in a committed lockfile (`pixi.lock` or `uv.lock`) for any analysis result.

## Model wrappers and scientific stack

- When wrapping Fortran or C hydrology models (SAC-SMA/Snow-17, NWSRFS, VIC, `mosartwmpy`) from Python, keep the wrapper thin. Never silently change a model's numerical defaults; changing defaults is an experiment that requires an explicit comparison.
