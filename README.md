# waterology

Waterology is a research workflow package for
[Claude Code](https://claude.com/claude-code),
[Codex](https://openai.com/codex/), and
[OpenCode](https://opencode.ai/). It supports research software in R, Python,
Fortran, Quarto, and LaTeX.

The package keeps research skills and agent definitions in the repository, then
installs runtime adapters for each supported tool. Packaging and agents support
all three runtimes. Command-backed skill bodies are still Claude-oriented until
Slice 2, when they become runtime neutral.

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
/plugin marketplace add ~/projects/waterology-cc
/plugin install waterology@waterology
```

Reload Claude Code after installation so `.claude-plugin/`, `agents/`,
`commands/`, and `skills/` register. Verify the marketplace with `/plugin`.

The canonical remote is a private Codeberg repository. Install from the Git URL
when working from the remote:

```text
/plugin marketplace add ssh://git@codeberg.org/waterology/waterology-cc.git
/plugin install waterology@waterology
```

Troubleshooting: `.waterology-install.lock` may remain after a crash. Remove it
only after confirming that no Waterology install process is running.

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

The cross runtime foundation is complete.
Later skill migration remains planned for Slice 2. The research roadmap is in
[ROADMAP.md](ROADMAP.md). Adapted sources are credited in
[ATTRIBUTION.md](ATTRIBUTION.md).

## License

MIT Copyright Cameron Bracken. Adapted material is credited in
[ATTRIBUTION.md](ATTRIBUTION.md).
