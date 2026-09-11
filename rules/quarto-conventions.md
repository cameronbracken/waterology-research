---
name: quarto-conventions
description: Quarto and LaTeX authoring conventions for waterology documents and reports
paths:
  - "**/*.qmd"
  - "**/*.tex"
---

# Quarto & LaTeX conventions

Conventions for research writing output: Quarto documents/blogs, journal
articles, and DOE reports.

Read the optional local context using this rule name. If the CLI is unavailable,
use the [local resolver](../skills/project-conventions/references/local-preferences.md).

## Quarto

Run `waterology config context quarto-conventions` for optional local guidance.
The themes below are examples; project and local preferences take precedence.

- Use the project environment or discover `quarto` on PATH.
- Standalone HTML uses `embed-resources: true` and a dual theme for a
  light/dark toggle:
  ```yaml
  format:
    html:
      embed-resources: true
      respect-user-color-scheme: false
      theme:
        dark: darkly
        light: flatly
  ```
  The first entry makes Darkly the default while the Quarto switch retains
  Flatly. Design figure palettes in light mode, then derive dark data colors
  with Chameleon's luminance, color consistency, and adjacent color objectives.
  Verify both palettes after rendering.
  - Compile to html: `quarto render document.qmd --to html -M embed-resources=true`
- **Light theme for anything print-bound** (PDF, journal, slides). Darkly is the
  default for interactive HTML reports, with Flatly available from the theme
  switch.
- Figures: generate them from R/Python scripts and reference the saved file,
  rather than embedding heavy inline computation — keeps the document fast and
  the figure regenerable. Use the project or local palette.
- Mermaid for flow charts, plotly for interactive plots, bokeh for richer
  interactives, PNG or vector for static.

## No hand-typed computed numbers

If a number was computed, it must be **imported**, not typed. A table or a
statistic in the prose should come from `\input{}` / an inline code chunk /
a generated `.tex` fragment — never copy-pasted from console output, which
silently goes stale when the analysis changes. Hand-typed results are the
single most common source of paper↔code drift.

## LaTeX hygiene

- Build through **`latexmk`** governed by a project `.latexmkrc`; let the rc
  file pick the engine. Don't call bare `pdflatex`/`xelatex` (Beamer decks here
  are often XeLaTeX, and a bare call ignores the rc file).
- Never write BibTeX entries from memory — verify a reference exists before
  citing it. A hallucinated citation is worse than a missing one.
- Overfull/underfull boxes are **not** tagged `Warning`, so `grep Warning`
  misses them. Detect with:
  ```bash
  grep -cE 'Overfull \\[hv]box \([0-9.]+pt too (wide|high)\)' out/file.log
  ```
  Severity: <1pt ignore, 1–10pt minor, >10pt fix. The only safe blanket fix is
  adding `microtype`.
- Keep LaTeX source separate from code/data — `paper/` holds `.tex`/`.bib`
  only; `.R`/`.py`/`.csv`/`.rds` live elsewhere.
- Don't commit LaTeX build artifacts (`.aux`, `.log`, `.synctex.gz`, generated
  `.pdf`) — including archive directories.
