---
name: ml-training-recipe
description: >
  Find implementable ML training recipes from papers, datasets, docs, and code.
  Use when the user wants to fine-tune, train, reproduce, or choose a practical
  ML method, dataset, hyperparameter setup, or benchmark — including energy,
  climate, and hydrology forecasting models.
---

# ML Training Recipe

Use `writing-style` for the recipe, comparisons, and recommendation.

Run the `/recipe` workflow. It starts from evidence of results (not example
scripts), links each result to the exact dataset, method, hyperparameters,
compute, and code path that produced it, validates dataset availability and
schema, and delivers a ranked recipe table with a recommendation and known gaps.

Agents used: `researcher`.
Output: `outputs/<slug>-recipe.md` with `outputs/<slug>-recipe.provenance.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
