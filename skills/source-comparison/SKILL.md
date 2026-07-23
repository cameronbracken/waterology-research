---
name: source-comparison
description: >
  Compare multiple sources on a topic and produce a grounded comparison matrix.
  Use when the user asks to compare papers, tools, approaches, frameworks, or
  claims across multiple sources.
---

# Source Comparison

Run the `/compare` workflow. It plans the sources and dimensions, gathers
material (delegating broad sets to the `researcher`), and builds a matrix of
source, key claim, evidence type, caveats, and confidence — cited via the
`verifier`, with agreement, disagreement, and uncertainty kept distinct.

Agents used: `researcher`, `verifier`.
Output: `outputs/<slug>-comparison.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
