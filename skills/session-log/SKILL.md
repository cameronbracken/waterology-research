---
name: session-log
description: >
  Write a durable session log capturing completed work, findings, open
  questions, and next steps. Use when the user asks to log progress, save
  session notes, write up what was done, or create a research diary entry.
---

# Session Log

Use `writing-style` for the durable log.

Run the `/log` workflow. It summarizes what was done, captures the strongest
findings and decisions, lists open questions and concrete next steps, references
artifacts written under `notes/`, `outputs/`, `experiments/`, or `papers/`, and
saves a dated Markdown log to `notes/`.

Output: `notes/<date>-session.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
