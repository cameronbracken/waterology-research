---
name: source-summarization
description: >
  Summarize a paper, report, README, PDF, or other long research source with a
  bounded read that keeps large content on disk. Use when the user asks for a
  source summary or when another workflow needs a compact view of a long source.
metadata:
  claude-command:
    name: summarize
    argument-hint: <source> [--window-size <chars>] [--overlap <chars>] [--tier1-threshold <chars>] [--tier2-threshold <chars>]
---

# Source Summarization

<!-- Adapted from companion-inc/feynman, prompts/summarize.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for the summary.

Read [workflow.md](references/workflow.md) and follow its bounded read,
checkpoint, coverage, and single source citation rules.

Output: `docs/<slug>-summary.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See
`ATTRIBUTION.md`.*
