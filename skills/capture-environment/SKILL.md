---
name: capture-environment
description: >
  Capture software, packages, compilers, flags, seeds, and platform details for
  an R, Python, Fortran, or mixed research workflow. Use before archival,
  handoff, replication, or a reproducibility audit.
metadata:
  claude-command:
    name: capture-environment
    argument-hint: <project directory> [--verify]
---

# Capture Environment

Record the environment that produced a result without changing dependencies.
For Waterology runs, the sealed archive stores `environment.json` and the derived
RO-Crate links that file to the run action; keep both consistent. Use
`project-conventions` to select the existing package manager. Never replace
Pixi with pip, add renv to a project that uses another declared R workflow, or
upgrade packages while capturing them.

## Detect the stack

Inspect project guidance and files, then run every applicable path:

- R: `.R`, `.Rmd`, `DESCRIPTION`, `renv.lock`, or `rv.lock`;
- Python: `.py`, notebooks, `pyproject.toml`, `pixi.toml`, `uv.lock`, or requirements files;
- Fortran: `.f90`, `.F90`, `.f95`, `.f`, `Makefile`, `meson.build`, or compiler tasks.

If no stack is found, report the inspected paths and stop. A mixed project gets
one capture for each language plus a combined requirements report.

## Capture

### R

- Preserve the declared lock approach. For renv, inspect `renv::status()` and record the existing lock hash by default. Run `renv::snapshot()` only with explicit authorization because it mutates `renv.lock`; review its diff before accepting it. Record `rv.lock` when rv is declared.
- Write `sessionInfo.txt` from `sessionInfo()` to the project's evidence or output directory.
- Record R version, package sources, locale, `RNGkind()`, and every `set.seed()` used by canonical scripts.

### Python

- Preserve `pixi.lock`, `uv.lock`, or a pinned requirements file according to the current project.
- Record the Python implementation and version plus the selected environment command.
- Record `default_rng`, `SeedSequence`, library seeds, and relevant deterministic settings.

### Fortran

- Record compiler identity and full version, such as `gfortran --version`.
- Record compile and link flags from Pixi tasks, Makefiles, Meson, CMake, or build logs.
- Record linked numerical libraries, OpenMP or MPI versions, preprocessing flags, default integer and real kind choices, and platform architecture.
- Preserve a command that rebuilds from clean source and a small qualification case when one exists.

## Verification

With `--verify`, use a throwaway environment or build directory. Restore the
declared locks, compile applicable Fortran targets, and run the smallest
documented smoke test. Do not overwrite the working environment. A missing
runtime, network restriction, licensed dependency, or restricted input is
`UNVERIFIED`, not PASS.

## Output

Write `quality_reports/computational-requirements.md` unless project guidance
sets another evidence location. Include:

- operating system and architecture;
- R, Python, and Fortran versions that apply;
- lockfiles and package sources;
- compiler and linker flags;
- seeds and RNG kind;
- canonical entry command and expected runtime;
- verification command, exit status, and date;
- sealed run IDs and RO-Crate export paths when the capture supports an archive;
- unavailable checks and restricted inputs.

Reference detailed machine output, including `sessionInfo.txt`, rather than
copying hundreds of package lines into the report. Never claim byte identity
unless a clean reconstruction was executed and compared.
