---
name: research-review
description: >
  Run a tough but constructive internal critique of a research artifact: paper,
  draft, analysis, or simulation study. Use when the user asks for a review,
  critique, or feedback on a paper or draft, or wants weaknesses identified
  before submission.
metadata:
  claude-command:
    name: review
    argument-hint: <artifact>
---

# Research Review

Use the `writing-style` skill to check claim strength, terminology, and prose
clarity without replacing the evidence review.

The `reviewer` agent covers not only AI/ML work but hydrology model evaluations,
statistical extremes analyses, and Monte Carlo studies, including the
coverage-against-the-estimate error and dropped non-converged replicates.

Derive a short slug from the artifact name. Create these artifacts:

- Plan: `docs/.plans/<slug>-review-plan.md`
- Evidence notes: `docs/.drafts/<slug>-review-evidence.md`
- Final review: `docs/<slug>-review.md`

Identify the artifact and source type, then plan checks for novelty, empirical
rigor, baselines, reproducibility, claim validity, figures, tables, metrics,
related work, and writing. Briefly summarize the plan and continue unless the
user asked to review it first.

Inspect local files directly. Fetch named remote sources and record their URLs.
Extract PDFs with an available parser. If parsing or evidence retrieval fails,
record the failure and continue with a partial review. Write evidence notes
before conclusions, including observed claims, methods, metrics, baselines,
reproducibility facts, and every inspected path or URL.

For a large artifact, delegate evidence gathering to the `researcher` and the
critique to the `reviewer` through the runtime's available agent mechanism.
Give each agent an explicit artifact, criteria, output path, and return
contract. For a smaller artifact, review directly.

Write exactly one final review with Summary Assessment, Strengths, Critical
Issues, Major Issues, Minor Issues, Reproducibility and Verification, Inline
Annotations, Recommendation, and Sources. Tie annotations to specific claims,
sections, figures, or tables. If critical evidence is unavailable, keep the
artifact, mark the affected checks `Verification: BLOCKED`, and distinguish
blocked checks from observed weaknesses.

Confirm `docs/<slug>-review.md` exists before reporting completion. If the
review cannot proceed, create that file as a blocked review with the reason.

Agents used: `researcher`, `reviewer` (when the artifact is large enough to benefit).
Output: `docs/<slug>-review.md`.
