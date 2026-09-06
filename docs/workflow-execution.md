# Execute and reproduce a project

Waterology connects a project's execution commands to its experiment history and
result evidence. Skills facilitate these operations; the CLI implements the full
lifecycle without an agent. Pixi, uv or rv owns the environment. TORC owns jobs,
compute resources and dependencies. `waterology.toml` names workflows and defines
what evidence to preserve and how to validate a selected deliverable.

## Initialize an existing project

```console
waterology init
waterology workflow list
waterology config refresh --check
waterology config show
```

Initialization discovers root Pixi tasks and literal outputs, environment files,
and `workflows/*.yaml` / `*.yml` TORC definitions. Root `torc.yaml` and
`workflow.yaml` files (also `.yml`) are recognized. It reads configuration without executing
it. `waterology config refresh` applies discoveries while preserving manually
changed workflows and other options. `--check` reports drift without writing and
returns a nonzero status when updates or unresolved drift exist.

Discovery cannot infer the scientific metric, acceptance criterion or which task
is the final evaluation. A missing lock, multiple environment managers, a name
collision or a removed native workflow requires inspection. uv and rv files are
recognized, but their execution and restore commands are explicit. The tools do
not have interchangeable task interfaces.

Inspect the resolved definitions and select a configured TORC profile. Named
workflows require TORC even for local compute. The legacy `direct` profile remains
available to the older single-command API. Keep profile endpoints and credentials
in machine configuration, described in [configuration](configuration.md).

## Register and run an evaluation

For a discovered task:

```console
waterology workflow register evaluate --task evaluate
```

For a native TORC definition:

```console
waterology workflow register evaluate --torc workflows/evaluate.yaml
```

Use a definition file to specify evidence and restoration, for example `workflow.nt`:

```nestedtext
command:
    - pixi
    - run
    - --locked
    - evaluate
outputs:
    - results/metrics.json
environment_files:
    - pixi.toml
    - pixi.lock
restore:
    -
        - pixi
        - install
        - --locked
environment_probe:
    - pixi
    - info
    - --json
metrics:
    -
        name: rmse
        path: results/metrics.json
        field: rmse
```

Replace `command` with `torc_file: workflows/evaluate.yaml` to retain native TORC
jobs and dependencies. Workflow paths are relative to the project root, including
paths in native YAML. TORC validates the staged workflow before submission.
Waterology adds metadata and an environment setup job when restoration is declared.
The native jobs depend on that setup job. Environment probes run on workers and
are preserved in job logs. Configure a probe appropriate to the actual runtime,
such as an R session inventory for an R workflow.

```console
waterology workflow register evaluate --definition workflow.nt
```

Registration is idempotent. A conflicting definition is rejected. Edit a registered
entry intentionally when its contract must change, then commit it with the code.
Generated outputs should be ignored by Git and covered by `artifact_roots`.
Automatic discovery adds artifact roots for explicit native output declarations;
explicit registration adds artifact roots for its declared outputs.

```console
waterology workflow run evaluate --profile local
```

This creates an experiment at the current clean commit, submits to TORC, waits,
extracts metrics and seals the outputs and logs. No artificial code change is
needed for a baseline or final run. Use `--detach` to submit without waiting and
`waterology workflow watch RUN_ID` to resume collection. The existing run status,
logs and cancellation commands remain available. Failed and unresolved attempts
remain recorded. A lost submission response does not authorize another submission.

CLI, MCP and dashboard inspection use these same records. Run IDs and measured
values live under `.waterology/`; iterations do not rewrite the TOML registry.

## Research and engineering studies

Use the [managed study contract](managed-studies.md) for candidate iterations.
Set `workflow: evaluate`. The CLI registers the contract path and creates a
baseline when `baseline_experiment` is omitted. Existing contracts that identify
a baseline remain supported. The runtime driver carries the workflow into its
candidate experiments. For manual candidates, use:

```console
waterology experiment create "Candidate objective" --workflow evaluate
waterology study create study-contract.nt --profile local --authorized-by "Recorded user authorization"
```

Supply the actual authorization and contract. Research mode retains scientific
assessments; engineering mode evaluates declared acceptance thresholds. Workflow
execution alone does not choose a scientific conclusion or a final deliverable.
The saved study owns its frozen evaluation. Refreshing an unrelated registry entry
does not modify the source or configuration of running candidate worktrees.

## Select and reproduce the final result

Create `final.nt` after explicitly selecting a completed reference run:

```nestedtext
workflow: evaluate
reference_run: run-REPLACE_WITH_ACTUAL_ID
checks:
    -
        path: results/metrics.json
        mode: numeric
        field: rmse
        atol: 0.000001
        rtol: 0
```

The tolerance is illustrative, not a default recommendation. Choose a tolerance
that matches the calculation. Use `mode: bytes` for exact file equality. Numeric
checks compare finite scalar JSON values selected by a dotted field path.

```console
waterology deliverable register final final.nt
waterology reproduce final reproduction-check --profile local
waterology deliverable export final deliverable-export
```

Reproduction restores the source tree and original commit object from the sealed
archive, preserving its identity without creating a substitute commit. It creates
a new experiment worktree, restores the declared environment through TORC, runs
with new output locations and checks the output against the reference. It requires
environment declarations, restoration commands and a worker environment probe.
Package download caches can be reused; prior task outputs cannot be supplied as
fresh results. Tracked generated outputs in declared output paths are rejected.

To reproduce an export with the original checkout unavailable:

```console
waterology reproduce final fresh-check --path deliverable-export --bundle --profile local
```

`reproduction.json` retains execution IDs, validation outcomes and failure reasons.
Use `--resume` with the same destination after interruption. Missing prerequisites
are `blocked`, output disagreement is `failed`, and all declared checks must pass
for `passed`. Resume preserves source, reference and validation identity.
If submission may have happened, reconcile the saved ID rather than retrying it.

Exports include tracked source, the original commit object, reference outputs,
configuration snapshots and checksums. They do not include Git history or harvest
ignored inputs. Supply external inputs through `--inputs INPUT_DIRECTORY`; each
file must match the workflow's SHA-256 identity. `input_instructions` records
retrieval/access guidance. Acquire restricted data through its approved process.
The exporter includes tracked input files because they are part of the selected
source; review the project contents before sharing an export.

For statistical validation, declare `mode: statistical` and `validator: NAME`.
The validator is another workflow in the selected source. It runs in the same
fresh worktree after the main calculation, with archived reference files under
`.waterology-reference/`. Its code must implement the declared statistical test
and exit unsuccessfully when the criterion or required inputs fail. Its run and
outputs are archived separately. Waterology does not invent a statistical test
from two point estimates.

Current portable source restoration accepts regular files and directories.
Symlinks and submodules require a different packaging strategy and are rejected.
Remote input mounts, worker software and platform compatibility require separate
qualification on the selected host. A local reproduction does not establish
identical results on every platform.
