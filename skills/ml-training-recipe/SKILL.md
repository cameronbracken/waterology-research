---
name: ml-training-recipe
description: >
  Find implementable ML training recipes from papers, datasets, docs, and code.
  Use when the user wants to fine-tune, train, reproduce, or choose a practical
  ML method, dataset, hyperparameter setup, or benchmark, including energy,
  climate, and hydrology forecasting models.
metadata:
  claude-command:
    name: recipe
    argument-hint: <task-or-paper>
---

# ML Training Recipe

<!-- Adapted from companion-inc/feynman, skills/ml-training-recipe/SKILL.md at
commit 8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for the recipe, comparisons, and recommendation.

Derive a short slug from the task. Create these artifacts:

- Plan: `docs/.plans/<slug>-recipe.md`
- Research notes: `docs/.drafts/<slug>-recipe-research.md`
- Final brief: `docs/<slug>-recipe.md`
- Provenance: `docs/<slug>-recipe.provenance.md`

Plan the target behavior or benchmark, feasibility limits, source types, and a
small task ledger. Continue after recording the plan unless the user asked to
review it first.

Start from evidence of results, not example scripts. For a broad sweep,
delegate paper and code research to the `researcher` through the runtime's
available agent mechanism. Prefer sources that report a concrete metric on a
named dataset, especially for streamflow, load, or weather forecasting.

For each candidate, link the reported result to its paper or report, dataset,
training method, hyperparameters, compute assumptions, metric, implementation
path, and current documentation. Inspect working code or official docs and
record exact file paths, functions, classes, and command patterns where they
matter.

Check each dataset's availability, schema, splits, columns, format, access, and
license when possible. Mark unchecked availability or schema `unverified`.
Never imply a dataset is usable solely because a paper names it.

Write the research notes first. Promote them into a concise brief containing:

- One recommended recipe and the reason to try it first.
- A ranked table of sources, results, datasets, methods, hyperparameters,
  compute, code or docs, and verification status.
- Dataset notes and a minimal implementation plan for the leading recipe.
- Known gaps such as missing code, inaccessible data, unclear settings, or a
  benchmark mismatch.
- Direct URLs for every paper, repository, dataset, and documentation page.

Verify source URLs plus dataset and code availability for the leading recipe.
Use `verified`, `unverified`, `blocked`, and `inferred` precisely. Do not call a
method state of the art, replicated, or production ready without evidence.
Record consulted, accepted, and rejected sources plus verification status in
the provenance file.

Agents used: `researcher`.
Output: `docs/<slug>-recipe.md` with `docs/<slug>-recipe.provenance.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
