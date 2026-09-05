---
name: paper-writing
description: >
  Build a targeted results report as a single interactive Quarto HTML file,
  or draft an academic paper from collected evidence. Use when the user says
  "write a report," asks for a technical report, writes up findings, or asks
  for a paper, document, or manuscript.
metadata:
  claude-command:
    name: draft
    argument-hint: <topic>
---

# Paper and Report Writing

<!-- Adapted from companion-inc/feynman, skills/paper-writing/SKILL.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` and its scientific prose layer for the draft and final
edit. Use `project-conventions` for Quarto settings and local research
preferences. Apply `figure-style` to every plot.

Choose _report mode_ when the user says "write a report," "draft a report," or
asks for a technical report. A report is a targeted summary of results from an
analysis or model, gathered with its validation information into one shareable
file. Choose _paper mode_ when the user asks for a paper, document, article, or
manuscript, which calls for academic quality writing throughout. A request
phrased as a report takes precedence over the general paper workflow.

Derive a short topic slug with lowercase hyphenated words, no filler words, and
at most five words. Write `docs/.plans/<slug>.md` before drafting. Include the
title, sections, claims, supplied source material, and verification checks for
critical claims, figures, and calculations. Briefly summarize the plan and
continue unless the user asked to review it first.

Draft only from collected notes and verified sources. For substantial work,
when delegation is available and authorized, give the `writer` the evidence
and output path, then give the resulting draft and sources to the `verifier`.
Keep their work sequential so verification reads the completed draft. Work
directly when delegation is unavailable.

Include a title, summary or abstract, problem statement, methods or synthesis,
evidence, limitations, and conclusion when the material supports those
sections. Use LaTeX math when an equation helps. Never hand-type a computed number.
Import it with an inline code result or a generated fragment tied to the
analysis. If evidence is missing, leave a labeled placeholder or proposed
analysis instead of claiming a result.

Every result, citation, figure, table, and quantitative comparison needs
provenance. Never invent sources, data, or graphics. Before delivery, weaken or
remove claims that exceed their support and remove unsupported numerics.

## Report mode

For archived Waterology runs, start with `waterology compare-runs` and export
selected runs with `waterology report --baseline RUN_ID --destination reports/SLUG`.
Supply the selected run IDs as arguments. The bundle contains Quarto source,
measurement data, figure code and provenance. Regenerate with its `render.py`,
then render and inspect the HTML as described below. Claim-reference integrity
and assessed claim support are separate. Do not describe an unassessed claim as
verified merely because its archive bytes match.

A report collects the results and validation of an existing analysis or model
in one place so the work can be reviewed and shared as a single HTML file.
Interactive graphics are the primary content. Prose exists to explain the
figures and tables, with a brief account of the methods and citations where
they help a reader interpret the results. Keep the text static and explanatory
so a parameterized or automated rerun stays correct without rewriting prose.
Use tables only for summary metrics, never for large listings of raw numbers.

Build a Quarto HTML report. Follow an existing project layout when one exists.
Otherwise use:

```text
reports/<slug>/
|-- report.qmd
|-- references.bib
|-- figures/
`-- scripts/
```

The main source is `reports/<slug>/report.qmd`. Include this standalone HTML
configuration unless the project has an equivalent setting:

```yaml
bibliography: references.bib
format:
  html:
    embed-resources: true
    theme:
      light: flatly
      dark: darkly
```

Reports are often parameterized or automated. When the report will be rerun
for different sites, periods, or model versions, declare Quarto `params` in
the YAML header and read them in code instead of hard coding values.

Use Quarto citation keys and verified bibliography metadata. Prefer scholarly
references. Cite a stable repository or source URL when no formal publication
exists. Run `bib-validate` locally before the final render. Add DOI verification
when network access is available and allowed. Treat an unavailable lookup as
unverified, not as a pass.

Include interactive graphics when supported data can clarify a result. Use
Plotly for ordinary interaction and Bokeh only when richer linked interaction
materially helps. Keep the display clean, use earth tones and colorblind
friendly palettes, and retain units, uncertainty, captions, and source links.
Save the data and code needed to regenerate each graphic. Provide a useful
static or tabular fallback when the report may be printed. Do not add a graphic
for decoration or manufacture example data to fill a gap.

Render with:

```bash
quarto render reports/<slug>/report.qmd --to html
```

Inspect the rendered HTML, not only the source. Confirm citations and the
reference list resolve, interactive controls work, the light and dark themes
remain readable, figures are not clipped, and the output is self contained.
When the report contains Plotly, run the `figure-style` Plotly layout checker
on the rendered HTML. Resolve every finding before visual inspection; then
inspect desktop and narrow layouts because the checker cannot detect every
pixel collision.

After the first successful render, apply `research-review` to the report. Check
claim support, citation coverage, methods, limitations, figure provenance,
interactive behavior, accessibility, and reproducibility. Resolve critical and
major findings that are within scope, then rerun `bib-validate` and `quarto
render`. If an independent reviewer is unavailable, perform the same review
directly and state that limitation.

Deliver the `.qmd`, rendered HTML, bibliography, figure sources, and review
path. Report the exact citation validation and render commands and any blocked
or unverified checks.

## Paper mode

A paper or document requires academic quality writing and referencing:
thorough explanation of methods and results, complete citations, and polished
publication quality figures.

Use Quarto or LaTeX according to the target venue and existing project layout.
For a format neutral draft with no venue requirements, save
`papers/<slug>.md`. Use the same evidence, provenance, citation validation, and
claim review rules as report mode. Interactive graphics are optional for a
paper and do not replace publication figures.

Agents used when available and authorized: `writer`, `verifier`, and `reviewer`.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
