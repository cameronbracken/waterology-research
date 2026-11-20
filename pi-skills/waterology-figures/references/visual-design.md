# Visual design defaults

Apply these defaults when the user and project leave visual choices open:

- **Earth-tone house palette** for categorical series and diagrams (with >= 3:1 contrast and secondary shape/linetype cues where needed for color vision deficiency):
  - Pine (`#2e6b4e`), Slate (`#3d6b82`), Ochre (`#c4842d`), Terracotta (`#b84a39`), Sage (`#6b9080`), Plum (`#7a5177`), Gold (`#d4a038`), Stone (`#8c857b`), Charcoal (`#2b2b2b`).
  - Use perceptually uniform palettes (`viridis` / `cividis` or earth-tone diverging ramps) for continuous scalar fields.
- **No container chrome:** separate figures with whitespace rather than decorative cards, borders, drop shadows, or background boxes unless a boundary encodes grouping. Use `assets/report-figure.css` when embedding figures in HTML.
- **Theme by medium:** light background for print, PDFs, manuscripts, and slides; Darkly default with a Flatly light toggle for interactive HTML reports (adapting data colors for dark backgrounds rather than inverting page CSS alone).
- **Export format and inspection:** SVG or PDF for vector graphics, 200+ DPI Cairo PNG for dense plots or Markdown report bundles. Set explicit width/height and inspect the rendered image file directly for label collisions, clipping, and legibility before finishing.
