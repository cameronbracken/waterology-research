---
name: bib-validate
description: >
  Validate citation keys and bibliography metadata, suggest likely key typos,
  and optionally verify DOI or title metadata through OpenAlex and Crossref.
  Use before rendering or releasing a Quarto or LaTeX document.
metadata:
  claude-command:
    name: bib-validate
    argument-hint: <document paths> <bib path> [--verify-doi] [--fix]
---

# Bibliography Validation

<!-- Adapted from flonat/claude-research at commit
e7007d0b1e465ef96de7338599ca04079e83a972 (MIT, Copyright 2026 Florian
Burnat), especially rules/doi-verification.md and the bibliography skills.
The portable validator and free OpenAlex plus Crossref path are Waterology
adaptations. See ATTRIBUTION.md. -->

Validate local references before rendering a paper. The included script uses
only the Python standard library:

Resolve the directory containing this `SKILL.md`, then run:

```bash
python3 <skill-directory>/scripts/validate_bib.py paper.qmd references.bib
```

Add `--verify-doi` to query OpenAlex for present DOIs and Crossref for entries
without one. Add `--fix` to correct only unambiguous citation key typos at edit
distance 1. The script never rewrites bibliography metadata automatically.

## Local checks

1. Extract citation keys from `.tex`, `.qmd`, and Markdown sources.
2. Compare them with keys declared in each `.bib` file.
3. Report an edit distance 1 candidate as a likely typo and distance 2 as a possible typo.
4. Treat an ambiguous match as unresolved. Do not guess.
5. Report uncited bibliography entries separately. They do not fail the check.

## DOI and fabrication checks

With `--verify-doi`, apply this evidence order:

- DOI present and OpenAlex resolves it: PASS.
- DOI present but OpenAlex returns not found: FAIL because the DOI may be wrong or fabricated.
- DOI absent and the closest Crossref title has similarity at least 0.95: WARN and show the candidate DOI. Do not insert it.
- DOI absent and no credible match is found: WARN HIGH and retain the entry as unverified.

For each Crossref candidate, report the fabrication matrix across normalized
title, first author, and year. A title match alone does not prove the record is
the intended work. A network failure is `UNVERIFIED`, not FAIL.

## Fix boundary

`--fix` changes a source citation only when exactly one bibliography key is at
edit distance 1. It preserves the `.bib` file and makes no DOI or metadata
change. Review the diff and rerun without `--fix` before accepting the result.

## Report

Return PASS only when all cited keys exist and every requested DOI check
passes. List likely and possible key typos, unused entries, DOI dispositions,
network limitations, changed files, and the exact verification command.
