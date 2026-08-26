# Constraint: computed prose results are imported

**Check:** `no-hardcoded-results.py`
**Applies to:** `.tex` and `.qmd` documents

The scanner flags prose lines containing recognizable computed result forms:
percentages, p-values, and reported sample sizes. Fenced code, LaTeX comments,
input statements, Quarto front matter, and width or height percentages inside
image attributes, HTML layout markup, or `\includegraphics` are ignored. Use
generated inputs or inline computations.

Add `waterology: allow-hardcoded-result` on a line for metadata, an
illustrative value, or another reviewed exception. The scanner is a narrow
guard, not proof that every stale value was detected.

Adapted from `flonat/claude-research`, `rules/no-hardcoded-results.md` at commit
`e7007d0b1e465ef96de7338599ca04079e83a972` (MIT, Copyright 2026 Florian
Burnat).
