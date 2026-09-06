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

The installed `wgy` command is an alias for `waterology` and accepts the same
subcommands and options, for example `wgy workflow list`.

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
templates/          reproducibility record templates
hooks/              Claude Code plugin event hooks
.mcp.json           Claude Code and Codex plugin MCP registration
.codex/config.toml  Codex project MCP registration
opencode.json       OpenCode project MCP registration
ATTRIBUTION.md      citation ledger for adapted upstream material
```

## Documentation

The [documentation index](docs/README.md) links the maintained user guides:

- [Getting started](docs/getting-started.md)
- [Configuration](docs/configuration.md)
- [TORC execution](docs/torc.md)

Files under `docs/superpowers/` are design and implementation records rather than setup guides.

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

### Development plugin refresh

Reinstall Waterology in each runtime where it is already installed:

```console
pixi run reinstall-plugins --dry-run
pixi run reinstall-plugins
```

The script detects Codex and Claude installations, preserves Claude's scope and
persistent plugin data, and refreshes a stale local marketplace path. It uses a
temporary development version to avoid stale plugin caches, then restores the
tracked manifests. Use `--runtime codex`, `--runtime claude`, or `--runtime all`
for a first install. Start a new Codex thread or restart Claude Code after the
refresh.

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

Direct execution remains available without TORC. Managed execution requires TORC 0.40.0 or newer
and a running TORC server. Define machine profiles in `$HOME/.config/waterology/config.toml`:

```toml
[profiles.local]
provider = "torc"
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"

[profiles.cluster]
provider = "torc"
mode = "slurm"
api_url = "http://cluster-control:8085/torc-service/v1"
torc_profile = "kestrel"
slurm_account = "your-project"
target_shell = "posix"
dashboard_url = "http://localhost:8090"
```

Remote profiles use `mode = "remote"` with an `ssh_alias` and a server URL reachable from the
worker. Remote profiles cannot use a loopback API URL. An optional `access_group_id` lets
Waterology share new workflows with separately authenticated workers while TORC access control
remains enabled. Keep passwords, tokens, SSH settings, and TORC credentials outside this file. Set
`WATEROLOGY_CONFIG` to use another machine configuration path.

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

Use `waterology compute inspect <profile>` for the configured TUI command, or add `--dashboard` to
print the dashboard URL. Run `waterology doctor --torc-profile <profile>` to check the installed
version and API connection. The [TORC guide](docs/torc.md) covers installation, server services,
remote PATH requirements, network security, upgrades, and troubleshooting.

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

For a source checkout that must expose the bare command to Codex, install it as
an isolated editable tool:

```console
uv tool install --editable '.[mcp]'
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

## Research dashboard

Install the optional dashboard dependencies and start the local research view from an initialized
project:

```console
pip install 'waterology-research[dashboard]'
waterology dashboard
```

The server binds to `127.0.0.1:8127` and opens a browser by default. Use `--no-open` for a headless
session or SSH port forwarding. The Overview puts experiment lineage, active agents, recent
evidence, archives, and compute state together. Separate Experiments, Agents, Evidence, Archives,
and Compute views provide hypotheses, commits, worktree ownership, logs, metrics, artifacts,
assessments, and TORC links.

Pages are rendered on the server and remain useful without JavaScript. A small checked in script
updates summary counts and stores the light, dark, or system theme choice in the browser. Guarded
forms create experiments, start or resume agents, start or cancel runs, record assessments, and
export verified archives through the same service functions used by the CLI and MCP server.

For remote access, prefer SSH forwarding while the dashboard remains bound to loopback:

```console
ssh -L 8127:127.0.0.1:8127 research-host
waterology dashboard --no-open
```

A non-loopback bind requires both `--allow-remote` and an access token. Set the token through the
environment so it does not appear in shell history:

```console
WATEROLOGY_DASHBOARD_TOKEN='replace-with-a-long-random-value' \
  waterology dashboard --host 0.0.0.0 --allow-remote --no-open
```

