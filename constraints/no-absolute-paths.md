# Constraint: no machine-specific absolute paths

**Type:** constraint (deterministic, scriptable pass/fail)
**Check:** `no-absolute-paths.py`
**Applies to:** `.R .r .py .f90 .f .F90 .f95 .qmd .Rmd .jl .do` source files

## Rule

Source code must not hard-code machine-specific absolute paths. A path that
points at one person's machine breaks the moment anyone else (or a cluster
node, or a clean checkout) runs the code. Paths must be project-root-relative,
constructed at runtime (`here::here()`, `file.path()`, `os.path.join`,
environment variables, config), or read from a settings block.

Flagged patterns:

- POSIX home / user paths: `/Users/...`, `/home/...`
- Tilde expansion baked into source: `~/...`
- Windows drive paths: `C:\...`, `D:\...`
- Cloud-storage roots: `.../CloudStorage/...`, `.../Dropbox/...`, `.../OneDrive/...`

## Why this is a constraint, not a convention

You can write a script that returns pass/fail by grepping for these patterns,
so it is enforced mechanically rather than left to judgment.

## Escape hatch

Append `# waterology: allow-abs-path` (or `! waterology: allow-abs-path` in
Fortran) to a line that legitimately needs an absolute path — for example a
documented, immutable shared data mount. The check skips flagged lines.

---
*Constraint pattern adapted from edwinhu/workflows (MIT, per README).
Path-hygiene checklist informed by flonat/claude-research (MIT, © 2026 Florian Burnat).*
