# Getting started

Waterology records research experiments as committed Git variants. Each run keeps its command,
environment evidence, logs, metrics, outputs, and assessment together.

## Install

From a source checkout:

```console
pixi install
pixi run waterology --help
pixi run waterology doctor
```

Install the adapters needed by the current project:

```console
pixi run waterology install claude
pixi run waterology install codex
pixi run waterology install opencode
```

Use `--scope user` for user configuration. Preview changes with `--dry-run` when the command
supports it.

## Initialize a research project

Run the initializer at the repository root:

```console
waterology init
```

Initialization creates a small project configuration without copying native tasks. Register the
tasks Waterology should execute, or run `waterology config refresh --check` to inspect available
discoveries. See the [named workflow guide](workflow-execution.md).
For the legacy single-command interface below, set `command`, `environment_files`,
and `outputs` in the generated `waterology.toml`.
See [Configuration](configuration.md) for every field.

Commit the configuration before creating an experiment:

```console
git add waterology.toml .gitignore
git commit -m "Configure Waterology"
waterology experiment create "Test a longer calibration window" --owner cam
```

## Run and assess an experiment

Open the experiment worktree, make one scientific change, and commit it. Waterology will not run an
uncommitted variant.

```console
waterology worktree open <experiment-id>
waterology run start <experiment-id>
waterology run watch <run-id>
waterology archive verify <run-id>
```

After reviewing the archive, record an assessment with evidence paths:

```console
waterology run assess <run-id> answer "The evidence supports the hypothesis" \
  --author cam --evidence .waterology/runs/<run-id>/metrics.json
```

Use `direct` execution for the simplest setup. Use [TORC execution](torc.md) when a run needs managed
local processes, remote workstations, or Slurm.
