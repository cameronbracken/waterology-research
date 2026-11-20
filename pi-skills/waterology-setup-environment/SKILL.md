---
name: waterology-setup-environment
description: >
  Scaffold, repair, or capture a research project environment: pixi for Python,
  compiled, and mixed-language tools, uv for pure Python, rv for R, system R on
  macOS, and direnv for project variables.
---

<!-- Generated from skills/setup-environment/SKILL.md. Do not edit. -->

# Environment Setup

Match an existing project's environment manager before introducing a new one. Discover installed tools and target platforms rather than assuming shell aliases or interpreter paths.

For pre-submission or archival environment snapshots, read [capture-environment.md](references/capture-environment.md).

## Choose the manager

- **pixi** is the default for anything with system or compiled dependencies (CmdStan, GDAL, gfortran, Quarto, pandoc) and mixed-language projects.
- **uv** for pure Python projects with PyPI-only dependencies.
- **R packages:** prefer `rv` (`rproject.toml` + `rv sync` -> `rv.lock`) for new work. Maintain an existing `renv` project without mixing managers; check `.Rprofile` first.
- **R on macOS:** prefer system R (Homebrew) and keep R itself out of Pixi. Pixi supplies tools R calls (`pandoc`, `quarto`, `air`, `cmdstan`). Verify `R` and `Rscript` resolve on `PATH`.
- **direnv:** use `.envrc` for project activation and non-secret variables; keep credentials and machine paths outside committed files. Use `bash` for portable noninteractive scripts.

## Global research CLIs (one-time per machine)

- **openalex** CLI (`npm install -g openalex-skill`) for citation graphs (`cited-by`, `references`, `related`) and OA PDF downloads.
- **waterology-mcp** (`wgy research-access`) for bounded scholarly search, Zotero sync, and Hugging Face Hub inspection.

## Scaffold a Pixi project

```bash
pixi init
echo '.pixi/' >> .gitignore
echo 'pixi.lock merge=binary linguist-generated=true -diff' >> .gitattributes
pixi install
```

Keep `[tasks]` concise (`test`, `lint`, `render`, `check`). For an installable Python package, keep `pyproject.toml` (hatchling metadata and `[project.scripts]`) alongside `pixi.toml`. Isolate conflicting heavy dependencies (such as alternate PyTorch builds) into `[feature.<name>]` environments (`pixi run -e <name> <task>`).

## Pitfalls

- **`pixi.toml` tasks use `deno_task_shell`**, which expands `$var` even inside single quotes. Avoid `$` in R task one-liners (`.Platform[["path.sep"]]`, enforced by `pixi-r-task-dollar`).
- **Never copy `.pixi/` across machines**; restore from `pixi.lock` with `pixi install`.
- **Formatters belong in the environment** (`ruff` for Python, `air` for R). After bulk `air format .`, restore any tool-managed files (`rv` activate scripts).
