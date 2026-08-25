# Slice 3 Experiment Core Implementation Plan

Date: 2026-08-25

Status: Complete

## Outcome

Add the local research core needed to initialize a project, create hypothesis
branches in isolated Git worktrees, run a committed variant with the direct
executor, seal and verify a run archive, record a scientific assessment, and
rebuild the SQLite index from durable records.

This slice does not add TORC, agent process adapters, MCP, or the dashboard.
Those remain in Slices 4 through 6.

## Starting evidence

- Branch: `codex/slice-3-experiment-core`
- Base revision: `f1d139a`
- Baseline: `pixi run pytest`, 176 passed on 2026-08-25
- The package contains runtime asset installation and validation code, but no
  research project service layer.
- The approved platform design defines project configuration, experiment and
  run states, archive contents, Git rules, SQLite recovery, and CLI groups.

## Progress

- [x] Task 1: Add project configuration and initialization.
- [x] Task 2: Add the SQLite index and event journal.
- [x] Task 3: Create experiments and Git worktrees.
- [x] Task 4: Build and verify immutable archives.
- [x] Task 5: Run committed variants with the direct executor.
- [x] Task 6: Record scientific assessments.
- [x] Task 7: Repair the index from durable records.
- [x] Task 8: Complete CLI output, documentation, and packaging.

## Architecture boundaries

Place research behavior under `src/waterology/core/`. The CLI may parse input
and format output, but it must call the same typed service functions that later
MCP and dashboard adapters will use.

Use these modules:

```text
src/waterology/core/
  archive.py       stage, seal, inspect, and verify run archives
  config.py        validated waterology.toml records and discovery
  database.py      migrations, transactions, events, and indexed records
  errors.py        stable error codes and structured details
  execution.py     direct provider and operational state transitions
  experiments.py   experiment records, assessments, and freeze rules
  git.py           explicit Git argument arrays and porcelain parsing
  project.py       initialization, paths, status, and service composition
  records.py       shared enums and Pydantic records
```

Numbered SQL migrations live in `src/waterology/core/migrations/` and ship in
the wheel. Tests use temporary Git repositories and never depend on the
developer checkout.

## Durable record contract

`waterology.toml` and sealed records under `.waterology/` outrank SQLite. Each
experiment receives an immutable creation record. Each terminal run receives a
sealed archive. Later assessments are append only records stored beside the
archive, so assessing a run does not modify sealed payloads. `repair-index`
rebuilds experiments, runs, and assessments from those records.

Every durable JSON record carries a schema version. Unsupported schema
versions stop repair with a structured error instead of dropping data.

## Task 1: Add project configuration and initialization

Create validated configuration records for the project name, artifact roots,
fixed command argument array, expected environment files, declared outputs,
metric extractors, concurrency, archive rules, and default compute profile.
Reject shell command strings and absolute or escaping project paths.

Add project discovery by walking from the requested path to the repository
root. `waterology init` writes a minimal `waterology.toml`, creates the local
state layout, and adds exactly one `.waterology/` entry to `.gitignore` without
ignoring configuration or artifacts. Repeated initialization must be safe.

Tests:

- `tests/core/test_config.py`
- `tests/core/test_project.py`
- focused CLI tests for `init` and `status --json`

## Task 2: Add the SQLite index and event journal

Add forward only numbered migrations for projects, experiments, runs,
assessments, artifacts, and events. Open SQLite in WAL mode with a busy timeout
and short explicit transactions.

Each mutation records an intent before an external action and an observation
afterward. Interrupted intents remain queryable for later reconciliation.
Database records are indexes of durable state, not the only copy of research
evidence.

Tests:

- migrations apply once and in order
- an unsupported newer schema fails clearly
- event intent and observation ordering survives a reopened connection
- concurrent connections honor the configured busy timeout

## Task 3: Create experiments and Git worktrees

Add a Git wrapper that accepts argument arrays, sets an explicit working
directory, and parses stable porcelain output. Experiment creation resolves a
frozen parent commit, generates a collision resistant identifier, creates a
`waterology/<experiment-id>` branch and `.waterology/worktrees/<experiment-id>`
worktree, writes the experiment creation record, and indexes the result.

