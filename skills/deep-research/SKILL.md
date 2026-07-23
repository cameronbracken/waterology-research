---
name: deep-research
description: >
  Run a thorough, source-heavy investigation on any topic. Use when the user
  asks for deep research, a comprehensive analysis, an in-depth report, or a
  multi-source investigation. Produces a cited research brief with provenance
  tracking.
---

# Deep Research

Run the `/deepresearch` workflow. The command expands the full protocol in the
active session — plan, scale, gather, draft, cite, review, deliver — do not try
to read a prompt-template path from this skill directory.

Agents used: `researcher`, `verifier`, `reviewer`.
Output: a cited brief in `outputs/` (or `papers/`) with a `.provenance.md` sidecar.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
