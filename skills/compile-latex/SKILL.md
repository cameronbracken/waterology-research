---
name: compile-latex
description: >
  Compile and verify a LaTeX or Beamer document with latexmk, including XeLaTeX,
  bibliography passes, cross references, and box diagnostics. Use to build a
  PDF or diagnose a LaTeX render failure.
metadata:
  claude-command:
    name: compile-latex
    argument-hint: <main.tex>
---

# Compile LaTeX

Use the project build command when one exists. Otherwise resolve the directory
containing this `SKILL.md`, copy its [bundled latexmk configuration](templates/latexmkrc)
to the project's `.latexmkrc`, review it, and run:

```bash
latexmk -xelatex -bibtex -interaction=nonstopmode -halt-on-error main.tex
```

`latexmk` repeats XeLaTeX and BibTeX until citations and cross references
stabilize. This replaces a hand maintained 3-pass sequence while preserving
the required passes.

## Verification

1. Read the complete command output and exit status.
2. Check the `.log` for undefined citations, undefined references, missing files, font substitutions, and rerun requests.
3. Resolve this skill's directory and run `python3 <skill-directory>/scripts/overfull_boxes.py <build-directory>`. It bundles the `overfull-boxes` constraint logic and parses box specific messages that a generic `Warning` search misses.
4. Confirm the PDF exists, has a plausible page count, and was modified by this build.
5. Render pages to images and inspect layout when the artifact will be shared or published.

Report major overflow above 10 pt before minor overflow. Do not silently rewrite
prose to fit a line. Keep build files in the declared output directory. Never
delete source or unrelated output during cleanup.
