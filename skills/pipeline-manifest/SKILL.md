---
name: pipeline-manifest
description: >
  Map research scripts to inputs, outputs, dependencies, figures, and tables,
  then derive a topological run order. Use for replication packages, handoffs,
  pipeline audits, or tracing a reported artifact to its source.
metadata:
  claude-command:
    name: pipeline-manifest
    argument-hint: <project directory>
---

# Pipeline Manifest

<!-- Adapted from flonat/claude-research,
skills/pipeline-manifest/SKILL.md at commit
e7007d0b1e465ef96de7338599ca04079e83a972 (MIT, Copyright 2026 Florian
Burnat). Fortran discovery, Quarto linkage, and the run template are original
Waterology additions. See ATTRIBUTION.md. -->

Build `pipeline.md` at the project root. Read scripts and documents without
running the analysis. Do not edit scripts unless the user separately asks for
headers.

## Discovery

Scan `code/`, `src/`, `scripts/`, and project declared analysis directories for:

- Python: `.py`;
- R: `.R`, `.r`, `.Rmd`;
- Fortran: `.f90`, `.F90`, `.f95`, `.F95`, `.f`;
- other declared pipeline languages when present.

Exclude tests, environments, generated code, build directories, caches, and
archived exploratory work. Preserve filename case because Fortran suffix case
can signal preprocessing.

## Extract

For each script, record:

- purpose and canonical entry command;
- files read and written;
- scripts or compiled programs invoked;
- build dependencies, compiler, flags, and linked libraries;
- figures, tables, or inline values fed to `.qmd`, `.tex`, or manuscript files;
- whether each value was declared in a structured header or inferred from code.

Recognize common Fortran I/O: `open`, `read`, `write`, `inquire`, command line
arguments, and fixed unit mappings. Trace a wrapper that compiles or launches a
Fortran executable as well as the source file itself.

## Dependency graph

Match each input to the script that produces it. Build a directed graph and run
a topological sort. A cycle is a failure, not an arbitrary run order. Report:

- executable order and steps that may run in parallel;
- missing inputs with no producer and no declared external source;
- orphan scripts whose outputs reach neither another step nor a document;
- duplicate producers for one output;
- document artifacts with no producing script;
- produced outputs that no consumer uses.

## Output

Write these sections in `pipeline.md`:

1. Pipeline table: script, purpose, inputs, outputs, dependencies, and document linkage.
2. Figure and table manifest: document reference, output file, and producer.
3. Dependency graph using Mermaid when the graph remains readable, otherwise an adjacency list.
4. Topological execution order with parallel groups.
5. Diagnostics for cycles, missing inputs, duplicate producers, and orphans.
6. Evidence status and limitations for every inferred edge.

Preserve reviewed manual annotations when refreshing an existing manifest.
Copy [the bundled run template](templates/run-all.sh) to `scripts/run-all.sh`
only after the graph is acyclic and every canonical command is known. Its root
resolution assumes that destination. If another destination is required,
adjust and test `project_root`. Do not invent filenames to fill gaps.
