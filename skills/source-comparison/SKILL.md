---
name: source-comparison
description: >
  Compare multiple sources on a topic and produce a grounded comparison matrix.
  Use when the user asks to compare papers, tools, approaches, frameworks, or
  claims across multiple sources.
metadata:
  claude-command:
    name: compare
    argument-hint: <topic>
---

# Source Comparison

<!-- Adapted from companion-inc/feynman, skills/source-comparison/SKILL.md at
commit 8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for the matrix notes and grounded comparison.

Derive a short slug from the comparison topic. Use lowercase words separated by
hyphens, omit filler words, and keep at most five words.

Write `docs/.plans/<slug>.md` before gathering evidence. Name the sources or
source types, comparison dimensions, evidence needed, and intended output.
Briefly summarize the plan and continue unless the user asked to review it
first.

Gather primary material for every source. Delegate broad source sets to the
`researcher` through the runtime's available agent mechanism. For a narrow
direct comparison, verify every source URL and inline citation directly after
drafting. For a broad or delegated comparison, delegate verification to the
`verifier`. Give each agent explicit source scope, file ownership, and return
paths.

Build a comparison matrix with source, claim, evidence type, caveats, and
confidence. State agreement, disagreement, and uncertainty separately. Use a
source backed table for quantitative comparisons. Use a Mermaid diagram for a
method or architecture comparison only when the relationships are supported by
the sources. Apply `figure-style` if a plot would change the decision.

Save exactly one comparison to `docs/<slug>-comparison.md`. End it with a
`Sources` section containing a direct URL for every source used.

Agents used: `researcher`, `verifier`.
Output: `docs/<slug>-comparison.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
