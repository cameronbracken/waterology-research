# Pipeline Manifest

Use when building a replication package, onboarding to a multi-script repository, or tracing manuscript figures/tables back to producing code. Do not execute long analyses while mapping the pipeline.

## Discovery and extraction

Scan `src/`, `scripts/`, `code/`, and analysis folders for `.py`, `.R`/`.r`/`.Rmd`, and `.f90`/`.F90`/`.f95`/`.f` (preserving Fortran case, excluding tests, caches, `.pixi/`, and build outputs). For each script record:

- Canonical command, inputs read, outputs written, and downstream `.qmd`/`.tex`/report consumers (including Fortran `open`/`read`/`write` units and build wrappers).
- Whether dependencies were declared explicitly or inferred from source.

## Dependency graph and `pipeline.md`

Build a directed graph and run a topological sort (flag cycles, missing upstream inputs, duplicate output producers, and orphan scripts/figures). Write `pipeline.md` at the project root with:

1. Script-to-I/O table and Figure/Table-to-producer manifest.
2. Dependency diagram ([diagrams](../../waterology-diagrams/SKILL.md) or Mermaid when compact) and parallelizable topological run order.
3. Missing-input, cycle, or orphan diagnostics.

When the graph is acyclic and commands are verified, optionally populate `scripts/run-all.sh` from [`../templates/run-all.sh`](../templates/run-all.sh).
