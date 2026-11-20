---
name: waterology-audit-reproducibility
description: >
  Audit numeric manuscript claims against produced R, Python, and Fortran
  outputs, check paper-to-code method parity, or map a project's script-to-figure
  pipeline manifest.
metadata:
  claude-command:
    name: audit-reproducibility
    argument-hint: <manuscript or repo path> [outputs path]
---

<!-- Generated from skills/audit-reproducibility/SKILL.md. Do not edit. -->

# Audit Reproducibility, Paper-Code Parity, and Pipelines

Use [writing-style](../waterology-writing-style/SKILL.md) for the audit report.

- For **script-to-output pipeline mapping** (`pipeline.md` and `run-all.sh`), read [pipeline-manifest.md](references/pipeline-manifest.md).
- For **`strict` mode reproducibility passports** (`quality_reports/passports/<slug>.yaml`), read [passport-schema.md](references/passport-schema.md).

## 1. Numeric claim-to-output audit

Compare every quantitative claim in a manuscript or report (point estimates, intervals/SEs, sample sizes, percentages, table cells, p-values) against produced artifacts without assuming either the prose or code is automatically right:

1. **Extract produced values** in priority order: `.rds` -> labeled `.tex` fragments -> `.csv`/`.parquet` -> Fortran/model `.dat`/`.log` -> `.json`/`.yaml`, recording exact file, field, and producing script:line.
2. **Apply tolerances** (unless overridden): exact for integers/counts, `< 0.01` for point estimates, `< 0.05` for standard errors, `<= 0.1` percentage points for percentages, and matching significance band for p-values.
3. **Assign dispositions:**
   - `PASS`: matched (>= 0.7 confidence) and within tolerance.
   - `FAIL`: outside tolerance with no verified alternative specification (blocks audit).
   - `EXPLAINED`: outside tolerance due to a named, verified specification difference.
   - `UNMATCHED`: no confident output match found (incomplete evidence, never treated as `PASS`).

## 2. Paper-to-code implementation audit

When comparing a paper (internal or external) against a codebase, inspect source code, configs, and tests directly rather than trusting the README:

- Check equations, loss/objective terms, boundary conditions, hyperparameter defaults, data splits/filtering, units, and RNG seeds against the paper's methods section.
- Flag missing scripts, silent default overrides, hardcoded paths, or unseeded stochastic steps.

## Output

In `light` mode, write one concise report (`quality_reports/reproducibility-audit-<slug>.md` or `docs/<slug>-audit.md`) listing summary counts, a claim/method comparison table with exact file:line locators, and prioritized fixes (`PAPER-CORRECTED`, `CODE-CORRECTED`, or `DEFENSIBLE-ALTERNATIVE`). Update a YAML passport only in `strict` mode or when requested.
