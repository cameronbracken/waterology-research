---
name: myst-to-quarto
description: >
  Convert a MyST Markdown document to Quarto syntax, including citations,
  callouts, figures, references, and executable code fences. Use when moving a
  MyST article, note, or tutorial into a Quarto project.
metadata:
  claude-command:
    name: myst-to-quarto
    argument-hint: <input.md> [output.qmd]
---

# MyST to Quarto

<!-- Adapted from the MyST to Quarto converter planned from
flonat/claude-research at commit e7007d0b1e465ef96de7338599ca04079e83a972
(MIT, Copyright 2026 Florian Burnat). The current pinned tree no longer contains
the original script, so this implementation follows the recorded Waterology
roadmap contract without copying unavailable code. See ATTRIBUTION.md. -->

Use the included converter for a deterministic first pass:

Resolve the directory containing this `SKILL.md`, then run:

```bash
python3 <skill-directory>/scripts/myst_to_quarto.py input.md output.qmd
```

The script converts MyST citation roles, cross references, note or warning
directives, figure directives, and executable language fences. It preserves
front matter and ordinary Markdown.

After conversion:

1. Read the source and output side by side. Record unsupported directives.
2. Confirm every citation key exists in the selected bibliography.
3. Confirm figure paths, identifiers, captions, alt text, and cross references.
4. Add Quarto format settings through project conventions. For standalone HTML, use embedded resources and the declared light and dark themes.
5. Render in the project environment and inspect the output. Do not call conversion complete from text replacement alone.

The converter never deletes the source. Refuse an output path equal to the
input path. Existing output requires `--force`.
