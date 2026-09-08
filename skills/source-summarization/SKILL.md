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

Use `writing-style` for the summary.

Read [workflow.md](references/workflow.md) and follow its bounded read,
checkpoint, coverage, and single source citation rules.

Output: `docs/<slug>-summary.md`.