The token protects every route and becomes an HTTP only same site cookie after browser bootstrap.
Open `http://<host>:8127/?token=<access-token>` once, then the server redirects to a clean URL.
The dashboard is a local project tool. It does not publish results, push Git state, or provide a
hosted collaboration service.

## Constraints

| Check | What it enforces |
| --- | --- |
| `no-absolute-paths` | No paths specific to one machine in source |
| `deterministic-seed` | Stochastic scripts set a seed |
| `pixi-r-task-dollar` | R commands in `pixi.toml` tasks contain no `$` |
| `mc-has-mcse` | Monte Carlo summaries report uncertainty for headline metrics |
| `conservation-tol` | Declared conservation evidence closes within tolerance |
| `overfull-boxes` | TeX overflow of at least 1 pt is reported by severity |
| `no-hardcoded-results` | Recognizable computed prose values are imported, not copied |

Run the checks with:

```bash
python3 constraints/check-all.py [PATH ...]
python3 constraints/check-all.py --only deterministic-seed src/
```

Run constraints after changing content they cover and target the changed paths.
Do not repeat a successful check for unchanged content. Use `.` when changing a
constraint, validating the full repository, or preparing a release.

## Research workflows

The research bundle provides seven agents: `researcher`, `writer`, `verifier`,
`reviewer`, `r-reviewer`, `sim-reviewer`, and `reproducibility-auditor`. It also
installs research skills and Claude Code compatibility commands.

The `writing-style` skill supplies shared prose guidance and a scientific
writing layer. The `research-software-quality` skill scales testing, debugging,
verification, review, and worktree isolation to the task.
The `agent-delegation` skill defines portable task briefs, worktree ownership,
compute authorization, and return contracts. `source-summarization` keeps long
source text on disk and reads it in bounded windows.

The `audit-reproducibility` skill compares numeric manuscript claims with R,
Python, Fortran, and text outputs. It records provenance and tolerance results
in `quality_reports/passports/`. The Claude plugin hook marks affected claims
`STALE` after a tracked source or output edit. Codex and OpenCode use the same
skill and passport, but do not install the Claude specific hook.

The completed research feature set adds Monte Carlo design and review,
environment capture, bibliography validation, pipeline manifests with Fortran
support, MyST to Quarto conversion, and verified LaTeX builds.

| Command | Does |
| --- | --- |
| `/deepresearch` | Multi source investigation to a cited brief with provenance |
| `/lit` | Literature review or a publication corpus review |
| `/draft` | Findings to a paper style Quarto or LaTeX draft |
| `/review` | Internal critique with severity and a revision plan |
| `/audit` | Compare paper claims with a codebase |
| `/audit-reproducibility` | Check numeric claims against produced outputs |
| `/simulation-study` | Design and review a Monte Carlo experiment |
| `/capture-environment` | Record R, Python, and Fortran environments |
| `/bib-validate` | Check citation keys and optional DOI metadata |
| `/pipeline-manifest` | Trace scripts, outputs, and document artifacts |
| `/myst-to-quarto` | Convert common MyST constructs to Quarto |
| `/compile-latex` | Build and verify LaTeX with latexmk and XeLaTeX |
| `/compare` | Build a grounded comparison matrix across sources |
| `/replicate` | Plan, then run a replication after an environment choice |
| `/recipe` | Rank implementable ML training recipes |
| `/summarize` | Summarize a long source and keep the result on disk |
| `/watch`, `/log`, `/autoresearch` | Monitor a field, log a session, or run an experiment loop |

## Status

The platform and research feature roadmaps are complete. The platform includes cross runtime
packaging, research methods, experiment state, TORC execution, agent sessions and MCP, and the
local research dashboard. The research roadmap is in [ROADMAP.md](ROADMAP.md). Adapted sources are credited in
[ATTRIBUTION.md](ATTRIBUTION.md).

## License

MIT Copyright Cameron Bracken. Adapted material is credited in
[ATTRIBUTION.md](ATTRIBUTION.md).

Named workflow registration and final-deliverable verification are described in
[Execute and reproduce a project](docs/workflow-execution.md).
