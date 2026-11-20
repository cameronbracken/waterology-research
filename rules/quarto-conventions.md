---
name: quarto-conventions
description: Quarto and LaTeX authoring conventions for waterology documents and reports
paths:
  - "**/*.qmd"
  - "**/*.tex"
---

# Quarto and LaTeX conventions

Conventions for Quarto documents/blogs, journal manuscripts, and technical PDF reports.

## Quarto

- Use the project environment or `quarto` on `PATH`.
- Standalone HTML uses `embed-resources: true` and a dual theme toggle (`darkly` default with `flatly` light switch):
  ```yaml
  format:
    html:
      embed-resources: true
      respect-user-color-scheme: false
      theme:
        dark: darkly
        light: flatly
  ```
- **Light theme for print** (PDF, journal, slides); Darkly/Flatly for interactive HTML.
- Generate heavy analysis and figures in R/Python scripts and import saved outputs rather than embedding slow inline computation.
- Use TikZ for flowcharts and conceptual diagrams unless Mermaid is explicitly requested ([diagrams](../skills/diagrams/SKILL.md)), [figures](../skills/figures/SKILL.md) for static or interactive plots, and [reports](../skills/reports/SKILL.md) when authoring a report deliverable.
- To convert MyST Markdown into Quarto syntax, run `python3 <project-conventions-dir>/scripts/myst_to_quarto.py input.md output.qmd`, then verify citations, cross-references, and rendered output.

## No hand-typed computed numbers

Computed numbers in prose or tables must be imported (`\input{}`, inline code chunks, or generated `.tex`/JSON fragments) rather than copy-pasted from console output (`no-hardcoded-results` constraint).

## LaTeX hygiene

- Build through **`latexmk`** governed by `.latexmkrc` ([compile-latex](../skills/compile-latex/SKILL.md)), never bare single-pass `pdflatex`/`xelatex`.
- Never write BibTeX entries from memory; validate keys and DOIs with [bib-validate](../skills/bib-validate/SKILL.md).
- Check overfull boxes (`> 10pt` fix, `1-10pt` minor, `< 1pt` ignore) using `compile-latex/scripts/overfull_boxes.py` or `constraints/overfull-boxes.py`.
- Keep LaTeX sources (`paper/`) separate from scripts/data and exclude `.aux`, `.log`, `.synctex.gz`, and build artifacts from Git.
