---
name: data-visualization
description: >
  Create or revise data visualizations: plots, charts, graphs, maps, graphics,
  figures, or images that encode measured or computed data. Use for static or
  interactive data displays, rather than conceptual diagrams or illustrations.
---

# Data Visualization

Choose the display from the data and the question it should answer. A request
for an image of a chart belongs here; a photograph or illustration belongs with
an available image creation tool, not a plotting workflow.

Read [visual design](references/visual-design.md). Read optional local guidance
with `waterology config context data-visualization`, or use the
[local resolver](../project-conventions/references/local-preferences.md).

- Identify the data source, units, transformations, and intended comparison.
  Do not invent observations or disguise missing data. Label synthetic examples.
- Prefer ggplot2 when working in R; use the project's plotting stack otherwise.
  Load [r-code-style](../r-code-style/SKILL.md) only when writing R.
- Label axes, scales, categories, and uncertainty as needed to interpret the
  figure. Preserve meaningful comparisons when choosing limits and scales.
- Save the generation code and enough input or source references to regenerate
  the visual. Follow the project's reproducibility mode for additional records.
- For standalone visual deliverables, start with a Markdown preview containing
  embedded images unless another format was requested. Apply
  [Markdown delivery](../writing-style/references/markdown-artifacts.md) when
  producing that file. A plot request alone does not require a full report.

Load only the matching addition:

- Scientific plot styling, labels, or review:
  [figure-style](../figure-style/SKILL.md).
- Publication figure with multiple panels:
  [figure-composer](../figure-composer/SKILL.md).
- Requested hover, zoom, filtering, linked views, or other interaction:
  [interactive-graphics](../interactive-graphics/SKILL.md).

Embedding an existing figure requires checking its source, caption, and
readability; it does not require loading a figure creation skill.
