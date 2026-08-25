---
name: session-log
description: >
  Write a durable session log capturing completed work, findings, open
  questions, and next steps. Use when the user asks to log progress, save
  session notes, write up what was done, or create a research diary entry.
metadata:
  claude-command:
    name: log
    argument-hint: (none)
---

# Session Log

<!-- Adapted from companion-inc/feynman, skills/session-log/SKILL.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for the durable log.

Write a session log for the current work. Capture completed work, the strongest
findings and decisions, open questions, unresolved risks, and concrete next
steps. Reference important artifacts under `notes/`, `docs/`, `experiments/`,
or `papers/`. Include direct URLs when external claims affect the record.

Save the log to `notes/<date>-session.md`, using the current date and a short
topic suffix when it helps distinguish multiple logs from the same day.

Output: `notes/<date>-session.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
