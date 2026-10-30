---
name: interactive-graphics
description: >
  Add requested interaction to data visualizations or conceptual diagrams:
  hover, zoom, selection, filtering, linked views, sliders, expandable nodes,
  or explorable schematics. Use for interactive graphics, not static visuals
  or a report's narrative and page structure.
---

# Interactive Graphics

Apply this layer only when interaction is requested or is part of the accepted
deliverable. HTML output alone does not require interactive graphics.
If the base guidance is not already loaded, read only the matching skill:
[data-visualization](../data-visualization/SKILL.md) for measured or computed
data, or [diagrams](../diagrams/SKILL.md) for conceptual relationships. Do not
reload a skill or reference already read for this task.

Use `waterology config context interactive-graphics` for optional local
guidance, or the
[local resolver](../project-conventions/references/local-preferences.md).

- Choose interaction that answers the user's question. Make controls, units,
  selected states, and reset behavior visible. Keep essential information
  accessible without hover alone.
- Prefer Plotly for ordinary interactive data plots. Use Bokeh when richer
  linked behavior is justified and supported by the delivery environment.
  For diagrams, choose a renderer with the requested node, edge, or navigation
  behavior; do not force a conceptual diagram into a plotting library.
- Preserve data and relationship meaning while filtering or changing views.
  Make hidden or excluded subsets clear. Avoid silently changing scales in
  ways that invalidate comparisons.
- Prefer dark mode for interactive work. Check contrast and data encodings
  in every supported theme; changing the page background alone is insufficient.
- Test the actual controls and inspect desktop and narrower layouts. Provide
  a static export or text equivalent when needed for print or accessibility.
  Record server or network requirements when the interaction cannot run offline.

For Plotly only, read
[Plotly text layout](../figure-style/references/plotly-text-layout.md). Use the
safe conversion helper when practical and run the bundled layout checker on
the final rendered output. These resources are usable without loading the
entire scientific figure skill; a passing structural check does not replace
visual inspection or control testing.

Load [interactive-reports](../interactive-reports/SKILL.md) only when building
the report around the graphic. A standalone widget does not require a report.
