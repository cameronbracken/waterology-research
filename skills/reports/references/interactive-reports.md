# Interactive Quarto HTML reports

Use only when the user explicitly requests an interactive report or standalone explorable HTML summary (otherwise produce the default Markdown report bundle in `SKILL.md`).

- Author in **Quarto** following `rules/quarto-conventions.md`, setting `embed-resources: true` and dual themes (`dark: darkly` default with `light: flatly` toggle; keep print exports light).
- Compute heavy metrics and static/interactive artifacts in scripts first and import them into `.qmd` so rendering stays fast and deterministic. Never hand-type computed numbers.
- Load [figures](../../figures/SKILL.md) when building interactive Plotly/Bokeh charts, and run `figures/scripts/check_plotly_layout.py` on rendered HTML to catch title/legend/facet text collisions.
- Keep titles, captions, prose, and filter explanations outside plot canvases in borderless layout containers with clean whitespace.
- Make the default initial state informative without requiring clicks, document what controls filter, and verify both dark and light themes plus offline standalone behavior after rendering.
