# waterology

A lean [Claude Code](https://claude.com/claude-code) plugin for
computational-science and research-software work — tuned for R, Python, Fortran,
Quarto, and LaTeX, with a bias toward **reproducibility**.

It is deliberately small. Where the big agent bundles try to cover everything,
`waterology` covers one person's research stack well: hydrology, energy systems,
and statistical extremes. Pair it with [`superpowers`](https://github.com/obra/superpowers)
for generic engineering discipline — this plugin adds the research-specific
conventions and checks superpowers can't know about.

## What's here

```
.claude-plugin/   plugin + marketplace manifests
skills/           project-conventions (entry point), setup-environment,
                  publish-blog-post, and the research skills (deep-research,
                  literature-review, paper-writing, figure-style, ...)
agents/           research subagents: researcher, writer, verifier, reviewer
commands/         research slash workflows: /deepresearch, /lit, /draft,
                  /review, /audit, /compare, /replicate, /recipe, /summarize, ...
rules/            path-scoped conventions: R, Python, Fortran, Quarto/LaTeX,
                  Stan, native builds (Makevars/configure), experiment trees
constraints/      paired <name>.md + <name>.py checks, run by check-all.py
ATTRIBUTION.md    citation ledger for adapted upstream material
```

The design follows two ideas borrowed from Edwin Hu's *Workflow Philosophy*:

- **Conventions vs constraints.** A *convention* needs reading and judgment
  (style, methodology) and lives in `rules/`. A *constraint* is a deterministic
  pass/fail check and lives in `constraints/` as a paired `.md`/`.py`. Litmus
  test: *can you write a script that returns pass/fail?*
- **Auto-discovery, no wiring.** `constraints/check-all.py` globs every
  `constraints/*.py` and runs it. Adding a check is just adding the file.

## Constraints (today)

| Check | What it enforces |
|-------|------------------|
| `no-absolute-paths` | No machine-specific paths baked into source |
| `deterministic-seed` | Stochastic scripts set a seed |
| `pixi-r-task-dollar` | R commands in `pixi.toml` tasks contain no `$` |

Run them:

```bash
python3 constraints/check-all.py [PATH ...]
python3 constraints/check-all.py --only deterministic-seed src/
```

## Research workflows

A source-grounded research bundle, adapted from Feynman and retargeted to this
stack. Four subagents (`researcher`, `writer`, `verifier`, `reviewer`) back a
set of slash commands and auto-activating skills:

| Command | Does |
|---------|------|
| `/deepresearch` | Multi-source investigation -> cited brief with provenance |
| `/lit` | Literature review, or a lab/author publication-corpus review |
| `/draft` | Findings -> paper-style Quarto/LaTeX draft |
| `/review` | Tough internal critique with severity and a revision plan |
| `/audit` | A paper's claims vs. its actual codebase |
| `/compare` | Grounded comparison matrix across sources |
| `/replicate` | Plan (and, once an environment is chosen, run) a replication |
| `/recipe` | Ranked, implementable ML training recipes |
| `/summarize` | Windowed summary of a long source, kept on disk |
| `/watch`, `/log`, `/autoresearch` | Monitor a field, log a session, run an experiment loop |

Every workflow refuses to invent sources, verifies URLs, and marks unverified
claims honestly. Paper search uses the Consensus MCP plus keyless OpenAlex and
arXiv when connected; figures follow the `figure-style` skill (ggplot2, light
for print, colorblind-safe).

## Install

Once this repo is pushed to a remote:

```text
/plugin marketplace add cameronbracken/waterology-cc
/plugin install waterology@waterology
```

### Local development (no remote needed)

The repo is its own marketplace — `.claude-plugin/marketplace.json` names the
marketplace and the plugin `waterology`, with the source at the repo root. Add
the directory and install from it:

```text
/plugin marketplace add ~/projects/waterology-cc
/plugin install waterology@waterology
```

Then reload Claude Code so `agents/`, `commands/`, and `skills/` register.
`waterology@waterology` is `<plugin>@<marketplace>` — both are `waterology`.

Notes:

- The marketplace points at this working copy, so edits show up on the next
  reload — no commit or push required while iterating.
- Verify it loaded: `/plugin` lists it as enabled, and `/help` shows the
  commands namespaced as `/waterology:deepresearch`, `/waterology:lit`, etc.
  Skills auto-activate by description; the four agents become available to the
  `Task` tool and the agent picker.
- Paper search is optional — the research workflows use the Consensus and Exa
  MCP servers when connected and fall back to keyless OpenAlex/arXiv otherwise.

## Status

Early, but growing. The foundation (manifests, conventions, constraint runner)
and the research bundle (agents, commands, skills) are in place. Planned next: a
reproducibility **passport** (claim → script provenance), an `r-reviewer` /
`sim-reviewer` for Monte Carlo work, bibliography/DOI validation, and
Fortran-aware pipeline tooling — see [ROADMAP.md](ROADMAP.md) for the full plan
and [ATTRIBUTION.md](ATTRIBUTION.md) for the upstream projects these adapt.

## License

MIT © Cameron Bracken. Adapts MIT-licensed material from
[`edwinhu/workflows`](https://github.com/edwinhu/workflows),
[`pedrohcgs/claude-code-my-workflow`](https://github.com/pedrohcgs/claude-code-my-workflow),
[`flonat/claude-research`](https://github.com/flonat/claude-research), and
[`companion-inc/feynman`](https://github.com/companion-inc/feynman) — full credit
in [ATTRIBUTION.md](ATTRIBUTION.md).
