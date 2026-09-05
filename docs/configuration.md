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
