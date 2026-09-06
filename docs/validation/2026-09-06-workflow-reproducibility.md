# Workflow registration and reproducibility validation

This change implements the [accepted workflow plan](../superpowers/plans/2026-09-06-workflow-reproducibility.md).
Named workflow definitions and final deliverables are registered in
`waterology.toml`. Generated attempts and results remain in durable records.
CLI, MCP and skills use shared services. The dashboard displays the same registry.

## Behavior checked

- Project discovery finds root Pixi tasks, environment declarations and native
  TORC YAML. Refresh preserves comments and manual overrides. Registration is
  idempotent and concurrent updates retain every entry. Ambiguous discoveries
  remain unresolved; removed discovered tasks cannot execute silently.
- Named baselines execute unchanged committed source through TORC. The legacy
  direct executor cannot bypass this rule. Existing configuration and study
  payloads retain their fingerprint shape when new options are absent.
- Multi-job graphs preserve native dependencies. Failed upstream jobs with blocked
  descendants resolve as failures when no runnable work remains. Unknown
  submissions retain their capacity reservation and identity.
- All TORC runs snapshot execution settings. Archives retain bounded, redacted
  job-specific logs, source commit objects, source trees and output evidence.
  Worker environment probes are distinct from controller metadata.
- Exported source restores its original commit and tree without the original
  repository or its history. Reproduction uses new output paths, verifies input
  identities and compares outputs with byte, numeric or explicit statistical
  criteria. It does not infer scientific support from completion.
- Resume rejects changed source, locks, configuration and preexisting outputs.
  An unsubmitted ID can resume after prerequisite repair. Reserved preparation
  failures are retained as failures. Submission uncertainty never triggers a
  duplicate attempt.
- Statistical validation checks staged inputs against archived evidence before
  and after execution. Validator archives and terminal reproduction records are
  checked for integrity. Paused validators cannot accept modified inputs.

## Automated verification

The full pytest output is saved in
[the test log](2026-09-06-workflow-reproducibility-pytest.txt).
Required checks are:

```console
pixi run pytest -q
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
git diff --check
```

Final result: 581 tests passed in 110.46 seconds. The warnings report an upstream
AnyIO deprecation and unavailable Zotero credentials in a provenance test. Ruff, generated-file
verification, all eight project constraints and whitespace checks passed.

The three changed canonical skills were edited and checked individually. Generated
runtime assets required no changes. A separate reviewer inspected the execution
boundaries and subsequent fixes. The final focused review found no remaining
blocker among its reported findings.

## Live local qualification

The bounded smoke script executes through the CLI:

```console
pixi run python scripts/smoke-workflow-reproduction.py NEW_DIRECTORY
```

It starts an isolated loopback TORC server, creates a Pixi project with two jobs
and an explicit dependency, records its result, exports a deliverable, makes the
original checkout unavailable, restores a fresh project and environment, and
checks the reproduced numeric output. The script saves `validation.json`, run
logs, reference archives and reproduction records in its new destination.

The final local qualification passed on 2026-09-06. Reproduction
`reproduction-8fdeb941a456426b`, run `run-f4ad82c1ff14`, passed the numeric
comparison for `results/value.json`. Worker environment evidence was retained in
`job-logs.json`.

Qualification environment: macOS arm64, Python 3.14.7 from conda-forge,
Pixi 0.76.1 and TORC 0.40.0. The synthetic value tests execution and evidence
handling, not model skill. The project lockfile records the development packages.

## Remaining qualification boundaries

Remote and Slurm workers, multiple physical workers and native Windows/Linux
reproduction need separate runs on their selected environments. uv and rv
manifest discovery is tested; this change does not claim a live restoration
qualification for either manager. Their execution and restore commands remain
explicit, while Pixi root tasks are discovered automatically.

Portable source restoration currently accepts regular files and directories.
Symlinks and submodules are rejected. Ignored/restricted inputs are supplied
explicitly and checked by hash. Exports include tracked source and reference
outputs, so input redistribution remains a project decision.

Workflow commands remain executable researcher code. A validator must implement
its stated domain criterion. Output agreement and file integrity do not by
themselves establish that a scientific claim is supported.
