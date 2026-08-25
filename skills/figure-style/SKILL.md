---
name: figure-style
description: >
  Apply scientific plotting and figure-quality rules to a single plot or panel.
  Use when drawing, cleaning, labeling, or reviewing a plot for a research
  artifact, paper, or report.
---

# Figure Style

<!-- Adapted from companion-inc/feynman, skills/figure-style/SKILL.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for labels, annotations, and captions.

Apply before producing or revising any single plot. This is the research-figure
layer; for general chart-design method (palette construction, mark specs), also
see the `dataviz` skill.

Checklist:

1. **Chart type from the data and claim**, not from decoration. A distribution
   wants a density or ECDF, not a bar of means; a time series over water years
   wants a line, not a scatter.
2. **Label axes with units**, define any transformation (log flow, standardized
   anomaly), and show uncertainty or replicate structure when it exists
   (ribbons, error bars, or the raw ensemble behind a mean).
3. **Color carries meaning only.** Use it for real grouping, keep palettes
   colorblind-safe (Okabe-Ito for categories, viridis for sequential), lean on
   earth tones, and keep the mapping consistent across panels.
4. **Render and inspect** text, tick labels, legends, clipping, and
   overplotting before saving — actually look at the output, do not assume.
5. **Save the code and data to regenerate it**, not just the image. A polished
   plot with unverifiable data is not acceptable; preserve provenance first.

Stack defaults (match a project's existing style first):
- **ggplot2** with a clean theme (`theme_minimal()` or a project theme), native
  pipe `|>`, `\(x)` lambdas, formatted with **air**. See `rules/r-conventions.md`.
- **Light mode for print**, vector output (PDF or SVG) for simple figures and
  PNG for dense ones. For interactive/dark contexts use plotly or bokeh.
- In Quarto, generate the figure in a code chunk with a caption and never
  hand-type a computed number into the caption or annotation — pull it from the
  data. See `rules/quarto-conventions.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
