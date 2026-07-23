---
name: watch
description: >
  Create a research watch baseline and optionally schedule follow-up checks. Use
  when the user asks to monitor a field, track new papers, watch for updates, or
  set up alerts on a research area.
---

# Watch

Run the `/watch` workflow. It plans what to monitor and what counts as a
meaningful change, runs a baseline sweep, and records the current state.

Claude Code has no in-session scheduler, so a recurring watch runs through the
`loop` skill (`/loop <interval> /watch <topic>`) or a cron entry. The baseline
artifact records the exact refresh command and notes `Scheduling: manual`.

Output: `outputs/<slug>-baseline.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `${CLAUDE_PLUGIN_ROOT}/ATTRIBUTION.md`.*
