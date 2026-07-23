---
description: Find ranked, implementable ML training recipes backed by papers, datasets, docs, and code.
argument-hint: <task-or-paper>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Find implementable ML training recipes for: $ARGUMENTS

This is an execution request, not a request to explain the workflow. Continue immediately.

Tools: `WebSearch`/`WebFetch` and paper search; `gh` and `Bash` to inspect datasets and code; the `Task` tool to launch the `researcher` agent for broad sweeps. Check a dataset's availability and schema by reading its card, docs, or repo — do not imply a dataset is usable without checking.

Derive a short slug from the task (lowercase, hyphens, no filler words, at most 5 words). Use it for all files in this run.

## Required artifacts
- `outputs/.plans/<slug>-recipe.md`
- `outputs/.drafts/<slug>-recipe-research.md`
- `outputs/<slug>-recipe.md`
- `outputs/<slug>-recipe.provenance.md`

## Workflow

1. **Plan** — Write `outputs/.plans/<slug>-recipe.md` with the target task, benchmark or desired behavior, candidate source types, feasibility constraints, and a task ledger. Continue automatically after writing it.
2. **Research** — Use the `researcher` subagent for a broad paper/code sweep; for narrow tasks gather directly. Start from evidence of results, not from example scripts alone. For energy, climate, or hydrology ML (streamflow, load, or weather forecasting), prefer sources reporting a concrete skill metric on a named dataset.
3. **Recipe extraction** — For each promising approach, link the observed result to the exact recipe: paper or report, benchmark/result, dataset, training method, key hyperparameters, compute assumptions, implementation code path, current docs.
4. **Dataset validation** — Check each dataset's availability, splits/columns, and whether the format matches the method. Mark unchecked schema or availability `unverified`; do not imply it is usable.
5. **Implementation grounding** — Find working code or official docs for the chosen path. Prefer current docs and actively maintained repos. Record exact file paths, function and class names, and command patterns.
6. **Synthesis** — Write `outputs/.drafts/<slug>-recipe-research.md` first, then promote a concise ranked brief to `outputs/<slug>-recipe.md`.
7. **Verification** — For the top-ranked recipe, verify the key source URLs and the dataset/code availability before delivery. Keep unverifiable items only with an explicit `blocked` or `unverified` label.
8. **Provenance** — Write `outputs/<slug>-recipe.provenance.md` with date, sources consulted, sources accepted/rejected, verification status, and artifact paths.

## Required final shape

The final brief includes:
- **Recommendation:** the one recipe to try first and why.
- **Ranked recipe table:** one row per candidate with paper/source, result, dataset, method, hyperparameters, compute, code/docs, and verification status.
- **Dataset notes:** schema, split, size, license/access when checked.
- **Implementation plan:** minimal steps to run the top recipe.
- **Known gaps:** missing code, inaccessible data, unclear hyperparameters, or benchmark mismatch.
- **Sources:** URLs for every paper, repo, dataset, and doc page used.

Do not claim a method is state of the art, replicated, or production-ready unless the checks prove it. Use `verified`, `unverified`, `blocked`, and `inferred` precisely.
