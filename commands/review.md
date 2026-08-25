---
description: Run an internal research critique with likely objections, severity, and a concrete revision plan.
argument-hint: <artifact>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Review this research artifact: $ARGUMENTS

This is an execution request, not a request to explain the workflow. Carry it out with tools and durable files. Do not answer by describing the protocol or stopping after a plan. Do not ask for confirmation — summarize the plan briefly and continue unless the user explicitly asked to review the plan first.

Tools: `WebFetch` to fetch a URL or arXiv source; `Read` for local files; the `Task` tool to launch the `researcher` and `reviewer` agents when the artifact is large enough to benefit.

Derive a short slug from the artifact name (lowercase, hyphens, no filler words, at most 5 words). Use it for all files in this run.

Required artifacts:
- Plan: `docs/.plans/<slug>-review-plan.md`
- Evidence notes: `docs/.drafts/<slug>-review-evidence.md`
- Final review: `docs/<slug>-review.md`

Workflow:
1. Create `docs/.plans`, `docs/.drafts`, and `docs`.
2. Write the plan with: artifact identifier and source type (arXiv ID, URL, local file, PDF, Markdown); review criteria (novelty, empirical rigor, baselines, reproducibility, claims validity, figures/tables, metrics, related work, writing quality); and the verification checks needed for claims, figures, reported metrics, and data/code availability.
3. Continue immediately — do not end after planning.
4. Inspect the artifact: read local files directly; for PDFs use `pdftotext` or an available parser (if parsing fails, record it and still produce a blocked or partial review); for arXiv IDs or URLs, fetch and record the URL; inspect linked code, data, or citations when they materially affect the review.
5. Write evidence notes before the final review: quoted or paraphrased claims, observed methods, reported metrics, baseline comparisons, reproducibility facts, and every inspected source path or URL.
6. Use the `researcher` and `reviewer` subagents only if the artifact is large enough to benefit; otherwise do the review directly. Never merely say a subagent was spawned — either launch it via `Task` or continue yourself.
7. Write exactly one final review to `docs/<slug>-review.md` with: Summary Assessment, Strengths, Critical Issues, Major Issues, Minor Issues, Reproducibility and Verification, Inline Annotations tied to sections/claims/figures/tables, Recommendation, Sources.
8. If the artifact cannot be parsed or critical evidence is unavailable, still write the review. Mark affected sections `Verification: BLOCKED`, explain what failed, and distinguish blocked checks from real weaknesses.
9. Before responding, verify on disk that `docs/<slug>-review.md` exists; if not, create it as a blocked review artifact with the failure reason.

Never end with planning-only chat. Never ask what to do next. Never claim the review is complete unless the review file exists.
