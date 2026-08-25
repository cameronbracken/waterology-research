---
description: Compare a paper's claims against its public codebase and identify mismatches, omissions, and reproducibility risks.
argument-hint: <paper-or-repo>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Audit the paper and codebase for: $ARGUMENTS

Tools: `WebSearch`/`WebFetch` for the paper and repo; `gh` and `Bash` to clone and inspect code; the `Task` tool to launch the `researcher` (evidence) and `verifier` (sources and citations) agents when the audit is non-trivial.

Derive a short slug from the audit target (lowercase, hyphens, no filler words, at most 5 words). Use it for all files in this run.

Requirements:
- Before starting, outline the audit plan: which paper, which repo, which claims to check. Write it to `docs/.plans/<slug>.md`. Summarize briefly and continue immediately unless the user asked to review the plan first.
- Compare claimed methods, defaults, metrics, and data handling against the actual code. Read the code — do not infer behavior from the README alone.
- Call out missing code, mismatches, ambiguous defaults, unstated seeds or RNG kinds, and reproduction risks.
- Save exactly one audit artifact to `docs/<slug>-audit.md`, ending with a `Sources` section containing paper and repository URLs.
