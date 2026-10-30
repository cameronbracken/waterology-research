---
name: reports
description: >
  Create or revise a report artifact, including a summary report, analysis
  report, technical report, or research reporting deliverable with narrative
  and linked or embedded evidence. Distinct from brief notes and code documentation.
---

# Reports

Use [writing-style](../writing-style/SKILL.md) for prose. Read
[Markdown delivery](../writing-style/references/markdown-artifacts.md) for
Markdown output. Read optional local guidance with
`waterology config context reports`, or use the
[local resolver](../project-conventions/references/local-preferences.md).

- Establish the question, audience, scope, and intended decision from the
  request and project context. Scale the structure to the report; a summary
  report does not need the full structure of a scientific manuscript.
- Lead with findings, then explain the evidence, method, limitations, and
  implications needed to assess them. Distinguish completed work, observed
  results, interpretation, and remaining work.
- Default to Markdown with linked or embedded visuals. Use Quarto for a
  requested rendered analysis report or HTML deliverable. Use LaTeX for a
  requested polished PDF report, manuscript, or white paper. Preserve existing
  templates and project formats.
- Link to existing tables, figures, code, and data instead of duplicating them.
  Embed the visuals needed to follow the argument and explain what each shows.
  Retain source credit, units, dates, and relevant uncertainty.
- Pull computed results from analysis outputs or generated text. Do not hand
  transcribe numbers that will drift when the analysis changes.
- Check links, embedded assets, captions, cross references, and correspondence
  between statements and evidence. Render and inspect formatted deliverables
  before claiming the layout is ready.

Load additional guidance only for work the report actually needs:

| Work requested | Additional skill or rule |
| --- | --- |
| Create or revise data figures | [data-visualization](../data-visualization/SKILL.md) |
| Create or revise conceptual diagrams | [diagrams](../diagrams/SKILL.md) |
| Interactive report | [interactive-reports](../interactive-reports/SKILL.md) |
| Quarto or LaTeX source | [document conventions](../../rules/quarto-conventions.md) |

Reusing a finished figure does not require its creation workflow. A brief note
or todo list uses [markdown-notes](../markdown-notes/SKILL.md); instructions that accompany code
use [documentation](../documentation/SKILL.md). Follow these alternatives only
when they describe the requested deliverable.
