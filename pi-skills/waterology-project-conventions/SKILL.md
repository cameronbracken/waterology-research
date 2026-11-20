---
name: waterology-project-conventions
description: >
  Apply research coding, file format, and tool defaults when writing scripts,
  adding features, or editing Python, R, Julia, Fortran, Quarto, or LaTeX.
  Defines light and strict reproducibility modes and repository constraints.
---

<!-- Generated from skills/project-conventions/SKILL.md. Do not edit. -->

# Waterology Project Conventions

Entry point for shared coding, format, tool, and reproducibility defaults across research, simulation, and manuscript repositories. Explicit user instructions and a project's established style take precedence.

When selecting languages, package managers, or tools for new work, read [tool choices](references/tool-choices.md). For the boundary between shared defaults and private settings, see [local preferences](references/local-preferences.md).

## Reproducibility mode

Default to **`light`** mode unless the user requests **`strict`** mode (used for publication submissions, formal DOE deliverables, and replication packages).

- **`light` (default):** Work is reproducible when code is committed, dependencies are pinned in a lockfile (`pixi.lock`, `uv.lock`, `rv.lock`), stochastic code sets a seed, paths are project-relative, and a README or task documents how to run it. Work on a descriptive branch in the current checkout (use a worktree only when concurrent writers or unrelated dirty changes require isolation). Run constraints and independent reviews on request or before a requested commit.
- **`strict`:** Isolate code/skill changes in a worktree, validate citations (`waterology-bib-validate`), run applicable deterministic checks (`constraints/check-all.py`), audit numeric manuscript claims (`waterology-audit-reproducibility`), capture computational requirements (`waterology-setup-environment`), and run an independent `reviewer` pass when warranted.

## File formats

| Content | Format |
| --- | --- |
| Settings people edit by hand (`pixi.toml`, `.zotero.toml`) | TOML |
| Structured records, ledgers, and configurations read by people and tools | YAML |
| Notes, skills, code documentation, and standalone report bundles (`reports/<slug>-<YYYY-MM-DD>/`) | Markdown, with TikZ for diagrams |
| Polished PDF reports, manuscripts, and white papers | LaTeX, with TikZ for diagrams |
| Reports requiring interactive graphics | Quarto HTML (`embed-resources: true`) |
| Machine-to-machine interchange or single-source plot metric payloads | JSON or JSONL |

Use JSON only when a tool, protocol, or plotting pipeline specifies it. Prefer YAML when a person will read structured records directly.

## Matching conventions and skills

Before editing code or documents, read the matching rule under `rules/` (relative to the Waterology installation root):

| File type | Rule / Skill |
| --- | --- |
| `.R`, `.r`, `.Rmd` | `rules/r-conventions.md` and [r-code-style](../waterology-r-code-style/SKILL.md) |
| `.py` | `rules/python-conventions.md` |
| `.f90`, `.F90`, `.f95`, `.f` | `rules/fortran-conventions.md` |
| `.qmd`, `.tex` | `rules/quarto-conventions.md` (`scripts/myst_to_quarto.py` converts MyST Markdown to `.qmd`) |
| `.stan` | `rules/stan-conventions.md` |
| `Makevars*`, `Makefile`, `meson.build` | `rules/native-build-conventions.md` |

Load artifact skills only for the deliverable requested: [figures](../waterology-figures/SKILL.md) for data plots, [diagrams](../waterology-diagrams/SKILL.md) for conceptual schematics, [reports](../waterology-reports/SKILL.md) for analysis/benchmark reports, [compile-latex](../waterology-compile-latex/SKILL.md) for LaTeX builds, and [research-software-quality](../waterology-research-software-quality/SKILL.md) for testing, debugging, and worktree decisions.

## Deterministic constraints

Run applicable checks on changed files before requested commits or in `strict` mode:

```bash
python3 <waterology-root>/constraints/check-all.py path/to/changed/files
```

Included checks: `no-absolute-paths`, `deterministic-seed`, `pixi-r-task-dollar`, `plotly-text-overlap`, `mc-has-mcse`, `conservation-tol`, `overfull-boxes`, and `no-hardcoded-results`. Fix violations rather than suppressing them (`# waterology: allow-abs-path` and `# waterology: allow-unseeded` are reserved for genuine exceptions).

## Repository hygiene

- Exclude OS and build debris (`.DS_Store`, `._*`, `.pixi/`, `.waterology/`, LaTeX build files) in `.gitignore`.
- Never commit `.env*`, `.Renviron`, credentials, or tokens.
