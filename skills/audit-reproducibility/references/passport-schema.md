# Reproducibility Passport Schema

<!-- Adapted from pedrohcgs/claude-code-my-workflow,
templates/passport-template.yaml at commit
cb38a277840fd0ee0c0a6ea61ddc2bceb940efc6 (MIT, Copyright 2026 Pedro H. C.
Sant'Anna). The Material Passport concept is credited upstream to
Imbad0202/academic-research-skills. See ATTRIBUTION.md. -->

A passport is a YAML record at
`quality_reports/passports/<paper-slug>.yaml`. Copy
`templates/passport.yaml` when the Waterology source assets are available, or
create the same structure from this reference.

## Paper record

`paper` contains:

- `slug`: stable lowercase identifier used in report filenames.
- `title`: manuscript title.
- `manuscript`: project relative manuscript path.
- `branch`: branch on which the record is current.
- `last_audit`: RFC 3339 timestamp or `null`.
- `last_audit_by`: auditor identifier or `null`.

## Claim record

Every item in `claims` represents one numeric claim and contains:

- `id`: stable identifier that is not reused.
- `claim`: the reported text or concise numeric statement.
- `location`: manuscript path plus a table, figure, section, or line locator.
- `kind`: `point_estimate`, `standard_error`, `p_value`, `sample_size`,
  `percentage`, or another explicit kind.
- `reported`: structured reported values needed for comparison.
- `source_file` and `source_line`: the script location that produces the value.
- `output_file` and `output_field`: the produced artifact and exact lookup.
- `tolerance`: one or more claim-specific thresholds. Omit a threshold only
  when the skill default applies.
- `last_verified_on`: RFC 3339 timestamp or `null`.
- `last_verified_by`: auditor identifier or `null`.
- `status`: `PASS`, `FAIL`, `EXPLAINED`, `STALE`, or `UNVERIFIED`.
- `notes`: discrepancy evidence and any named alternative specification.

Keep paths project relative and use forward slashes. The provenance quadruple
`source_file`, `source_line`, `output_file`, and `output_field` is required.
An output file may be `.rds`, `.tex`, `.csv`, `.parquet`, `.dat`, fixed-width
text, `.log`, or `.json`.

## Default tolerances

- `sample_size: exact`
- `point_estimate: 0.01`, using a strict absolute difference
- `standard_error: 0.05`, using a strict absolute difference
- `p_value: same_significance_level`
- `percentage_points: 0.1`

For an inequality such as `p < 0.01`, the computed p-value must satisfy the
same inequality. Otherwise compare conventional bands bounded by 0.001, 0.01,
0.05, and 0.10. Record a different scientific threshold explicitly rather
than inferring it.

## Status transitions

- New claims begin `UNVERIFIED`.
- A tracked source or output modification changes the claim to `STALE`.
- An audit changes a matched claim to `PASS`, `FAIL`, or `EXPLAINED`.
- A claim without a confident match is reported as `UNMATCHED` but remains
  `UNVERIFIED` in the passport until a provenance match is supplied.

Only an audit updates verification timestamps. The reconciliation hook may
mark a claim `STALE`, but it does not claim that the new output is correct.
Never remove a claim automatically.
