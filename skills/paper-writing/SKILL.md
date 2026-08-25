---
name: paper-writing
description: >
  Turn research findings into a polished paper-style draft with sections,
  equations, and citations. Use when the user asks to write a paper, draft a
  report, write up findings, or produce a technical document from collected
  research.
---

# Paper Writing

Run the `/draft` workflow. It outlines the structure, produces the draft from
collected notes with the `writer` agent, then adds inline citations and verifies
sources with the `verifier`.

Use the `writing-style` skill and its scientific prose layer for the draft and
final edit.

Write real manuscripts in Quarto or LaTeX. Never hand-type a computed number —
reference it with `\input{}` or an inline code result so it stays tied to the
analysis. See `rules/quarto-conventions.md` for the document conventions and the
`figure-style` skill for any plot.

Agents used: `writer`, `verifier`.
Output: `papers/<slug>.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
