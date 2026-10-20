# Apptainer for paper environments

Apptainer packs a pixi environment and a Linux userspace into one read-only
`.sif` file. Consider it when a paper needs a frozen environment that runs on
HPC or a reviewer's Linux machine. For daily work on macOS, pixi with a
committed `pixi.lock` and `detached-environments = true` remains the default.

This note records a decision under consideration. The example below has not
been built or tested in this repository.

## Where it fits

| Option | What it fixes | Cost |
| --- | --- | --- |
| pixi + committed lock | Package versions, system tools, tasks | None beyond committing the lock |
| [pixi-pack](https://github.com/Quantco/pixi-pack) | One file for archiving or offline transfer | Must unpack before running |
| [Apptainer](https://apptainer.org/docs/user/latest/) | One runnable file, pinned glibc and OS libraries | Linux only, needs a build host |
| Docker | Same as Apptainer | Daemon, root, image registry |

A committed lock already pins every conda package. Apptainer adds the layer
below conda: the base OS and its C library. That layer matters most on shared
Linux systems where the host OS changes underneath a project.

Compared with Docker, Apptainer runs as the calling user without a daemon,
mounts `$HOME` and the working directory by default, and stores the image as
one file. Most HPC centers already provide it. The project is hosted by the
Linux Foundation.

## Build an image from a pixi project

Apptainer runs only on Linux. On macOS, build and run images inside a Linux VM
such as [Lima](https://lima-vm.io/). The `pixi.lock` must include `linux-64`.

Save this as `apptainer.def` beside `pixi.toml`:

```
Bootstrap: docker
From: ghcr.io/prefix-dev/pixi:0.76.1-bookworm

%files
    pixi.toml /opt/project/pixi.toml
    pixi.lock /opt/project/pixi.lock

%post
    cd /opt/project
    pixi install --locked
    pixi shell-hook --shell bash > /opt/project/activate.sh
    pixi clean cache --yes

%runscript
    exec /bin/bash -c '. /opt/project/activate.sh && exec "$@"' bash "$@"
```

Build and run:

```bash
apptainer build env.sif apptainer.def
apptainer run env.sif python scripts/run.py
```

The container sees the project directory through the default bind mount, so
scripts and outputs stay on the host. Only the environment lives in the image.

Notes:

- `--locked` fails if the lock does not match `pixi.toml`, rather than solving
  again.
- For a strict archive, pin the base image by digest
  (`From: ghcr.io/prefix-dev/pixi@sha256:...`) instead of by tag.
- Pixi tasks do not run cleanly from the image, because the manifest is inside
  the read-only image. Call the task commands directly, or keep a small shell
  script that pixi tasks and `apptainer run` both call.
- Add `--containall` to isolate the run from host files and variables, and
  `--nv` for NVIDIA GPUs.
- For R, install `rv` in `%post` and restore packages from Posit Package
  Manager Linux binaries for the base OS (Debian bookworm here).

[pixitainer](https://github.com/RaphaelRibes/pixitainer) wraps these steps in a
`pixi containerize` command. It is young (v0.9 in October 2026), and the
definition file above is short enough to own directly.

## Archive with a paper

Deposit these together, for example on Zenodo:

- `apptainer.def`, `pixi.toml`, and `pixi.lock`
- `env.sif`, optionally signed with `apptainer sign`
- the base image digest and the Apptainer version used to build

The definition file and lock let someone rebuild the image. The `.sif` lets
them run it if a channel or base image later disappears.
