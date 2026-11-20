---
name: research-review
description: >
  Run a rigorous, constructive critique of a paper, draft, report, analysis, or
  simulation study, or reshape a manuscript's scientific narrative and figure
  arc before submission.
metadata:
  claude-command:
    name: review
    argument-hint: <manuscript, report, or analysis path>
---

# Research Review and Manuscript Narrative

Use [writing-style](../writing-style/SKILL.md) (`references/scientific-prose.md`) when evaluating prose clarity and claim calibration.

## Choose focus

- **Internal peer critique (default):** Stress-test methods, baselines, statistical/physical assumptions, leakage, uncertainty, code-to-prose consistency, and conclusions across hydrology/energy modeling, statistics/extremes, Monte Carlo studies, or ML benchmarks.
- **Narrative and figure arc:** Extract the central claim, target audience, section order, and figure sequence; identify figures that overclaim or redundant panels; propose concrete structural reordering before line-editing.

For large manuscripts or when the current session authored the draft, delegate the review to the `reviewer` subagent so it inspects the artifact with fresh context. Do not create intermediate `.plans/` or `.drafts/` files.

## Inspection rules

- Read the actual manuscript, code, and produced tables/figures rather than trusting prose summaries or exit codes.
- Distinguish observed methodological or numerical defects from blocked checks (`Verification: BLOCKED` when external data or full text is unavailable).
- Tie every requested baseline, sensitivity check, or diagnostic to a specific claim weakness rather than padding a generic checklist.

## Output

Write a single concise review (`docs/<slug>-review.md` when a saved file is useful, or directly in chat for quick feedback):

1. **Overall assessment:** Central claim, main strengths, and decisive blockers.
2. **Prioritized findings (`FATAL`, `MAJOR`, `MINOR`):** Location (section/figure/file:line), inspected evidence, consequence for the claim, and concrete remedy.
3. **Revision plan:** Ordered, practical edits or analyses to resolve `FATAL` and `MAJOR` items.
