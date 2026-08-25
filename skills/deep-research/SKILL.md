---
name: deep-research
description: >
  Run a thorough, source-heavy investigation on any topic. Use when the user
  asks for deep research, a comprehensive analysis, an in-depth report, or a
  multi-source investigation. Produces a cited research brief with provenance
  tracking.
metadata:
  claude-command:
    name: deepresearch
    argument-hint: <topic>
---

# Deep Research

<!-- Adapted from companion-inc/feynman, skills/deep-research/SKILL.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for the research brief and synthesis.

Read [workflow.md](references/workflow.md) and follow it for the complete plan,
scale, evidence, drafting, citation, review, and delivery protocol.

Agents used: `researcher`, `verifier`, `reviewer`.
Output: a cited brief in `docs/` (or `papers/`) with a `.provenance.md` sidecar.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
