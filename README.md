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
skills/           project-conventions  (the entry point)
rules/            path-scoped conventions: R, Python, Fortran, Quarto/LaTeX
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

Run them:

```bash
python3 constraints/check-all.py [PATH ...]
python3 constraints/check-all.py --only deterministic-seed src/
```

## Install

```text
/plugin marketplace add cameronbracken/waterology-cc
/plugin install waterology@waterology
```

(Local development: `/plugin marketplace add ~/projects/waterology-cc`.)

## Status

Early. The foundation (manifests, conventions, constraint runner) is in place.
Planned next: a reproducibility **passport** (claim → script provenance), an
`r-reviewer` / `sim-reviewer` for Monte Carlo work, bibliography/DOI validation,
and Fortran-aware pipeline tooling — see [ROADMAP.md](ROADMAP.md) for the full
plan and [ATTRIBUTION.md](ATTRIBUTION.md) for the upstream projects these adapt.

## License

MIT © Cameron Bracken. Adapts MIT-licensed material from
[`edwinhu/workflows`](https://github.com/edwinhu/workflows),
[`pedrohcgs/claude-code-my-workflow`](https://github.com/pedrohcgs/claude-code-my-workflow),
and [`flonat/claude-research`](https://github.com/flonat/claude-research) — full
credit in [ATTRIBUTION.md](ATTRIBUTION.md).
