---
name: replication
description: >
  Plan a replication of a paper, claim, or benchmark, and execute only after an
  explicit environment choice. Use when the user asks to replicate results,
  reproduce an experiment, verify a claim empirically, or build a replication
  package.
---

# Replication

Run the `/replicate` workflow. It extracts implementation details, enumerates
the paper's main empirical claims into a ledger (paper result, observed result,
assessment, downscaling, compute cost), does a recipe pass for training or
dataset-heavy targets, plans what code, data, metrics, and environment are
needed, then asks where to run before executing. Assessments come from a fixed
vocabulary (`aligned`, `partially aligned`, `inconclusive under this setup`,
`not attempted`); divergent results are quantified, never characterized as the
claim being wrong.

Execution environments are matched to this stack: Local, a new git branch, a
Pixi environment (`rv`/`renv` for R), or remote SSH/Slurm for GPU or long jobs.
Nothing is installed or run until the environment is confirmed. See the
`setup-environment` skill for scaffolding an isolated environment.

Agents used: `researcher`.
Output: replication plan, scripts, raw outputs, and a `CHANGELOG.md` trail.

---
*Adapted from Feynman (companion-inc/feynman, MIT); claim ledger from
openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See
`${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
