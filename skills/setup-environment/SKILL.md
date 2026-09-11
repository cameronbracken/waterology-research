---
name: setup-environment
description: >
  Scaffold or repair a project environment for a research project: pixi for
  Python and system tools, rv or renv for R packages, direnv for per-project
  variables. Use when creating a new project, adding an environment to an
  existing one, moving a project between machines, or when an environment
  misbehaves (missing deps, wrong interpreter, broken shebangs).
---

# Environment setup

Run `waterology config context setup-environment` for optional local environment
guidance. Match an existing project's setup before choosing a new one.
Discover installed tools and required target platforms; do not assume a user's
package manager, operating system, interpreter location, or shell aliases.

If the CLI is unavailable, use the shared
[local preferences resolver](../project-conventions/references/local-preferences.md)
with this skill name, including common preferences and matching local guidance.

## Choose the tool

- **pixi** is the default for anything with system or compiled dependencies
  (CmdStan, GDAL, gfortran, quarto, pandoc) and for mixed-language projects.
- **uv** only for pure Python projects with PyPI-only dependencies.
- **R packages**: `rv` (`rproject.toml` + `rv sync`) in newer projects, `renv`
  in older ones. Never mix the two; check `.Rprofile` to see which is active.
- **R installation**: use the project's chosen system or environment-managed R.
  Verify that its Rscript/R executable is available in the execution environment.
- **HPC**: inspect the target system's module and environment requirements.
  Put machine-specific instructions in local guidance, not shared templates.

## Research CLIs the agents expect (global, one-time)

The `researcher`, `reviewer`, and `verifier` agents reach for two tools that
live outside any project environment. Install once per machine, not per project.

- **openalex** — scholarly-metadata CLI (paper/author search, citation graphs,
  DOI/ORCID resolution, OA PDF download). Install globally and verify:

  ```bash
  npm install -g openalex-skill
  openalex --help
  ```

  Keyless for light use; set a mailto or key for higher rate limits with
  `openalex config set mailto you@example.com`.
- **kagi** — an MCP server, configured in Claude Code settings (not on PATH and
  not a project dependency). The agents fall back to `WebSearch`/`WebFetch` when
  it is absent, so this is optional but preferred.

## Scaffold a pixi project

```bash
pixi init
```

Then shape `pixi.toml`:

```toml
[workspace]
channels = ["conda-forge"]
platforms = ["linux-64"]  # example; choose the required target platforms

[dependencies]
python = "3.12.*"
pytest = "*"

[tasks]
test = "pytest tests/"       # one task per verb: test, render, check
```

Housekeeping that goes with it, every time:

```bash
echo '.pixi/' >> .gitignore
echo 'pixi.lock merge=binary linguist-generated=true -diff' >> .gitattributes
pixi install     # solves and writes pixi.lock; commit the lockfile
```

For a Python *package* (not just an environment), keep a `pyproject.toml`
alongside: hatchling build backend, metadata, and `[project.scripts]` entry
points. `pixi.toml` manages the environment; `pyproject.toml` defines the
package. Both belong in the repo. Do not delete `pyproject.toml` on the theory
that it is a uv leftover.

When tools need conflicting dependency versions (e.g. different torch pins),
isolate them in feature environments and keep the default environment minimal:

```toml
[feature.audiosr.dependencies]
torch = "==2.1.1"

[environments]
audiosr = ["audiosr"]
```

Run with `pixi run -e audiosr <task>`.

## R package layer (rv)

- Dependencies live in `rproject.toml`; `rv sync` installs them and writes
  `rv.lock`. `.Rprofile` sources the rv activate scripts.
- Non-CRAN builds (cmdstanr, posterior, bayesplot) come from r-universe
  repositories declared in `rproject.toml`, not from git pins.
- The edit loop is: edit `rproject.toml`, `rv sync`, run the tests.

## Pitfalls (each cost a real debugging session)

- **pixi tasks run under deno_task_shell**, which expands `$var` even inside
  single quotes. R one-liners in `pixi.toml` must avoid `$` entirely: write
  `.Platform[["path.sep"]]`, never `.Platform$path.sep`. The
  `pixi-r-task-dollar` constraint catches this.
- **A copied pixi env is not relocatable.** Console-script shebangs keep the
  old machine's absolute python path, and compiled wheels may link libraries
  that are missing on the new machine. Prefer `pixi install` from the lockfile
  over copying `.pixi/`.
- **`pixi install` does not rebuild path dependencies.** After editing the
  source of a non-editable local package (e.g. a vendored submodule), run
  `pixi reinstall`.
- **Formatters belong in the env.** Add `air` (R) or `ruff` (Python) to pixi
  dependencies so formatting does not depend on global installs. After a bulk
  `air format .`, restore any tool-managed files it touched (rv activate
  scripts).

## Done means

`pixi run <test task>` passes from a clean checkout, the lockfile is
committed, and `python3 ${CLAUDE_PLUGIN_ROOT}/constraints/check-all.py .`
passes.
