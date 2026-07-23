---
name: research-review
description: >
  Run a tough but constructive internal critique of a research artifact — paper,
  draft, analysis, or simulation study. Use when the user asks for a review,
  critique, or feedback on a paper or draft, or wants weaknesses identified
  before submission.
---

# Research Review

Run the `/review` workflow. It plans the review criteria, inspects the artifact
(local file, PDF, arXiv ID, or URL), writes evidence notes, and produces a
structured review with severity-graded findings and inline annotations.

The `reviewer` agent covers not only AI/ML work but hydrology model evaluations,
statistical-extremes analyses, and Monte Carlo studies — including the
coverage-against-the-estimate error and dropped non-converged replicates.

Agents used: `researcher`, `reviewer` (when the artifact is large enough to benefit).
Output: `outputs/<slug>-review.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
