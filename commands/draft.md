---
description: Turn research findings into a polished paper-style draft with equations, sections, and explicit claims.
argument-hint: <topic>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Write a paper-style draft for: $ARGUMENTS

Tools: `WebSearch`/`WebFetch` for sources; the `Task` tool to launch the `writer` (synthesis) and `verifier` (citations) agents.

Derive a short slug from the topic (lowercase, hyphens, no filler words, at most 5 words). Use it for all files in this run.

Requirements:
- Before writing, outline the draft: proposed title, sections, key claims, source material to draw from, and a verification log for the critical claims, figures, and calculations. Write the outline to `outputs/.plans/<slug>.md`. Summarize it briefly and continue immediately unless the user asked to review it first.
- Use the `writer` subagent to produce the draft from already-collected notes, then the `verifier` subagent to add inline citations and verify sources.
- Include at minimum: title, abstract, problem statement, related work, method or synthesis, evidence or experiments, limitations, conclusion.
- Write in Quarto or LaTeX where the target is a real manuscript; use LaTeX math where equations materially help. Never hand-type a computed number — reference it with `\input{}` or an inline code result so it stays tied to the analysis that produced it.
- Follow the provenance rule for all results, figures, tables, and quantitative comparisons. If evidence is missing, leave a placeholder or a proposed analysis plan instead of claiming an outcome.
- Write a chart specification or source-backed table rather than fabricating a figure; every figure, chart spec, or table needs provenance. Follow the `figure-style` skill for any plot produced.
- Before delivery, sweep the draft for claims stronger than their support. Mark tentative results as tentative and remove unsupported numerics rather than letting the verifier discover them.
- Save exactly one draft to `papers/<slug>.md`, ending with a `Sources` appendix of direct URLs for all primary references.
