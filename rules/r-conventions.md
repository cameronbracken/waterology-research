---
name: r-conventions
description: R style and numerical-discipline conventions for waterology research code
paths:
  - "**/*.R"
  - "**/*.r"
  - "**/*.Rmd"
---

# R conventions

Follow these defaults unless the surrounding file clearly uses another established project style.

## Style

- Use [r-code-style](../skills/r-code-style/SKILL.md) for `=` assignment, native `|>` pipes, `air` formatting, function syntax, and script layout.
- Use `# %%` section markers for editor cell navigation (VSCode / Positron / Zed).

## Reproducibility

- Put one `set.seed()` near the top of any script that draws random numbers (`deterministic-seed` constraint). For parallel work use `RNGkind("L'Ecuyer-CMRG")` and `furrr_options(seed = TRUE)`.
- Use `library()` (loud failure), not `require()` (silent).
- Use project-relative paths only (`here::here()` or `file.path()`, enforced by `no-absolute-paths`). Never write to `data/raw/`.
- Route tables and figures to the project's figures/results directory rather than next to scripts, and save underlying data objects (`saveRDS` or JSON/CSV) so figures regenerate cleanly.

## Numerical discipline

- Never compare doubles with `==`; use `abs(x - y) < tol` or `all.equal()`.
- Clamp probabilities to an open interval before `qnorm()`/`q*()`: `eps = 1e-12; p = pmin(1 - eps, pmax(eps, p))`.
- Use integer literals (`1L`, `0L`) for counts and indices.
- Pre-allocate vectors rather than growing with `c()` or `append()` inside loops.
- Always pass `na.rm =` explicitly to `mean`, `sum`, `var`, and `sd`.
- Write `TRUE`/`FALSE`, never `T`/`F`.

## Visualization and packages

- When creating or revising a data figure, load [figures](../skills/figures/SKILL.md). Set explicit `ggsave` dimensions and `bg = "transparent"` only when slide layouts require transparency.
- Treat `man/` and `NAMESPACE` in R packages as generated via `devtools::document()`. Ship CRAN-clean (`R CMD check --as-cran`: 0 errors, 0 warnings). Use Posit Package Manager (`https://packagemanager.posit.co/cran/latest`) for binary packages where supported.
