# Configuration

Waterology separates portable project settings from machine settings and credentials.

| File or environment | Scope | Commit it? |
| --- | --- | --- |
| `waterology.toml` | Research command, outputs, resources, and archive contract | Yes |
| `$HOME/.config/waterology/config.toml` | Compute profiles for one machine | No |
| SSH and TORC configuration | Host access and service credentials | No |
| `WATEROLOGY_CONFIG` | Alternate machine configuration path | No |

## Project configuration

`waterology init` creates `waterology.toml`. Paths must be relative to the project and use forward
slashes.

```toml
schema_version = 1
name = "flood-study"
artifact_roots = ["artifacts", "results"]
command = ["pixi", "run", "analysis"]
environment_files = ["pixi.toml", "pixi.lock"]
outputs = ["results/metrics.json"]
default_compute_profile = "direct"

[concurrency]
max_runs = 1

[resources]
cpus = 4
gpus = 0
memory_mb = 8192
walltime_minutes = 60

[archive]
allow_missing_outputs = false
environment_allowlist = ["OMP_NUM_THREADS"]
log_redactions = ["token=[^\\s]+"]

[[metrics]]
name = "rmse"
path = "results/metrics.json"
format = "json"
field = "rmse"
```

`command` is an argument array, not a shell string. `outputs` may not overlap. Metric extractors read
named fields from JSON files after successful execution.

## Machine compute profiles

Machine profiles live outside the repository. A profile selects TORC local, remote, or Slurm
execution without putting hostnames or accounts into a portable project file.

```toml
[profiles.local]
provider = "torc"
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"
target_shell = "posix"

[profiles.worker]
provider = "torc"
mode = "remote"
api_url = "http://control-host:8080/torc-service/v1"
ssh_alias = "worker"
access_group_id = 2
target_shell = "posix"
```

Remote profiles require an SSH alias and a TORC API URL that the worker can reach. Set
`access_group_id` when authenticated workers use separate identities and TORC enforces workflow
ownership. Waterology shares each new remote workflow with that group before starting the worker.
Slurm profiles also require `slurm_account` and may specify `torc_profile`. Neither mode accepts a
loopback URL; loopback is valid only when execution stays on the server host.

Keep passwords, tokens, SSH keys, and private environment values out of both Waterology files.
Waterology passes the current process environment to TORC, so use TORC's supported credential
environment when the server requires authentication.

Validate the result:

```console
waterology compute profile list
waterology compute profile show worker
waterology doctor --torc-profile worker
```

The first remote or Slurm run requires `--confirm-remote`. Waterology records that trust only in the
machine configuration.

## Complete project option reference

Use `waterology config schema` for the machine-readable JSON Schema, including
validation bounds. `waterology config show` displays the resolved settings. All
paths below are relative to the project root, use forward slashes and may not
escape it. Commands are argument arrays. The serializer retains schema version 1
and reads existing single-command projects without migration.

| Option | Type and default | Meaning and ownership |
| --- | --- | --- |
| `schema_version` | integer, `1` | Supported project schema version. |
| `name` | required string | Project identity; initialization uses the repository directory name. |
| `artifact_roots` | string array, `["artifacts"]` | Allowed output locations. Explicit discovered outputs add suitable roots. |
| `command` | string array, `[]` | Legacy project evaluation command. Named execution selects a workflow command. |
| `environment_files` | string array, `[]` | Environment manifests and locks whose identities are captured. Discovery populates existing files. |
| `outputs` | string array, `[]` | Legacy output paths to archive; paths must not overlap. |
| `default_compute_profile` | string, `"direct"` | Machine profile name. Select a TORC profile for named workflows and studies. |
| `concurrency.max_runs` | integer, `1`, minimum 1 | Maximum active Waterology runs, including unresolved submissions. |
| `resources.cpus` | integer, `1`, minimum 1 | CPU request for a generated single-job workflow. |
| `resources.gpus` | integer, `0`, minimum 0 | GPU request for a generated single-job workflow. |
| `resources.memory_mb` | integer, `1024`, minimum 1 | Memory request for a generated single-job workflow. |
| `resources.walltime_minutes` | optional positive integer | Runtime request. Omitted by default. |
| `archive.allow_missing_outputs` | boolean, `false` | Whether a completed run may omit declared outputs. Does not waive deliverable checks. |
| `archive.environment_allowlist` | string array, `[]` | Environment variables whose value hashes may be captured. Values are not stored. |
| `archive.log_redactions` | regex string array, `[]` | Redactions applied to aggregate and retained job logs. |
| `metrics` | metric table array, `[]` | Legacy metric extractors, described below. |
| `workflows` | named tables, `{}` | Registered execution/evidence definitions. Discovery and registration add entries. |
| `deliverables` | named tables, `{}` | Explicit selections of a reference run and output checks. |
| `study_contracts` | name-to-path table, `{}` | Stable references automatically registered by CLI study creation. |
| `discovery` | table, `{}` | Generated ownership metadata used by refresh; do not edit it manually. |
| `discovery.workflows` | name-to-hash table | Last discovered workflow identities, used to preserve manual edits. |
| `discovery.environment_files` | string array | Last discovered environment declarations. |
| `torc_file` | optional string | Resolved native YAML reference in execution snapshots. Prefer setting this inside a named workflow. |
| `restore` | array of argument arrays, `[]` | Resolved environment restore commands in execution snapshots. Prefer workflow declarations. |
| `environment_probe` | string array, `[]` | Resolved worker inventory command in execution snapshots. Prefer workflow declarations. |

