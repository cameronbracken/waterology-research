---
name: no-hardcoded-results
description: Import computed values into Quarto and LaTeX rather than typing them
paths:
  - "**/*.tex"
  - "**/*.qmd"
---

# Import computed results

<!-- Adapted from flonat/claude-research, rules/no-hardcoded-results.md at
commit e7007d0b1e465ef96de7338599ca04079e83a972 (MIT, Copyright 2026 Florian
Burnat). Quarto support is an original Waterology addition. See
ATTRIBUTION.md. -->

Computed coefficients, uncertainty, p-values, counts, percentages, and table
cells must come from the analysis outputs. Do not copy them into prose or a
handwritten table.

- In LaTeX, use a generated `\input{}` file or generated command.
- In Quarto, use an inline computation or import a committed evidence table.
- Generate figures from source data and retain the script that created them.
- Keep illustrative values, dates, identifiers, and other source metadata distinct from computed results.
- If a result cannot yet be generated, use an explicit placeholder that fails review instead of a plausible number.

Run `constraints/no-hardcoded-results.py` as a narrow mechanical check. Review
still needs to trace values that the scanner cannot classify.
