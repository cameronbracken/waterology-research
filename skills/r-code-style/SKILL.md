---
name: r-code-style
description: >
  Apply R code style when writing, editing, or reviewing R scripts, functions,
  packages, or R chunks in Quarto and R Markdown documents.
---

# R Code Style

Follow these defaults unless the user or an established project style specifies otherwise:

- Follow tidyverse style using `dplyr` and the native pipe `|>`.
- Format with `air` (line width 100 by default when creating new config). Run `air format` on edited `.R` files while excluding tool-managed files (`rv` activate scripts).
- Use `=` for assignment.
- Put variable assignment on its own line and start multi-step pipe chains on the next line:

  ```r
  result =
    data |>
      filter(year >= 2000) |>
      summarise(mean_flow = mean(flow, na.rm = TRUE))
  ```

- Use `\(x)` for inline anonymous functions and `function(x)` for multiline functions.
- Group file paths, constants, and seeds in a dedicated header section at the top of each script.
- Also apply `rules/r-conventions.md` for numerical discipline, RNG seeding, and package checks.
