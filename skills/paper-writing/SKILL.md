---
name: paper-writing
description: >
  Turn research findings into a polished paper-style draft with sections,
  equations, and citations. Use when the user asks to write a paper, draft a
  report, write up findings, or produce a technical document from collected
  research.
metadata:
  claude-command:
    name: draft
    argument-hint: <topic>
---

# Paper Writing

<!-- Adapted from companion-inc/feynman, skills/paper-writing/SKILL.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use the `writing-style` skill and its scientific prose layer for the draft and
final edit.

Derive a short topic slug with lowercase hyphenated words, no filler words, and
at most five words. Write `docs/.plans/<slug>.md` before drafting. Include the
title, sections, claims, supplied source material, and verification checks for
critical claims, figures, and calculations. Briefly summarize the plan and
continue unless the user asked to review it first.

Draft only from collected notes and verified sources. For substantial work,
give the `writer` the evidence and output path, then give the resulting draft
and sources to the `verifier` through the runtime's available agent mechanism.
Keep their work sequential so verification reads the completed draft.

Include a title, abstract, problem statement, related work, method or synthesis,
evidence or experiments, limitations, and conclusion when the evidence supports
those sections. Use Quarto or LaTeX for a real manuscript and LaTeX math when an
equation helps. Never hand-type a computed number. Use `\input{}` or an inline
code result tied to the analysis. If evidence is missing, leave a placeholder
or proposed analysis instead of claiming a result.

Every result, figure, table, and quantitative comparison needs provenance. Use
a source backed table or chart specification instead of inventing a figure, and
apply `figure-style` to plots. Before delivery, weaken or remove claims that
exceed their support and remove unsupported numerics.

Save exactly one draft to `papers/<slug>.md`. End with a `Sources` appendix of
direct URLs for all primary references.

Agents used: `writer`, `verifier`.
Output: `papers/<slug>.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
