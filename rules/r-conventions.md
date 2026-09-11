---
name: r-conventions
description: R style and numerical-discipline conventions for waterology research code
paths:
  - "**/*.R"
  - "**/*.r"
  - "**/*.Rmd"
---

# R conventions

Conventions (ex-ante judgment guidance), not mechanically-checked constraints.
When editing R, follow these unless the surrounding file clearly does otherwise
— match an existing file's local style first.

Read the optional local context using this rule name. If the CLI is unavailable,
use the [local resolver](../skills/project-conventions/references/local-preferences.md).

## Style

Run `waterology config context r-conventions` for optional local style.

- Use the project formatter and its configuration (for example, **air**).
- Match the project assignment convention. If none exists, choose a consistent
  convention; the example below uses `<-`.
- Use the native pipe `|>`, never magrittr `%>%`.
- Place the variable assignment on the first line of a pipe chain, with the
  first operation on the next line:
  ```r
  result <-
    data |>
      filter(year >= 2000) |>
      summarise(mean_flow = mean(flow, na.rm = TRUE))
  ```
- Use `function(x)` for multiline functions, use `\(x)` lambda syntax for inline functions.
- Use `# %%` section markers for editor cell navigation (VSCode / Positron).
- Put file paths and settings in a dedicated section at the top of the script.

## Reproducibility

- One `set.seed()` near the top of any script that draws random numbers
  (enforced by the `deterministic-seed` constraint). For parallel work use
  `RNGkind("L'Ecuyer-CMRG")` and `furrr_options(seed = TRUE)`.
- Use `library()` (loud failure), not `require()` (silent).
- Project-relative paths only — `here::here()` / `file.path()`, never absolute
  (enforced by the `no-absolute-paths` constraint). Never write to `data/raw/`.
- Routed outputs: tables and figures go to a paper/figures area, not next to
  the script. Save the underlying object (`saveRDS`) alongside any figure so it
  can be regenerated.

## Numerical discipline

- Never compare doubles with `==`; use `abs(x - y) < tol` or `all.equal()`.
- Clamp probabilities to an open interval before `qnorm()`/`q*()`:
  `eps = 1e-12; p = pmin(1 - eps, pmax(eps, p))` — exact 0/1 give ±Inf.
- Use integer literals (`1L`, `0L`) for counts and indices.
- Pre-allocate; never grow a vector with `c()`/`append()` inside a loop.
- Always pass `na.rm =` explicitly to `mean`/`sum`/`var`/`sd`.
- Avoid `T`/`F` (re-assignable); write `TRUE`/`FALSE`.

## Visualization

- Follow the project or local figure guidance. Choose accessible colors and
  backgrounds suited to the intended medium.
- ggplot for static, plotly for interactive, base R + TikZ/`pgfSweave` for
  publication graphics. Explicit `ggsave` dimensions; `bg = "transparent"`
  for figures dropped into Beamer.

## Packages

- `package.skeleton` for new packages. Treat `man/` and `NAMESPACE`
  as generated — `devtools::document()`, never hand-edit. Ship CRAN-clean
  (`R CMD check --as-cran`: 0 errors, 0 warnings, every note justified).
- Use ppm to install binary packages: https://packagemanager.posit.co/cran/latest
