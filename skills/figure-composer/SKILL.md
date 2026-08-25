---
name: figure-composer
description: >
  Compose a publication-grade multi-panel scientific figure from a claim,
  dataset, or draft result. Use when the task needs panel planning, consistent
  figure layout, figure review, or final multi-panel assembly.
---

# Figure Composer

Use `writing-style` for panel text, captions, and figure notes.

For multi-panel scientific figures — the composite that carries one argument.

1. State the figure's **single claim** and list every data artifact that
   supports it.
2. Draft a **panel plan**: labels (a, b, c), chart type per panel, data source,
   required annotations, and what each panel proves.
3. Style each plot with the `figure-style` skill before composing, so axes,
   fonts, and the color mapping stay consistent across panels.
4. **Render, inspect, and revise** for label collisions, axis readability,
   color meaning, caption fit, and data-source fidelity.
5. Save the final figure, the source data, the generation code, the caption,
   and a provenance sidecar.

Do not invent data or hide excluded data inside a summary panel.

Stack defaults: assemble panels with **patchwork** or **cowplot** over ggplot2;
keep a shared legend where panels share an encoding; export vector (PDF/SVG) for
print. In Quarto, build the composite in one code chunk with a figure caption
and cross-reference. See `rules/r-conventions.md` and `rules/quarto-conventions.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
