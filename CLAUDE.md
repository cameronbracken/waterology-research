# CLAUDE.md

Guidance for Claude Code when working in the **waterology** plugin repo.

## What this is

`waterology` is a lean Claude Code plugin tuned to Cam Bracken's research stack
(R / Python / Fortran / Quarto / LaTeX; hydrology, energy systems, statistical
extremes). It is intentionally small — the opposite of a kitchen-sink bundle.
Pair it with the `superpowers` plugin: superpowers handles generic engineering
discipline, `waterology` adds research-specific conventions and reproducibility
checks superpowers can't know.

## Design: conventions vs constraints

This is the organizing principle (adapted from edwinhu/workflows). Decide where
new material goes with one litmus test: **can you write a script that returns
pass/fail?**

- **Yes → a constraint.** A paired `constraints/<name>.md` (the rule) +
  `constraints/<name>.py` (a standalone check: target paths as argv, print
  findings, exit `0` pass / `1` fail / `2` internal error). `check-all.py`
  auto-discovers it — adding the two files is the whole wiring step.
- **No, it needs reading and judgment → a convention.** A `rules/<name>.md`
  entry with `paths:` frontmatter scoping it to file types. Conventions always
  defer to a file's existing local style when they conflict.

`skills/project-conventions/SKILL.md` is the entry point: it routes to the right
rule for the file being edited and runs the constraints before work is "done."

## Working here

- **Run the checks** after editing: `python3 constraints/check-all.py <paths>`.
  The repo must self-pass clean (`python3 constraints/check-all.py .`).
- **Escape hatches** (genuine exceptions only): `# waterology: allow-abs-path`,
  `# waterology: allow-unseeded` (use `!` for Fortran).
- **Attribution is mandatory.** Anything adapted from an upstream project gets a
  one-line credit at the top of the file *and* an entry in `ATTRIBUTION.md`. The
  three sources are MIT; edwinhu/workflows asserts MIT in its README but ships
  no LICENSE file — cite it as "MIT, per README."
- **Style:** Python is plain `python3`, format with `ruff`. Match the R
  conventions the plugin itself preaches (`rules/r-conventions.md`) in any R
  examples. Keep files small and focused.
- **Privacy:** this repo is local-only and private until it is more complete. Do
  not create a remote or push without being asked.

## Roadmap

Next slices are documented in [ROADMAP.md](ROADMAP.md) with enough detail
(source files, what to strip, what to add) to resume cold. Update it as slices
land.
