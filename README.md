# waterology-research

waterology-research is a set of skills, agents, and workflows for
[Claude Code](https://claude.com/claude-code),
[Codex](https://openai.com/codex/), and
[OpenCode](https://opencode.ai/). It supports research software in R, Python,
Fortran, Quarto, and LaTeX.

The package keeps research skills and agent definitions in the repository, then
installs runtime adapters for each supported tool. Packaging and agents support
all three runtimes. Research workflows are runtime neutral. Claude slash
commands are generated compatibility shims that invoke the canonical skills.

## What's here

```
skills/             canonical research skills
agent-definitions/  canonical agent definitions
agents/              generated Claude Code agents
.codex/agents/      generated Codex agents
.opencode/agents/   generated OpenCode agents
commands/           Claude Code compatibility commands
rules/              path scoped conventions
constraints/        paired checks run by check-all.py
.mcp.json           Claude Code and Codex plugin MCP registration
.codex/config.toml  Codex project MCP registration
opencode.json       OpenCode project MCP registration
ATTRIBUTION.md      citation ledger for adapted upstream material
```

## Install

Install the development environment, then install the runtime adapters needed
by the current project:

```console
pixi install
pixi run waterology install claude
pixi run waterology install codex
pixi run waterology install opencode
pixi run waterology install all --dry-run
pixi run waterology doctor
```

Project scope is the default. Use `--scope user` for user configuration.
`--target` is available only for project installs. Both `install` and `doctor` support `--json`.

For a user-scoped Codex install:

```console
pixi run waterology install codex --scope user
```

Root `skills/` is canonical. The Codex manifest is `.codex-plugin/plugin.json`.
Generated Codex agents install in `.codex/agents/`.
Codex installs root skills in `.agents/skills/`. See the official
[Codex plugin documentation](https://developers.openai.com/plugins/concepts/plugins).

OpenCode installs project files under `.opencode/`, including agents and
skills. See the official [OpenCode skills documentation](https://opencode.ai/docs/skills)
and [OpenCode agent documentation](https://opencode.ai/v2/docs/agents).

### Claude Code plugin

The Claude Code marketplace remains available for local development. Add the
repository as a marketplace, then install the plugin:

```text
/plugin marketplace add ~/projects/waterology-research
/plugin install waterology@waterology
```

Reload Claude Code after installation so `.claude-plugin/`, `agents/`,
`commands/`, and `skills/` register. Verify the marketplace with `/plugin`.

The canonical remote is a private Codeberg repository. Install from the Git URL
when working from the remote:

```text
/plugin marketplace add ssh://git@codeberg.org/waterology/waterology-research.git
/plugin install waterology@waterology
```

Troubleshooting: `.waterology-install.lock` may remain after a crash. Remove it
only after confirming that no Waterology install process is running.

## Experiment core

Waterology manages local experiments as committed Git variants. Initialize a
repository, then edit `waterology.toml` to set the fixed command, declared
outputs, artifact roots, environment files, metric extractors, and any regular
expressions that should redact sensitive log text before archive sealing:

```console
pixi run waterology init
git add waterology.toml .gitignore
git commit -m "Configure Waterology"
pixi run waterology experiment create "Test a longer calibration window" --owner cam
```

The create command returns an experiment identifier and worktree path. Make
the scientific change in that worktree and commit it before starting a run:

```console
pixi run waterology worktree open <experiment-id>
pixi run waterology run start <experiment-id>
pixi run waterology run status <run-id>
pixi run waterology archive verify <run-id>
```

Record a scientific conclusion after inspecting the archive. An `answer`
freezes the experiment at the run commit. Two consecutive `no_answer`
assessments require a decision before further repair:

```console
pixi run waterology run assess <run-id> answer "The evidence supports the hypothesis" \
  --author cam --evidence .waterology/runs/<run-id>/metrics.json
```

SQLite is a rebuildable index. Durable experiment records, run archives, and
assessment records remain readable without it:

```console
pixi run waterology repair-index
```

Project status and all experiment, worktree, run, archive, assessment, and
repair commands support structured JSON where automation needs it.

## TORC managed execution

Direct execution remains available without TORC. Managed execution uses the
TORC command line client and its JSON output. Install TORC 0.39.0 or newer
from the official [TORC repository](https://github.com/NatLabRockies/torc),
then define machine local profiles in `~/.config/waterology/config.toml`:

```toml
[profiles.local]
provider = "torc"
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"

[profiles.cluster]
provider = "torc"
mode = "slurm"
api_url = "http://localhost:8085/torc-service/v1"
torc_profile = "kestrel"
slurm_account = "your-project"
target_shell = "posix"
dashboard_url = "http://localhost:8085/dashboard"
```

Profiles may also use `mode = "remote"` with an `ssh_alias`. Keep passwords,
tokens, SSH settings, and TORC credentials outside this file. Set
`WATEROLOGY_CONFIG` to use another machine configuration path. Profiles default
to the host shell and may set `target_shell = "posix"` or `"windows"` when the
workers use a different operating system.

List profiles and start a managed run with:

```console
pixi run waterology compute profile list
pixi run waterology run start <experiment-id> --profile local
pixi run waterology run watch <run-id>
pixi run waterology run cancel <run-id>
```

The first remote or Slurm launch requires `--confirm-remote`. Waterology then
records the trusted profile name in machine configuration. Project
configuration cannot grant this trust.

Waterology generates and validates a TORC workflow from the committed command
and resource request. TORC handles local workers, remote workers, Slurm
generation, scheduling, and retries. Waterology records workflow and job IDs,
maps executor state, collects terminal logs and declared artifacts, then seals
the standard run archive. Time series resource databases are retained and
summarized in the archive metrics. An unreachable TORC service reports
`unknown`; it does not turn the run into a failure.

TORC submits from the experiment worktree and the generated job changes to
`TORC_WORKFLOW_SUBMISSION_DIR` before running the fixed command. Remote workers
therefore need the experiment worktree at the same shared path. Waterology does
not add a separate SSH file transfer layer.

Use `waterology compute inspect <profile>` for the configured TUI command, or
add `--dashboard` to print the dashboard URL. `waterology doctor` reports TORC
binary and profile availability while leaving direct execution usable. Run
`waterology doctor --torc-profile <profile>` to check the installed version and
API connection for one profile.

## Agent sessions and MCP

Waterology can launch Claude Code, Codex, or OpenCode in an experiment worktree. Each top level
session receives a task brief, role, compute profile, artifact location, project guidance, and MCP
instructions. The database prevents two active sessions from writing to the same worktree.

```console
pixi run waterology agent start <experiment-id> "Compare the calibration variants" \
  --runtime codex --role researcher
pixi run waterology agent list
pixi run waterology agent status <session-id>
pixi run waterology agent logs <session-id>
pixi run waterology agent resume <session-id> "Check the residual diagnostics"
pixi run waterology agent stop <session-id>
```

Claude Code, Codex, and OpenCode keep their native sessions and structured events. Waterology stores
the native identifier, process metadata, task brief, attempt logs, timestamps, and resulting commits
under `.waterology/sessions/<session-id>/`. Resume uses the runtime's native mechanism. A missing
process becomes `lost`, while its worktree and logs remain available. `waterology repair-index`
rebuilds session, note, evidence, and artifact reference rows from these durable records.

Install the optional MCP dependency when Waterology is installed outside the Pixi development
environment:

```console
pip install 'waterology-research[mcp]'
waterology-mcp
```

The server uses local stdio and offers bounded tools for experiments, runs, archives, metrics,
evidence, artifact references, and session notes. It does not expose shell execution, arbitrary file
reads, Git publication, or remote deletion. The plugin `.mcp.json` registers the server for Claude
Code and Codex plugins. `.codex/config.toml` and `opencode.json` contain project registrations for
Codex and OpenCode. A project scoped `waterology install` copies the matching registration when its
destination is absent or already owned by Waterology. Print a machine neutral registration snippet
or supported CLI command with:

```console
waterology mcp config claude
waterology mcp config codex
waterology mcp config opencode
```

The runtime command must be able to find `waterology-mcp` on `PATH`. The installer refuses to replace
project configuration it does not own. Merge the printed snippet manually when another configuration
already owns the destination.

## Constraints

| Check | What it enforces |
| --- | --- |
| `no-absolute-paths` | No paths specific to one machine in source |
| `deterministic-seed` | Stochastic scripts set a seed |
| `pixi-r-task-dollar` | R commands in `pixi.toml` tasks contain no `$` |

Run the checks with:

```bash
python3 constraints/check-all.py [PATH ...]
python3 constraints/check-all.py --only deterministic-seed src/
```

## Research workflows

The research bundle provides four agents (`researcher`, `writer`, `verifier`,
and `reviewer`), research skills, and Claude Code compatibility commands.

The `writing-style` skill supplies shared prose guidance and a scientific
writing layer. The `research-software-quality` skill scales testing, debugging,
verification, review, and worktree isolation to the task.
The `agent-delegation` skill defines portable task briefs, worktree ownership,
compute authorization, and return contracts. `source-summarization` keeps long
source text on disk and reads it in bounded windows.

| Command | Does |
| --- | --- |
| `/deepresearch` | Multi source investigation to a cited brief with provenance |
| `/lit` | Literature review or a publication corpus review |
| `/draft` | Findings to a paper style Quarto or LaTeX draft |
| `/review` | Internal critique with severity and a revision plan |
| `/audit` | Compare paper claims with a codebase |
| `/compare` | Build a grounded comparison matrix across sources |
| `/replicate` | Plan, then run a replication after an environment choice |
| `/recipe` | Rank implementable ML training recipes |
| `/summarize` | Summarize a long source and keep the result on disk |
| `/watch`, `/log`, `/autoresearch` | Monitor a field, log a session, or run an experiment loop |

## Status

The cross runtime foundation, research methods migration, experiment core, TORC managed execution,
and agent session and MCP slices are complete.
The research roadmap is in [ROADMAP.md](ROADMAP.md). Adapted sources are credited in
[ATTRIBUTION.md](ATTRIBUTION.md).

## License

MIT Copyright Cameron Bracken. Adapted material is credited in
[ATTRIBUTION.md](ATTRIBUTION.md).
