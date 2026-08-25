---
name: watch
description: >
  Create a research watch baseline and optionally schedule follow-up checks. Use
  when the user asks to monitor a field, track new papers, watch for updates, or
  set up alerts on a research area.
metadata:
  claude-command:
    name: watch
    argument-hint: <topic>
---

# Watch

<!-- Adapted from companion-inc/feynman, skills/watch/SKILL.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for the baseline, update summaries, and alerts.

Derive a short slug from the watch topic. Use lowercase words separated by
hyphens, omit filler words, and keep at most five words.

Write `docs/.plans/<slug>.md` before searching. Define the topic boundary,
signals to monitor, meaningful change criteria, sources, and a sensible check
frequency. Briefly summarize the plan and continue unless the user asked to
review it first.

Run a source grounded baseline sweep and record the current state. Save exactly
one baseline to `docs/<slug>-baseline.md`. Include the date, search scope,
refresh instructions, meaningful change criteria, and `Scheduling: manual`.
End with a `Sources` section containing direct URLs for every source used.

Create a recurring schedule only when the user explicitly asks for one. Use the
current runtime's scheduling capability when available. Otherwise provide a
local cron or task scheduler recipe and keep `Scheduling: manual`. Do not claim
that monitoring is active until the schedule exists and its next run is known.

Output: `docs/<slug>-baseline.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
