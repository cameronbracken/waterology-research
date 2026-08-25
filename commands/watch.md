---
description: Create a research watch baseline, with an optional scheduled follow-up.
argument-hint: <topic>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Create a research watch baseline for: $ARGUMENTS

Tools: `WebSearch`/`WebFetch` and paper search for the baseline sweep.

Derive a short slug from the watch topic (lowercase, hyphens, no filler words, at most 5 words). Use it for all files in this run.

Requirements:
- Before starting, outline the watch plan: what to monitor, which signals matter, what counts as a meaningful change, and a sensible check frequency. Write it to `docs/.plans/<slug>.md`. Summarize briefly and continue immediately unless the user asked to review the plan first.
- Run a baseline sweep of the topic and record the current state.
- Claude Code has no built-in in-session scheduler. To make the watch recurring, use the `loop` skill (`/loop <interval> /watch <topic>`) or a cron entry. Record the exact command the user can run to refresh the watch, and note `Scheduling: manual` in the baseline artifact.
- Save exactly one baseline artifact to `docs/<slug>-baseline.md`, ending with a `Sources` section of direct URLs for every source used.
