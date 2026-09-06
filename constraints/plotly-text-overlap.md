# Plotly text overlap

**Check:** `plotly-text-overlap.py`
**Applies to:** `.Rmd` and `.qmd` documents

Interactive Plotly layouts must reserve separate regions for titles, legends,
facet labels, axes, and tick labels.

The check rejects these predictable collision risks in rendered HTML:

- a title or subtitle inside the Plotly canvas;
- a horizontal legend above the plotting domain;
- an external bottom or right legend without enough margin; and
- a visible text bearing axis without `automargin = TRUE`.

Place the figure title and caption in the document. Put interactive legends
below or to the right of the plotting domain, reserve their margin, and enable
axis automargins. The `figure-style` skill includes a reusable R helper and a
standalone checker for this layout contract.

For `.Rmd` and `.qmd` sources, the scanner detects Plotly references in executable
chunks and checks the corresponding rendered HTML. It reads `output-file` from
front matter and a Quarto project's `output-dir` (including the `_site` and
`_book` defaults). Missing HTML, HTML older than the source or project config,
and renders without inspectable layouts fail with an instruction to render.
The scanner does not execute document code.

R htmlwidgets and Python Plotly HTML with literal JSON `Plotly.newPlot` arguments
are supported. Embedded htmlwidgets are also checked. Arbitrary JavaScript and
Plotly calls hidden inside external helpers cannot be resolved statically. Pass
the rendered HTML explicitly when the source does not name Plotly. Timestamp
checks do not establish freshness of external data or helper scripts.