Record hypothesis, parent experiment, base commit, branch, worktree, owner,
creation time, and status. Refuse paths outside local state, existing branch or
directory collisions, and a second writable owner. Do not merge, rebase, push,
or remove worktrees.

Tests use temporary repositories to cover creation, tree relationships,
collisions, owner conflicts, list, show, and notes.

## Task 4: Build and verify immutable archives

Create run archives in `.waterology/staging/<run-id>` and atomically rename a
complete archive into `.waterology/runs/<run-id>`. Include the files specified
by the platform design. Build `source.tar.zst` from the recorded Git commit,
not from uncommitted worktree contents.

Allowlisted environment metadata includes platform details, tool versions,
configured environment file hashes, and the compute profile. Never record the
complete environment. Artifact collection resolves symlinks and rejects paths
outside the worktree or declared roots.

Hash every payload except `checksums.sha256`, write the checksum file last, and
never overwrite an existing sealed run. Verification reports missing, changed,
and unexpected payloads with a stable result record.

Tests cover deterministic manifests, hash failures, path traversal, symlink
escape, missing declared outputs, staging recovery, and destination collision.

## Task 5: Run committed variants with the direct executor

Implement the provider sequence `prepare -> launch -> inspect -> collect` for
one local subprocess. Require a clean experiment worktree and a committed
variant. Run only the configured argument array with no implicit shell. Capture
stdout, stderr, process identifier, timestamps, exit status, and declared
outputs.

The first CLI implementation may wait for the direct process to finish. It
must still persist each operational transition so later agent and TORC work can
reuse the state model. Cancellation and asynchronous process recovery remain
for the provider and session slices unless they are needed to preserve a
started direct run.

Tests cover successful and failing commands, dirty worktrees, uncommitted
variants, exit status mapping, logs, exact commit capture, and archive sealing.

## Task 6: Record scientific assessments

Support `unassessed`, `invalid`, `no_answer`, and `answer`. An assessment stores
the conclusion, evidence references, author, timestamp, and optional note.
Append a durable assessment record and index it without changing the run
archive.

An `answer` freezes its experiment. Two consecutive `no_answer` assessments
set a decision required flag. Operational completion alone never freezes an
experiment. Reject assessments for nonterminal runs and evidence paths outside
the project artifact or run archive roots.

Tests cover state independence, freeze behavior, the consecutive no answer
rule, and append only assessment history.

## Task 7: Repair the index from durable records

Implement index repair into a new temporary database. Scan project
configuration, experiment records, sealed run manifests, and assessment
records. Validate schemas and archive identifiers before importing. Replace
the old index atomically only after the rebuilt database passes integrity and
referential checks.

Report imported counts, rejected records, and warnings in a typed result. A
failure leaves the prior database untouched. Test deletion and full rebuild,
corrupt records, unsupported schemas, duplicate identifiers, and interrupted
replacement.

## Task 8: Complete CLI output, documentation, and packaging

Expose the Slice 3 commands:

```text
waterology init
waterology status
waterology experiment create|list|show|note
waterology worktree open|list
waterology run start|list|status|logs|assess
waterology archive list|show|verify
waterology repair-index
```

Read and status commands support `--json`. Mutating commands also return one
final JSON object when requested. JSON output contains no ANSI escapes. Errors
use stable codes, messages, and details with exit status 1. Invalid command
syntax remains a Typer usage error with exit status 2.

Update the README with a minimal local workflow. Package migrations and any
archive templates in the wheel. Mark Slice 3 complete only after every
acceptance check passes.

## Acceptance checks

Run after the final change:

```bash
pixi run pytest
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
```

Build and inspect the wheel. Run an end to end temporary repository test that
initializes a project, creates an experiment, commits a variant, runs it,
records an assessment, verifies the archive, deletes the database, repairs the
index, and confirms the same experiment and run remain queryable.

Request an independent review before integration because this slice adds the
durable research state model, process execution, and recovery behavior.

## Completion evidence

- Full suite: 231 tests passed on 2026-08-25.
- Ruff: all checks passed.
- Generated runtime assets: current.
- Repository constraints: 3 of 3 passed.
- Wheel inspection: core SQL migration and cross runtime assets present.
