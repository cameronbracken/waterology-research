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
