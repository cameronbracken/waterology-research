---
name: paper-code-audit
description: >
  Compare a paper's claims against its public codebase. Use when the user asks
  to audit a paper, check code-claim consistency, verify a paper's
  reproducibility, or find mismatches between a paper and its implementation.
metadata:
  claude-command:
    name: audit
    argument-hint: <paper-or-repo>
---

# Paper / Code Audit

<!-- Adapted from companion-inc/feynman, skills/paper-code-audit/SKILL.md at
commit 8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for the audit report and claim comparisons.

Derive a short slug from the paper or repository. Use lowercase words separated
by hyphens, omit filler words, and keep at most five words.

Write `docs/.plans/<slug>.md` before the audit. Identify the paper, repository,
claims, and code paths to inspect. Briefly summarize the plan and continue
unless the user asked to review it first.

Read the implementation, tests, configuration, and relevant history. Do not
infer behavior from the README alone. Compare the paper's methods, defaults,
metrics, and data handling with the code. Report missing implementations,
ambiguous defaults, mismatches, unstated seeds or RNG kinds, and reproduction
risks. Use repository tools such as Git or `gh` when local inspection requires
them.

For a broad audit, delegate evidence gathering to the `researcher` and source
and citation checks to the `verifier` through the runtime's available agent
mechanism. Keep ownership and expected artifact paths explicit in each brief.

Save exactly one report to `docs/<slug>-audit.md`. End it with a `Sources`
section containing direct paper and repository URLs.

Agents used: `researcher`, `verifier` (for non-trivial audits).
Output: `docs/<slug>-audit.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
