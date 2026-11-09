#!/usr/bin/env Rscript
# =============================================================================
# Reusable Earth-Tone Publication Figure Template for Technical & Benchmark Reports
# Usage: Rscript scripts/plot_<topic>_figures.R <results.json> <figures_dir>
# =============================================================================

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
json_path <- if (length(args) >= 1) args[1] else "reports/example/results.json"
fig_dir   <- if (length(args) >= 2) args[2] else "reports/example/figures"
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

# Cohesive Earth-Tone Publication Palette
ET_PINE     <- "#2e6b4e"
ET_SLATE    <- "#3d6b82"
ET_OCHRE    <- "#c4842d"
ET_TERRA    <- "#b84a39"
ET_SAGE     <- "#6b9080"
ET_PLUM     <- "#7a5177"
ET_CHARCOAL <- "#2b2b2b"
ET_STONE    <- "#8c857b"
ET_SAND     <- "#f4f1ea"
ET_GOLD     <- "#d4a038"
ET_TEAL     <- "#2a7b88"

ET_PINE_B   <- "#1f4d37"
ET_SLATE_B  <- "#284b5c"
ET_OCHRE_B  <- "#8f5d19"
ET_TERRA_B  <- "#853023"
ET_SAGE_B   <- "#49695b"
ET_PLUM_B   <- "#543452"

# Helper: Add direct value labels above grouped or single bars
add_bar_labels <- function(bp, vals_plot, vals_raw = vals_plot, cex = 0.62,
                           offset = 0.032, digits = 2, bold_rows = NULL) {
  nr <- nrow(vals_plot)
  nc <- ncol(vals_plot)
  for (r in seq_len(nr)) {
    for (c in seq_len(nc)) {
      v_raw <- vals_raw[r, c]
      v_plt <- vals_plot[r, c]
      if (is.finite(v_raw)) {
        lbl <- sprintf(paste0("%.", digits, "f"), v_raw)
        fnt <- if (!is.null(bold_rows) && (r %in% bold_rows)) 2 else 1
        text(bp[r, c], max(v_plt, 0) + offset, labels = lbl,
             cex = cex, col = ET_CHARCOAL, font = fnt, xpd = TRUE)
      }
    }
  }
}

# Helper: Order a cross-family comparison so Left of the red line is Ascending (Low -> High)
# and Right of the red line is Descending (High -> Low) by the primary metric (`wy_raw`).
build_split_peak_order <- function(left_labels, left_primary, left_secondary,
                                   right_labels, right_primary, right_secondary) {
  ord_left  <- order(left_primary, decreasing = FALSE)
  ord_right <- order(right_primary, decreasing = TRUE)
  list(
    labels    = c(left_labels[ord_left], right_labels[ord_right]),
    primary   = c(left_primary[ord_left], right_primary[ord_right]),
    secondary = c(left_secondary[ord_left], right_secondary[ord_right]),
    n_left    = length(ord_left)
  )
}
