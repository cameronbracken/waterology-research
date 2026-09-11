---
name: figure-style
description: >
  Apply scientific plotting and figure-quality rules to a single plot or panel.
  Use when drawing, cleaning, labeling, or reviewing a plot for a research
  artifact, paper, or report.
---

# Figure Style

Use `writing-style` for labels, annotations, and captions. Run
`waterology config context figure-style` for optional local design guidance.
Project and local choices take precedence over the example stack below.

Apply before producing or revising any single plot. This is the research-figure
layer; for general chart-design method (palette construction, mark specs), also
see the `dataviz` skill.

If the CLI is unavailable, use the shared
[local preferences resolver](../project-conventions/references/local-preferences.md)
with this skill name, including common preferences and matching local guidance.

Checklist:

1. **Chart type from the data and claim**, not from decoration. A distribution
   wants a density or ECDF, not a bar of means; a time series over water years
   wants a line, not a scatter.
2. **Label axes with units**, define any transformation (log flow, standardized
   anomaly), and show uncertainty or replicate structure when it exists
   (ribbons, error bars, or the raw ensemble behind a mean).
3. **Color carries meaning only.** Use it for real grouping, keep palettes
   colorblind-safe (Okabe-Ito for categories, viridis for sequential), and keep the mapping consistent across panels.
4. **Separate figures with whitespace, not container chrome.** Do not add a
   border, rounded box, background card, or shadow around a plot unless the
   boundary encodes information. For report HTML, use the bundled
   `assets/report-figure.css` or an equivalent borderless wrapper.
5. **Render and inspect** text, tick labels, legends, clipping, and
   overplotting before saving. Inspect the target width and a narrower layout;
   source inspection is not evidence that the rendered text fits.
6. **Save the code and data to regenerate it**, not just the image. A polished
   plot with unverifiable data is not acceptable; preserve provenance first.

For Plotly or `ggplotly` output, read
[Plotly text layout](references/plotly-text-layout.md). Do not accept the
default `ggplotly` title and top legend layout. Use the bundled safe conversion
helper when practical, then run the bundled layout checker on the rendered
HTML. The checker catches known structural risks; it does not replace visual
inspection.

Stack defaults (match a project's existing style first):
- **ggplot2** with a clean theme (`theme_minimal()` or a project theme), native
  pipe `|>`, `\(x)` lambdas, formatted with **air**. See `rules/r-conventions.md`.
- **Light mode for print**, vector output (PDF or SVG) for simple figures and
  PNG for dense ones. For interactive/dark contexts use plotly or bokeh.
- In Quarto, generate the figure in a code chunk with a caption and never
  hand-type a computed number into the caption or annotation — pull it from the
  data. See `rules/quarto-conventions.md`.
