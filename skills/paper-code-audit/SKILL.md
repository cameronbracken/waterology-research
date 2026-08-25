---
name: paper-code-audit
description: >
  Compare a paper's claims against its public codebase. Use when the user asks
  to audit a paper, check code-claim consistency, verify a paper's
  reproducibility, or find mismatches between a paper and its implementation.
---

# Paper / Code Audit

Use `writing-style` for the audit report and claim comparisons.

Run the `/audit` workflow. It plans which claims to check, reads the actual code
(cloning with `gh` when needed rather than trusting the README), and reports
missing code, method/default mismatches, unstated seeds, and reproduction risks.

Agents used: `researcher`, `verifier` (for non-trivial audits).
Output: `docs/<slug>-audit.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
