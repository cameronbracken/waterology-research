---
name: waterology-figures
description: >
  Create, style, compose, or add interaction to data visualizations: scientific
  plots, charts, maps, multi-panel publication figures, and interactive Plotly
  or Bokeh graphics. Distinct from conceptual diagrams (use diagrams).
---

<!-- Generated from skills/figures/SKILL.md. Do not edit. -->

# Figures (Static, Multi-Panel, and Interactive Data Graphics)

Use [writing-style](../waterology-writing-style/SKILL.md) for titles, labels, and captions, and read [visual-design.md](references/visual-design.md) for the earth-tone palette, theme rules, and export defaults. Conceptual flowcharts and architecture schematics belong in [diagrams](../waterology-diagrams/SKILL.md).

## 1. Scientific plot checklist

1. **Match chart type to claim and data structure:** densities, ECDFs, or quantiles for distributions rather than bare bar charts of means; lines/ribbons for time series; sorted horizontal or vertical bars when categories have no intrinsic order.
2. **Label axes with explicit units**, state transformations (log flow, standardized anomaly), and show uncertainty or ensemble spread (ribbons, intervals, or underlying replicates).
3. **Preserve reproducibility:** never invent observations or silently drop missing/non-converged points. Save both the plotting script and the machine-readable data needed to regenerate the figure, and never hand-type computed numbers into annotations or captions.
4. **Stack defaults** (preserve an existing project's stack first):
   - **R:** `ggplot2` with a clean minimal theme (`resources/earth_tone_plot_template.R` in [reports](../waterology-reports/SKILL.md) or `theme_minimal()`), formatted with `air` ([r-code-style](../waterology-r-code-style/SKILL.md)).
   - **Python:** `matplotlib` / `seaborn` for static figures; `plotly` or `bokeh` when interaction is requested.
5. **Mandatory visual inspection:** render at the target dimensions and view the saved `.png`/`.svg` output with `read_file` (or browser/viewer) to verify zero clipped titles, overlapping tick labels, or colliding legends.

## 2. Multi-panel publication figures

When composing a multi-panel figure (`1x2`, `2x2`, or custom grid):

1. State the figure's **single argument** and plan each panel (`(a)`, `(b)`, `(c)`, ...) so every panel earns its space.
2. Keep shared scales, fonts, and color-to-category mappings identical across panels; share a single legend whenever panels use the same encoding.
3. Assemble cleanly with `patchwork` or `cowplot` in R (or `gridspec` / `constrained_layout` in Python) rather than manual pixel pasting.

## 3. Interactive graphics (only when requested)

HTML output alone does not require interactive widgets; add interaction only when requested:

- Prefer **Plotly** for interactive plots and **Bokeh** when custom linked views justify it. Keep essential takeaways readable before hover, make active filters/resets obvious, and verify dark and light themes.
- When building Plotly figures (especially via `ggplotly`), read [plotly-text-layout.md](references/plotly-text-layout.md), use `scripts/safe_ggplotly.R` when in R, and validate rendered HTML/JSON output with:
  ```bash
  python3 <skill-directory>/scripts/check_plotly_layout.py path/to/output.html
  ```
