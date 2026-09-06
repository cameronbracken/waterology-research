# Workflow registration and reproducible deliverables

Status: implemented. See [the workflow guide](../../workflow-execution.md) for
the final interfaces and [validation record](../../validation/2026-09-06-workflow-reproducibility.md)
for evidence and qualification boundaries. This document retains the accepted design.

## Purpose and ownership

Waterology should make a research project easier to execute, inspect and reproduce.
Keep `waterology.toml` as the portable registry of named workflows, evidence
contracts and deliverables. Researchers should not have to maintain duplicate
task definitions or manually register each result.

- Environment managers own dependencies, locks, environment creation and their
  native tasks. Support Pixi, uv and rv through explicit adapters without
  assuming they expose equivalent task or lock interfaces.
- TORC owns compute jobs, nodes, active execution and job dependencies. Existing
  TORC YAML remains authoritative for those definitions.
- Waterology owns experiment trees, study intent, portable workflow entry points,
  captured evidence, result comparisons and reproducibility verification.
- Skills help formulate and invoke workflows. Every lifecycle operation must
  remain available through shared services and the CLI without an agent runtime.

Native capabilities to reuse:

- [TORC workflow definitions](https://natlabrockies.github.io/torc/latest/core/concepts/workflow-definition.html)
  define jobs and dependencies.
- [TORC workflow creation](https://natlabrockies.github.io/torc/latest/core/workflows/creating-workflows.html)
  supports validation and file dependency inference.
- [Pixi task definitions](https://github.com/prefix-dev/pixi/blob/main/docs/reference/pixi_manifest.md)
  support task aliases, dependencies, inputs and outputs.

Verify the supported installed versions before implementing adapters. Do not
build another dependency resolver, scheduler or package manager.

## Current implementation and gaps

`src/waterology/core/config.py` defines a single command with outputs, metrics,
environment files, resources and archive settings. `core/project.py` initializes
generic defaults. `torc/workflow.py` renders that command as one TORC job.
`core/archive.py` preserves source and run evidence and verifies archive integrity.
`core/studies.py` and the study controller already provide bounded execution
records. These services should be extended rather than replaced.

Missing pieces are named workflow registration, project discovery and refresh,
execution of existing multi-job TORC definitions, an explicit final deliverable,
and a fresh-run reproduction check. Skill instructions currently expose many
low-level operations and leave their assembly to the agent.

## Proposed researcher interface

```console
waterology init
waterology config refresh --check
waterology config refresh
waterology workflow list
waterology workflow register evaluate --torc workflows/evaluate.yaml
waterology workflow run evaluate
waterology deliverable register final --workflow simulate --validator validate
waterology reproduce final
```

Retain existing study commands. Extend study creation to reference a named
evaluation workflow and automatically register its stable contract reference.
Expose the same services through MCP and relevant dashboard actions.

`workflow run` should create the required execution record, submit through the
resolved TORC profile, collect results and retain terminal evidence automatically.
Ordinary baseline and final-deliverable runs must work at an existing clean commit
without creating an artificial code change. Candidate experiments still retain
their branch, parent and committed variant identity.

Workflow entries reference a native TORC file or an environment-manager command.
For the latter, Waterology generates a minimal TORC wrapper. A named command such
as `final` selects the appropriate workflow and validation contract. Multi-job
ordering belongs in TORC; native task dependencies stay in the environment
manager. Do not translate and maintain the same dependency graph in three files.

## Registration and records

The TOML registry holds stable names and references for workflows, study contracts
and deliverables. Invocation registers a missing explicit definition before
execution, validates it and snapshots the resolved configuration. Repeated
registration of the same definition is idempotent. A name collision with a
different definition must produce a specific conflict, not replace it silently.

Generated records under `.waterology/` hold study IDs, experiment lineage, runs,
job identities, attempts, outputs and assessments. Avoid rewriting committed TOML
for every metric or iteration. Automatically capture favorable, unfavorable,
failed, cancelled and unresolved attempts. An unresolved submission remains
reconcilable and never triggers a blind duplicate submission.

Write registration atomically under project coordination, preserve comments and
manual fields, and commit or require inclusion of the resulting execution
contract in the source snapshot before compute. Concurrent registrations must
not lose entries. Do not change a running study's pinned contract during refresh.
Use a canonical project registry with explicit reconciliation of definitions
created in candidate worktrees; never modify a candidate that is already queued.

## Project-aware initialization and refresh

Inspect project manifests and locks, native task declarations, TORC workflow
files, and explicit input/output declarations. Discovery reads configuration;
it does not execute discovered commands. Record why a default was selected.

Infer environment files from actual files and workflow entries from explicit
native definitions. Do not guess scientific metrics, seeds, acceptance thresholds,
data access rights or remote profiles. Multiple plausible environments or
evaluation tasks remain unresolved until selected. Existing result files alone
do not establish the intended output contract.

Refresh compares recorded discovery with the current project. Add unambiguous
discoveries and update fields still owned by discovery. Preserve manual overrides,
surface removed/renamed references and mark affected workflows as needing repair.
Do not silently delete registrations or loosen reproducibility requirements.
`--check` reports drift without mutation and supports CI. Repeated refresh should
produce no diff when the project is unchanged.

Execution should perform lightweight drift detection automatically. Safe additive
registration may proceed within the requested work. Changes affecting frozen
evaluation identity require a new contract, while ordinary unresolved choices
produce an actionable diagnostic. No background watcher is required.

## Reproduce the final deliverable

A deliverable identifies the selected source revision or exported source,
workflow, environment locks, input identities and retrieval instructions,
expected outputs, validation procedure and reference evidence. Record a selection
explicitly; do not infer the final result from the latest or numerically best run.

`reproduce` creates a fresh isolated destination, restores the declared environment
through its manager, obtains and verifies inputs, submits through TORC, collects
new outputs and evaluates them against the pinned validation contract. Preserve
the original evidence and write a separate reproduction record.

Support byte equality, numeric tolerances and declared statistical criteria as
distinct validation modes. A successful process or intact archive does not prove
reproduction. Record missing inputs, unavailable platforms, failed execution and
failed output checks separately. Restricted inputs may use externally supplied
paths with verified identities; an access description is not proof of access.

Cached outputs cannot count as a fresh rerun. Reuse package caches where safe,
but use new output paths and disable or invalidate native task output caches
through documented manager capabilities. Capture actual worker environment
evidence rather than treating controller metadata as worker metadata.

Provide an export that includes the selected source, registry, native workflow
files, environment declarations, validation contract and redistribution-eligible
inputs or retrieval manifest. Reproduction must not depend on the original
checkout, agent transcript or SQLite index. Preserve the selected provenance
records explicitly because `.waterology/` is ordinarily ignored by Git.

## Implementation order and acceptance

1. Extend the configuration schema with named workflows and deliverables and
   implement comment-preserving registration. Keep schema-v1 single-command
   projects working. Test round trips, collisions and concurrent writes.
2. Add project discovery, initialization and refresh. Cover Pixi, uv, rv,
   mixed environments, absent locks, ambiguous tasks, manual overrides and drift.
   Test only adapter behavior actually supported by each manager.
3. Extend shared execution services for named workflows and existing TORC YAML.
   Preserve native job dependencies and archive all job outcomes and outputs.
   Test a multi-job graph, upstream failure, restart and submission uncertainty.
4. Connect study creation and ordinary experiment execution to automatic
   registration and collection. Demonstrate the complete lifecycle through CLI
   alone, including unchanged baseline code and negative results.
5. Add deliverable selection, portable export and reproduction. Prove a fresh
   rerun against fixed reference outputs and detect intentional input, output,
   environment and tolerance drift. Test missing restricted inputs and stale
   cached outputs. Do not claim remote or cross-platform support without runs.
6. Update canonical skills one at a time after their service entry points exist.
   Route autoresearch, simulation-study and replication through the same CLI/MCP
   lifecycle. Keep domain reasoning in skills and execution state in services.
   Regenerate runtime commands and agents instead of editing generated files.
7. Publish a full configuration reference covering every existing and new option:
   type, default, required conditions, discovery behavior, ownership, relative-path
   base, example, compatibility and effect on reproducibility. Include minimal
   existing-project setup, research, engineering and final-reproduction examples.

Run focused behavior tests at each step, then the repository's required pytest,
Ruff, render and constraint checks. Include a bounded local TORC smoke workflow
and a fresh-directory reproduction test. Runtime-free CLI completion is a release
criterion. No live compute run is authorized merely by reading or registering a
workflow definition.
