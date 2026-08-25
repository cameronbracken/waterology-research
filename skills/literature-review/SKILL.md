---
name: literature-review
description: >
  Run a literature review using paper search and primary-source synthesis. Use
  when the user asks for a lit review, paper survey, state of the art, or the
  research landscape on a topic — or a publication-corpus review of a specific
  lab, PI, or author.
---

# Literature Review

Use `writing-style` for the review and source synthesis.

Run the `/lit` workflow. It plans the scope, gathers papers in multi-hop passes
(new queries built from each hop's citations, authors, and terminology, until a
hop surfaces nothing new; wide sweeps delegated to the `researcher` agent),
synthesizes consensus and disagreement by theme, cites via the `verifier`,
checks with the `reviewer`, and delivers a cited review plus provenance and a
short "start here" reading list.

When the target names a lab, PI, or author, it runs as a publication-corpus
review: resolve identity, collect the reachable publication list, then map the
research trajectory.

Agents used: `researcher`, `verifier`, `reviewer`.
Output: `docs/<slug>.md` with `docs/<slug>.provenance.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT); multi-hop search from
openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See
`${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
