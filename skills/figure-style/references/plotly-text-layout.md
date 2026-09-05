# Plotly text layout

Use this reference for Plotly figures in Quarto or other responsive HTML.

## Why the default fails

`ggplotly()` commonly puts the ggplot title inside the Plotly canvas and a
horizontal legend just above the plotting domain. Facet labels use the same
upper region. Plotly then inherits margins sized for the static ggplot rather
than the browser layout. Long titles, legends, facet labels, and axis text can
overlap even when the saved PNG is correct.

Treat static and interactive layout as separate outputs from the same plot
object. A correct static image does not validate its interactive conversion.

## Layout contract

For interactive Plotly figures:

1. Put the title and explanatory caption in the document, outside the Plotly
   canvas. Keep a title in a standalone static fallback if useful.
2. Place the legend below or to the right of the plotting domain. Never rely on
   the default top horizontal legend for titled or faceted output.
3. Reserve margin for the chosen legend position and its longest labels.
4. Set `automargin = TRUE` on every visible text bearing axis. Give axis titles
   a small standoff.
5. Render at the intended desktop width and at about 768 px. Inspect the figure
   with the longest title, legend labels, category labels, and facet labels.
6. Run the structural checker after the final render. A passing checker does
   not prove that every pixel is legible, so keep the visual inspection.

## R and ggplotly

The bundled `scripts/safe_ggplotly.R` defines `waterology_ggplotly()`. It leaves
the supplied ggplot unchanged for static export, removes its title, subtitle,
and caption from the interactive canvas, enables axis automargins, and reserves
space for an external legend.

```r
source(file.path(waterology_root, "skills", "figure-style", "scripts", "safe_ggplotly.R"))

static_plot = build_plot(data)
ggsave("figures/result.png", static_plot, width = 10, height = 6, dpi = 180)

widget = waterology_ggplotly(
  static_plot,
  tooltip = "text",
  legend = "bottom",
  target_width_px = 900
)
widget
```

Set the Quarto chunk `fig-cap` or add a short document heading for the title.
Use `legend = "right"` when a short vertical legend costs less space than a
multirow bottom legend. Use `legend = "none"` only when labels or the document
make every series unambiguous.

## Native Plotly

Apply the same contract when building Plotly directly. In Python, for example:

```python
figure.update_layout(
    title=None,
    legend={
        "orientation": "h",
        "x": 0,
        "y": -0.2,
        "xanchor": "left",
        "yanchor": "top",
    },
    margin={"t": 24, "r": 24, "b": 160, "l": 48},
)
figure.update_xaxes(automargin=True, title_standoff=12)
figure.update_yaxes(automargin=True, title_standoff=12)
```

Adjust the bottom margin when the legend wraps to more than one row. Keep the
title in the surrounding Quarto or HTML element so normal browser text wrapping
handles narrow screens.

## Automated check

Run after Quarto renders the final HTML:

```bash
python3 <waterology-root>/skills/figure-style/scripts/check_plotly_layout.py \
  reports/<slug>/<slug>.html
```

The checker accepts htmlwidget HTML and Plotly JSON. It fails on an internal
Plotly title, a top horizontal legend, an underreserved external legend, or a
text bearing axis without automargin. Waterology's constraint runner applies
the same check automatically to rendered HTML under its target paths.
