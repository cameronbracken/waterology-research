# %% Safe Plotly conversion

waterology_ggplotly = function(
  plot,
  tooltip = "text",
  legend = c("bottom", "right", "none"),
  target_width_px = 900,
  axis_standoff_px = 12
) {
  if (!inherits(plot, "ggplot")) {
    stop("plot must inherit from ggplot", call. = FALSE)
  }
  if (!requireNamespace("plotly", quietly = TRUE)) {
    stop("plotly is required", call. = FALSE)
  }
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("ggplot2 is required", call. = FALSE)
  }

  legend = match.arg(legend)
  interactive_plot =
    plot +
      ggplot2::theme(
        plot.title = ggplot2::element_blank(),
        plot.subtitle = ggplot2::element_blank(),
        plot.caption = ggplot2::element_blank()
      )
  widget = plotly::ggplotly(interactive_plot, tooltip = tooltip)
  widget$x$layout$title = NULL

  axis_names = grep("^[xy]axis[0-9]*$", names(widget$x$layout), value = TRUE)
  for (axis_name in axis_names) {
    axis = widget$x$layout[[axis_name]]
    axis$automargin = TRUE
    if (is.character(axis$title)) {
      axis$title = list(text = axis$title)
    }
    if (is.list(axis$title)) {
      axis$title$standoff = axis_standoff_px
    }
    widget$x$layout[[axis_name]] = axis
  }

  margin = widget$x$layout$margin
  if (is.null(margin)) {
    margin = list()
  }
  for (side in c("t", "r", "b", "l")) {
    if (is.null(margin[[side]])) {
      margin[[side]] = 24
    }
  }
  margin$t = max(margin$t, 24)

  trace_labels =
    vapply(
      widget$x$data,
      function(trace) {
        if (identical(trace$showlegend, FALSE) || is.null(trace$name)) "" else trace$name
      },
      character(1)
    ) |>
    unique()
  trace_labels = trace_labels[nzchar(trace_labels)]

  if (legend == "bottom" && length(trace_labels) > 0L) {
    longest_label = max(nchar(gsub("<[^>]+>", "", trace_labels)))
    entry_width = min(260, max(120, 36 + 8 * longest_label))
    legend_columns = max(1, floor((target_width_px - 48) / entry_width))
    legend_rows = ceiling(length(trace_labels) / legend_columns)
    margin$b = max(margin$b, 72 + 28 * legend_rows)
    widget$x$layout$legend = modifyList(
      widget$x$layout$legend,
      list(
        orientation = "h",
        x = 0,
        y = -0.16,
        xanchor = "left",
        yanchor = "top",
        entrywidth = entry_width,
        entrywidthmode = "pixels"
      )
    )
  } else if (legend == "right" && length(trace_labels) > 0L) {
    longest_label = max(nchar(gsub("<[^>]+>", "", trace_labels)))
    margin$r = max(margin$r, min(360, 48 + 8 * longest_label))
    widget$x$layout$legend = modifyList(
      widget$x$layout$legend,
      list(
        orientation = "v",
        x = 1.02,
        y = 1,
        xanchor = "left",
        yanchor = "top"
      )
    )
  } else if (legend == "none") {
    widget$x$layout$showlegend = FALSE
  }

  widget$x$layout$margin = margin
  widget
}
