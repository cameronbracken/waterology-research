# Choosing artifact skills

Load only the skill matching the requested deliverable, and add interaction only when requested:

| Request | Skill | Bundled resources / verifiers |
| --- | --- | --- |
| Plot, chart, map, multi-panel figure, or interactive chart | [figures](../skills/figures/SKILL.md) | `references/visual-design.md`, `references/plotly-text-layout.md`, `scripts/check_plotly_layout.py`, `scripts/safe_ggplotly.R` |
| Flowchart, architecture schematic, or pipeline diagram | [diagrams](../skills/diagrams/SKILL.md) | `resources/flowchart-tikz.sty`, `scripts/check_tikz_svg.py`, `references/integration-patterns.md` |
| Technical, analysis, summary, or benchmark report | [reports](../skills/reports/SKILL.md) | `reports/<topic>-<YYYY-MM-DD>/` default bundle, `resources/earth_tone_plot_template.R`, `scripts/verify_report_bundle.py`, and `references/interactive-reports.md` for Quarto HTML |
| LaTeX or Beamer PDF build | [compile-latex](../skills/compile-latex/SKILL.md) | `templates/latexmkrc`, `scripts/overfull_boxes.py` |
| Quarto blog post and WebP media | [publish-blog-post](../skills/publish-blog-post/SKILL.md) | `references/blog-defaults.md` |
| Prose editing, READMEs, notes, or Markdown delivery | [writing-style](../skills/writing-style/SKILL.md) | `references/scientific-prose.md` |

Coding, environment, and research verification tasks map directly to:

- `project-conventions` and `r-code-style` for language, format, and `light` vs `strict` reproducibility defaults (including `scripts/myst_to_quarto.py`).
- `setup-environment` for Pixi, uv, rv, system R on macOS, direnv, and `strict` environment snapshots.
- `literature-review` and `bib-validate` for multi-provider search, Zotero sync, and BibTeX/DOI verification.
- `simulation-study`, `research-review`, and `audit-reproducibility` for Monte Carlo studies, peer critiques, claim-to-output audits, and `pipeline.md` manifests.
- `autoresearch` and `sol-pi` for bounded Git/benchmark iteration loops and SoL-Pi delegation.
