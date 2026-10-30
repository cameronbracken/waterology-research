---
name: waterology-r-code-style
description: >
  Apply R code style when writing, editing, or reviewing R scripts, functions,
  packages, or R chunks in Quarto and R Markdown documents.
---

<!-- Generated from skills/r-code-style/SKILL.md. Do not edit. -->

# R Code Style

Follow these defaults unless the user or an established project style specifies
otherwise. Read optional local guidance with
`waterology config context r-conventions`; use the
[local resolver](../waterology-project-conventions/references/local-preferences.md) if the
CLI is unavailable.

- Follow tidyverse style and use dplyr with the native pipe operator `|>`.
- Format with air. Default to line width 100 when establishing formatter
  configuration, and preserve an existing project's configuration. Run
  `air format` on edited source; exclude generated or tool-managed files.
- Use `=` for variable assignment.
- Put the variable assignment on the first line of a pipe chain and start the
  pipeline on the next line:

  ```r
  result =
    data |>
      filter(year >= 2000) |>
      summarise(mean_flow = mean(flow, na.rm = TRUE))
  ```

- Use `\(x)` for inline or single-line functions and `function(x)` for
  multiline functions.
- Keep file paths and settings in a dedicated section at the top of each script.

For research reproducibility, numerical discipline, and package conventions,
also follow [R conventions](../../rules/r-conventions.md).