Native TORC YAML owns its resource requirements and job dependencies. The project
`resources` defaults apply to generated command workflows; they do not overwrite
native job requirements. Machine configuration remains outside this file.

### Named workflows

Each `[workflows.NAME]` table supports:

| Option | Type and default | Meaning |
| --- | --- | --- |
| `command` | string array, `[]` | Native environment task or executable. Exactly one of `command` and `torc_file` is required. |
| `torc_file` | optional path | Existing TORC YAML with a nonempty job list. |
| `description` | string, `""` | Researcher-facing description. |
| `outputs` | string array, `[]` | Files or directories to preserve. Literal paths, no globs or overlaps. |
| `metrics` | metric table array, `[]` | Extract values after successful execution. |
| `environment_files` | string array, `[]` | Overrides project environment files when nonempty. Files must exist. |
| `restore` | array of argument arrays, `[]` | Ordered environment restoration commands executed by a TORC setup job. Required for reproduction. |
| `environment_probe` | string array, `[]` | Worker inventory command, recorded in job logs. Required for reproduction. |
| `input_files` | path-to-SHA-256 table, `{}` | Immutable local input identities, checked before submission and reproduction. |
| `input_instructions` | path-to-string table, `{}` | Retrieval/version/access guidance; never credentials or proof of access. |

Initialization discovers root Pixi tasks, not arbitrary shell scripts. Pixi
feature-specific environments and ambiguous mixed projects need explicit workflow
definitions. uv (`pyproject.toml`, `uv.lock`) and rv (`rproject.toml`, `rv.lock`, `.Rprofile`)
environment files are detected but no task syntax is
invented for them. For uv, an explicit definition can invoke `uv run --locked`
and restore with `uv sync --locked`. For rv, supply the commands supported by your
project's installed version. Environment managers perform restoration themselves.

Refresh preserves comments and manual values, updates definitions still owned by
discovery, adds new unambiguous workflows and reports removed or conflicting
references. It does not delete old definitions or modify frozen study records.
Commit changed execution declarations before starting a named workflow.

### Metric tables

Project `[[metrics]]` and `[[workflows.NAME.metrics]]` use the same options:

| Option | Type and default | Meaning |
| --- | --- | --- |
| `name` | required string | Metric name in the sealed result record. |
| `path` | required path | JSON file containing the value. |
| `format` | string, `"json"` | Only JSON extraction is currently supported. |
| `field` | required string | Field selector used by the existing JSON metric extractor. |

### Deliverables and output checks

Each `[deliverables.NAME]` table supports:

| Option | Type and default | Meaning |
| --- | --- | --- |
| `workflow` | required string | Workflow executed by the selected reference run. |
| `reference_run` | required run ID | Completed, verified archive with an execution snapshot. |
| `description` | string, `""` | Description of the selected result. |
| `checks` | required nonempty check array | Explicit reproduction criteria. All checks must pass. |

Each `[[deliverables.NAME.checks]]` table supports:

| Option | Type and default | Meaning |
| --- | --- | --- |
| `path` | required path | Output to check, relative to the project within archived artifacts. |
| `mode` | `"bytes"`, `"numeric"` or `"statistical"`; default `"bytes"` | Byte equality, scalar numerical comparison, or a domain validator. |
| `field` | optional string | Required for numeric mode; dotted JSON field path. |
| `atol` | finite nonnegative number, `0` | Absolute numeric tolerance. |
| `rtol` | finite nonnegative number, `0` | Relative numeric tolerance. |
| `validator` | optional workflow name | Required for statistical mode; must exist in the selected source. |

Tolerances and statistical criteria are authored decisions. Discovery never sets
them. See [workflow execution](workflow-execution.md) for complete setup, study,
export and fresh-reproduction examples.

Adapter references: [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
and [rv project layout](https://a2-ai.github.io/rv-docs/intro/getting-started/).
