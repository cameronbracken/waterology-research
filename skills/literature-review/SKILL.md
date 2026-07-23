---
name: literature-review
description: >
  Run a literature review using paper search and primary-source synthesis. Use
  when the user asks for a lit review, paper survey, state of the art, or the
  research landscape on a topic — or a publication-corpus review of a specific
  lab, PI, or author.
---

# Literature Review

Run the `/lit` workflow. It plans the scope, gathers papers (delegating wide
sweeps to the `researcher` agent), synthesizes consensus and disagreement, cites
via the `verifier`, checks with the `reviewer`, and delivers a cited review plus
provenance.

When the target names a lab, PI, or author, it runs as a publication-corpus
review: resolve identity, collect the reachable publication list, then map the
research trajectory.

Agents used: `researcher`, `verifier`, `reviewer`.
Output: `outputs/<slug>.md` with `outputs/<slug>.provenance.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
