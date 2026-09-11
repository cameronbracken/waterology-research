---
name: project-conventions
description: >
  Conventions and selective reproducibility checks for research
  code (hydrology / energy systems / extremes). Use when writing or editing R,
  Python, Fortran, Quarto, or LaTeX in a research project. Run constraints only
  for applicable content changed since its last successful check.
---

# waterology — project conventions

This skill is the entry point for the `waterology` plugin. It loads the right
**conventions** (judgment guidance) for the file being edited. It also runs
**constraints** (deterministic pass/fail checks) when the current task creates
or changes content they cover. The split between conventions and constraints
follows Edwin Hu's methodology (*edwinhu/workflows*, MIT per README).

## When to use

Editing or reviewing any of: `.R` `.r` `.Rmd`, `.py`, `.f90` `.F90` `.f`,
`.qmd`, `.tex` — in a research/analysis/simulation/paper context.

## Preferences and privacy

When the project does not settle a choice about tools, collaboration, privacy,
source credit, or visual design, read
[local preferences](references/local-preferences.md). Run
`waterology config context project-conventions` to include the current user's
identity and optional local guidance. No personal defaults ship with the package.

## How it works

### 1. Load the matching convention

Before editing, read the rule file under `${CLAUDE_PLUGIN_ROOT}/rules/` that
matches the file type, and follow it (it defers to a file's existing local
style when they conflict):

| Editing… | Read |
|----------|------|
| `.R` `.r` `.Rmd` | `rules/r-conventions.md` |
| `.py` | `rules/python-conventions.md` |
| `.f90` `.F90` `.f95` `.f` | `rules/fortran-conventions.md` |
| `.qmd` `.tex` | `rules/quarto-conventions.md` |
| `.stan` (and cmdstanr drivers) | `rules/stan-conventions.md` |
| `Makevars*` `Makefile` `configure` `meson.build` | `rules/native-build-conventions.md` |

Highlights you should not need to re-derive: R follows the project formatter and assignment style;
Python matches the project environment; Fortran is `implicit none` + explicit kinds + `intent`; documents use
dual-theme Quarto with `ggplot` -> `ggplotly` graphics, light for print and never 
hand-type computed numbers.

### 2. Run constraints for unvalidated changes

The constraints are scriptable, deterministic checks. Run them after the final
edit only when the current task creates or changes an applicable source,
configuration, result, or rendered artifact. Target the changed paths:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/constraints/check-all.py path/to/changed/files
```

Do not run constraints for read only work, explanations, plans, or changes to
unrelated file types. Do not repeat a successful run when the checked content
has not changed, including on a later prompt. A passing run in the current task,
a durable validation record for the same contents, or passing CI for the same
commit establishes that state. If validation cannot be established for a
changed applicable file, run the focused check once.

Use a whole project target only when the task changes a constraint, requests
full repository validation, prepares a release, or otherwise needs repository
wide evidence. Other test and repository instructions may still require their
own checks; they do not make the Waterology constraint suite unconditional.

Current checks:

- **`no-absolute-paths`** — no machine-specific paths (`/Users/…`, `~/…`,
  `C:\…`, cloud-storage roots) baked into source.
- **`deterministic-seed`** — any script that draws random numbers sets a seed.
- **`pixi-r-task-dollar`** — R commands in `pixi.toml` tasks contain no `$`
  (deno_task_shell expands it even inside single quotes).
- **`plotly-text-overlap`** — rendered Plotly widgets separate titles,
  legends, facets, axes, and tick labels instead of relying on collision-prone
  default layout.

A check exits non-zero on a real violation and prints the offending lines. Fix
the violation rather than suppressing it; the documented escape-hatch comments
(`# waterology: allow-abs-path`, `# waterology: allow-unseeded`) exist for the
genuine exceptions only.

### 3. Apply repository hygiene

- Exclude operating system debris such as `.DS_Store`, `._*`, `.Trashes`,
  `.Spotlight-V100`, `.fseventsd`, and `Thumbs.db`.
- Do not commit editor state such as `.vscode/` or `.positron/` without the user's
  permission.
- Never commit secret-bearing environment files such as `.env*`, `.Renviron`,
  credentials, or access tokens. Inspect files before staging when their names
  or contents may be sensitive.
- Ensure the project `.gitignore` covers these local artifacts. Do not ignore
  all dotfiles: project assets such as `.gitignore`, `.mcp.json`, and runtime
  configuration directories may be intentional source files.

### 4. Add a new check (no wiring)

Drop a paired `constraints/<name>.md` (the rule) + `constraints/<name>.py` (a
standalone script: target paths as argv, print findings, exit 0 pass / 1 fail).
`check-all.py` discovers it automatically — adding the file is the whole step.

Litmus test for where something belongs: **can you write a script that returns
pass/fail?** Yes → a constraint (a paired `.md`/`.py`). No, it needs reading and
judgment → a convention (a `rules/*.md` entry).

## Sibling skills

- **`setup-environment`** — scaffold or repair a project environment (pixi,
  rv/renv, lockfile hygiene, relocation pitfalls).
- **`publish-blog-post`** — the waterology-blog post workflow (webp media,
  R2 uploads, publish checklist).
- **research bundle** — source-grounded research agents (`researcher`, `writer`,
  `verifier`, `reviewer`), skills (`deep-research`, `literature-review`,
  `paper-writing`, `figure-style`, ...), and slash workflows (`/deepresearch`,
  `/lit`, `/draft`, `/review`, `/summarize`, ...).

## Software quality

Use `research-software-quality` for proportional testing, debugging,
verification, review, persistence, and worktree isolation. Skill and agent
instruction edits count as behavior changes even when the files are Markdown.
