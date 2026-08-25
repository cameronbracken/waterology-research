# TORC Integration Implementation Plan

**Goal:** Add optional managed execution through TORC without changing direct execution or
reimplementing TORC scheduling.

**Branch:** `codex/slice-4-torc`

**Worktree:** `.worktrees/slice-4-torc`

**Base:** Slice 3 experiment core at `e7c4c75`

## Current TORC contract

This plan targets the current TORC workflow specification and CLI documented by the official
[workflow guide](https://natlabrockies.github.io/torc/latest/core/workflows/creating-workflows.html),
[workflow specification](https://natlabrockies.github.io/torc/latest/core/reference/workflow-spec.html),
and [remote worker guide](https://natlabrockies.github.io/torc/latest/specialized/remote/remote-workers.html).
TORC owns scheduling, workers, retries, Slurm submission, resource accounting, its TUI, and its
dashboard.

TORC's generated Python client currently requires Python below 3.14, while this repository's
development environment uses Python 3.14. Waterology will therefore depend on an internal gateway
protocol and ship a subprocess implementation over TORC's JSON CLI. Tests will use a fake gateway.
The protocol leaves room for a generated client adapter after its Python support catches up.

Waterology will submit from the experiment worktree so TORC's workflow submission directory points
at the committed variant. Commands will be converted from the configured argument array with
`shlex.join` for POSIX workers or `subprocess.list2cmdline` for Windows workers. No command input
will be accepted from a compute profile.

## Scope

The slice includes:

- Machine local compute profiles with provider, mode, API URL, TORC site profile, SSH alias, output
  root, dashboard URL, and trust state.
- A `prepare -> launch -> inspect -> cancel -> collect` provider protocol shared by direct and TORC
  execution.
- Deterministic TORC workflow generation for local, remote worker, and Slurm modes.
- Durable TORC workflow and job references, state reconciliation, and terminal collection into the
  existing immutable run archive.
- First use confirmation for remote profiles.
- CLI commands for managed run start, watch, cancel, profile inspection and trust, and TORC TUI or
  dashboard handoff.
- Doctor checks and documentation for the optional TORC integration.

Agent session ownership and resume belong to Slice 5. The Waterology dashboard belongs to Slice 6.
Actual SSH, Slurm, or public network execution is outside automated tests.

## Task 1: Machine compute profiles

**Files:**

- Create `src/waterology/core/profiles.py`.
- Modify `src/waterology/core/config.py` only for portable project resource requests and the default
  profile name.
- Create `tests/core/test_profiles.py` and extend `tests/core/test_config.py`.

**Behavior:**

1. Write failing tests for XDG and explicit config path discovery, strict TOML parsing, supported
   modes, normalized paths, missing profiles, and atomic trust updates.
2. Add immutable profile models. Accept `local`, `remote`, and `slurm`; require an SSH alias for
   remote mode and never accept credentials.
3. Store trusted profile names only in machine configuration. Expose an explicit environment
   override for test and automation use.
4. Add portable CPU, memory, wall time, and GPU requests to committed project configuration.

## Task 2: Provider contracts and durable executor references

**Files:**

- Create `src/waterology/core/providers.py`.
- Modify `src/waterology/core/records.py`, `database.py`, and `repair.py`.
- Add migration `src/waterology/core/migrations/002_torc_execution.sql` if migrations are split into
  resources; otherwise extend the existing migration registry.
- Create `tests/core/test_providers.py`; extend database and repair tests.

**Behavior:**

1. Define typed prepare, launch, inspection, cancellation, and collection records.
2. Keep the direct executor available through the same interface without changing its archive
   semantics.
3. Persist provider, compute profile, workflow ID, job IDs, TORC version, API URL, execution mode,
   last known state, and last observation time.
4. Preserve backward compatibility for Slice 3 manifests and rebuild the new index fields during
   repair.

## Task 3: Deterministic TORC workflow generation

**Files:**

- Create `src/waterology/torc/workflow.py` and package initialization.
- Create `tests/torc/test_workflow.py` with golden mappings.

**Behavior:**

1. Write failing tests for stable YAML, safe argument quoting, explicit execution mode, resource
   mapping, job and workflow names, metadata, outputs, and rejection of invalid paths.
2. Generate one TORC job from the fixed committed project command. Include Waterology run,
   experiment, and commit identifiers as metadata.
3. Stage the generated workflow beside other run staging data and record its digest.
4. Do not emit secrets, machine credentials, or implicit `auto` execution mode.

## Task 4: TORC gateway and command contracts

**Files:**

- Create `src/waterology/torc/gateway.py` and `src/waterology/torc/errors.py`.
- Create `tests/torc/test_gateway.py`.

**Behavior:**

1. Define an injectable gateway protocol and normalized TORC workflow, job, and result records.
2. Implement the official TORC CLI boundary with argument arrays, JSON output, explicit working
   directory, timeout handling, redacted errors, and `TORC_CLIENT__API_URL` scoped to the child.
3. Cover create dry run, create, run or submit, inspect, cancel, version, TUI, dashboard URL, remote
   worker startup, and log collection without invoking a real server in unit tests.
4. Convert malformed JSON, missing binaries, incompatible versions, timeouts, and unavailable API
   responses into stable Waterology errors.

## Task 5: TORC provider launch and remote confirmation

**Files:**

- Create `src/waterology/torc/provider.py`.
- Extend `src/waterology/core/execution.py` and `tests/core/test_execution.py`.
- Create `tests/torc/test_provider.py`.

**Behavior:**

1. Prepare and validate the generated workflow before recording launch intent.
2. Require an explicit confirmation for the first use of remote and Slurm profiles. Persist trust
   only after confirmation succeeds. Noninteractive use without prior trust must fail safely.
3. Create the TORC workflow, launch it in the configured mode, and durably store returned IDs and
   the TORC version.
4. If launch fails after intent is recorded, preserve the staging record and a diagnostic that can
   be reconciled or collected.

## Task 6: Inspection, reconciliation, and cancellation

**Files:**

- Create `src/waterology/torc/states.py` and `src/waterology/torc/reconcile.py`.
- Extend provider and database tests.

**Behavior:**

1. Test every documented TORC workflow and job state, including unknown future states.
2. Map TORC observations into Waterology's smaller state model. An unreachable service produces
   `unknown`, never `failed`.
3. Restore the prior known state when service access returns. Use `lost` only when a successful
   reconciliation confirms that the recorded workflow is absent.
4. Make cancellation idempotent and retain both requested intent and observed terminal state.

## Task 7: Terminal collection and archive sealing

**Files:**

- Extend `src/waterology/core/archive.py` and TORC provider modules.
- Extend archive, repair, and TORC provider tests.

**Behavior:**

1. Collect TORC logs, normalized resource metrics, result metadata, and declared project artifacts
   into the existing staging archive.
2. Validate every collected path and reject symlinks or traversal before copying.
3. Add executor references to the manifest while retaining schema compatibility for direct runs.
4. Seal only after terminal observation and successful collection. Missing expected outputs remain
   in `collecting` and keep recoverable staging metadata.

## Task 8: CLI and doctor integration

**Files:**

- Modify `src/waterology/cli.py` and `src/waterology/runtime/doctor.py`.
- Add CLI and doctor tests.

**Behavior:**

1. Extend `run start` with `--profile`; keep direct execution as an explicit supported path.
2. Add `run watch` and `run cancel` with stable JSON events and interrupt handling.
3. Add profile list, show, and trust commands. Never print credentials or full inherited
   environments.
4. Add TORC TUI and dashboard handoff commands that print the exact command or URL in dry run and
   JSON modes.
5. Doctor will report profile validity, TORC binary and version, and optional API reachability.
   Missing TORC must not break direct execution, archive inspection, or existing commands.

## Task 9: Documentation, attribution, and release checks

**Files:**

- Modify `README.md`, `ATTRIBUTION.md`, and relevant package metadata.
- Add packaging tests when optional metadata or new resources require them.

**Behavior:**

1. Document installation, profile examples, trust, execution modes, reconciliation, collection,
   and TUI or dashboard handoff.
2. Credit TORC and its BSD 3-Clause license. No TORC source will be copied.
3. Run the focused tests after each task, then run:

```bash
pixi run pytest
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
git diff --check
```

4. Build the wheel and run packaging tests against it.
5. Request an independent review. Resolve all release blockers, repeat the full checks, and create a
   signed commit. Do not merge or push without permission.

## Completion evidence

- `pixi run pytest`: 345 passed.
- `pixi run ruff check .`: passed.
- `pixi run waterology render --check`: generated assets current.
- `python3 constraints/check-all.py .`: 3 of 3 constraints passed.
- `git diff --check`: passed.
- Wheel and source distribution built successfully; 12 packaging tests passed.
- TORC 0.39.0 accepted generated default, explicit resource, POSIX, Windows, and Slurm workflow
  variants in independent review.
- Independent review found no remaining release blockers.
