---
name: audit-reproducibility
description: >
  Audit numeric claims in manuscripts against produced R, Python, Fortran, and
  text outputs. Use before submission, after analysis changes, or when a
  reproducibility passport needs to be created or refreshed.
metadata:
  claude-command:
    name: audit-reproducibility
    argument-hint: <manuscript> [output path] [passport]
---

# Audit Reproducibility

<!-- Adapted from pedrohcgs/claude-code-my-workflow,
.claude/skills/audit-reproducibility/SKILL.md at commit
cb38a277840fd0ee0c0a6ea61ddc2bceb940efc6 (MIT, Copyright 2026 Pedro H. C.
Sant'Anna). The Material Passport concept is credited upstream to
Imbad0202/academic-research-skills. See ATTRIBUTION.md. -->

Use `writing-style` for the audit report. Read
[references/passport-schema.md](references/passport-schema.md) before creating
or updating a passport.

Compare numeric claims in a manuscript with the current analysis outputs. A
mismatch is not automatically a failure. The manuscript is not the oracle.
Treat the computed value as a challenger, not as ground truth, and identify
which artifact needs correction through evidence.

## Inputs and boundaries

Require a manuscript path. Accept one or more output files or directories and
an optional passport at `quality_reports/passports/<paper-slug>.yaml`. If the
output location is omitted, discover plausible project output directories and
show the selected scope before auditing.

The audit reads existing outputs. It does not silently run an analysis,
replace a manuscript value, or choose between conflicting specifications. If
current outputs are missing and a rerun is authorized, launch a long command in
the background, preserve its log, and poll it at short intervals. Do not assume
that a runtime provides a dedicated monitoring tool.

## Audit workflow

### 1. Establish the contract

- Read project guidance and any recorded tolerance overrides.
- Confirm that the manuscript, output scope, and optional passport exist.
- Record output modification times and available environment captures.
- Mark missing data, unreadable formats, and unavailable environments as
  limitations. Do not turn absent evidence into a pass.

### 2. Extract manuscript claims

Find point estimates with standard errors or confidence intervals, table
cells, counts, sample sizes, percentages, summary statistics, and p-values.
Record a stable claim identifier, manuscript location, kind, reported value,
uncertainty, and surrounding context. Save the extraction to
`quality_reports/reproducibility-claims-<paper-slug>.json` so it can be
inspected separately from the matching step.

### 3. Extract produced results

Use this priority when more than one representation exists:

1. `.rds`, with a precise R lookup.
2. `.tex`, using row and column labels rather than cell position alone.
3. `.csv` or `.parquet`, using named fields.
4. `.dat`, fixed-width text, or `.log` from Fortran and simulation programs.
5. `.json`, using a complete field path.

For each result, record the output path, lookup field, value, uncertainty, and
the source script and line when known. Preserve raw output rather than copying
untraceable values into the report.

### 4. Match claims to results

Prefer explicit passport fields and mechanical manuscript inputs. Otherwise
compare labels, table context, units, and nearby descriptions. Magnitude can
help rank candidates but cannot establish identity by itself.

Assign a confidence from 0 to 1 and explain ambiguous matches. A confidence
below 0.7 is `UNMATCHED`; it never passes and cannot be downgraded to
`EXPLAINED`.

### 5. Apply tolerances and dispositions

Use a claim's override when present. Otherwise apply:

| Claim kind | Default tolerance |
| --- | --- |
| Integer or sample size | Exact |
| Point estimate | Absolute difference `< 0.01` |
| Standard error | Absolute difference `< 0.05` |
| P-value | Same reported significance level |
| Percentage | Absolute difference `<= 0.1` percentage points |

Assign one audit disposition:

- `PASS`: the matched result is within tolerance.
- `FAIL`: it is outside tolerance and no concrete alternative is recorded.
  This blocks the audit.
- `EXPLAINED`: it is outside tolerance, but `notes` names the exact alternative
  specification that accounts for the difference. Surface it without blocking.
- `UNMATCHED`: no result was matched with at least 0.7 confidence.

`STALE` and `UNVERIFIED` are lifecycle states. `STALE` means a tracked source
or output changed after verification and must be audited again. `UNVERIFIED`
means the claim has never completed this audit.

Downgrade `FAIL` to `EXPLAINED` only for a specific named alternative tied to
that claim. Blank notes, `unclear`, `looks fine`, rounding without a quantified
comparison, and general assurances do not qualify. Record whether the eventual
resolution was `PAPER-CORRECTED`, `CODE-CORRECTED`, or
`DEFENSIBLE-ALTERNATIVE`.

### 6. Report and update the passport

Write `quality_reports/reproducibility-audit-<paper-slug>.md` with:

- manuscript and output provenance;
- the tolerance source and any overrides;
- counts for every disposition and lifecycle state;
- reported value, computed value, difference, tolerance, match confidence,
  and source fields for each claim;
- limitations, environment evidence, and concrete next actions.

In passport mode, update each audited claim's status, `last_verified_on`, and
`last_verified_by`. Update `paper.last_audit`. Do not delete claims that
disappear from the manuscript. Leave them `STALE` for a person to retract or
relocate. Warn about manuscript claims that have no passport entry.

The overall audit fails when any claim is `FAIL`. `EXPLAINED` remains visible
but does not fail. Report `UNMATCHED`, `STALE`, and `UNVERIFIED` as incomplete
evidence and do not describe the manuscript as fully verified while any remain.

Output: claim extraction, updated passport when present, and reproducibility
audit report.

---
*Adapted from pedrohcgs/claude-code-my-workflow (MIT, Copyright 2026 Pedro H.
C. Sant'Anna). Material Passport concept credited to
Imbad0202/academic-research-skills. See `ATTRIBUTION.md`.*
