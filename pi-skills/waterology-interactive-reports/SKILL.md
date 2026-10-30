---
name: waterology-interactive-reports
description: >
  Build or revise an interactive report, interactive analysis report, or
  explorable summary with narrative, interactive figures or diagrams, and
  controls. Use for the report deliverable, not a standalone widget or static report.
---

<!-- Generated from skills/interactive-reports/SKILL.md. Do not edit. -->

# Interactive Reports

Use [reports](../waterology-reports/SKILL.md) for narrative and evidence if it is not
already loaded. Read only additional skills needed for the content being built;
do not reload guidance already read for this task.
Use `waterology config context interactive-reports` for optional local guidance,
or the [local resolver](../waterology-project-conventions/references/local-preferences.md).

- Prefer Quarto for a reproducible report with standalone HTML. Use the project
  environment and follow the Quarto and computed-number sections of
  [document conventions](../../rules/quarto-conventions.md).
- Set `embed-resources: true`. Prefer Darkly as the default theme with Flatly
  available through the theme toggle, unless local or project settings differ.
  Keep print output light. Use an existing project theme when one is established.
- Generate expensive analysis and figures in scripts, then import the results.
  Keep the document render fast and preserve the code and data needed to rebuild.
- Load [interactive-graphics](../waterology-interactive-graphics/SKILL.md) only when adding
  or changing interactive plots or diagrams. A report with only an interactive
  table or navigable text does not need plotting guidance.
- Keep titles, captions, controls, and prose outside plotting canvases where
  ordinary document layout can wrap them. Use borderless figure wrappers and
  sufficient whitespace rather than decorative cards.
- Make the default view useful before any interaction. Explain what controls
  change and whether the text summarizes the full dataset or the current view.
  Ensure displayed numbers and captions remain consistent with selections.
- Render the actual HTML and test navigation, controls, linked assets, both
  themes, and a narrower layout. Verify offline behavior for a claimed standalone
  deliverable. Resource embedding does not make a server callback or remote
  dataset available offline; name any remaining dependencies.

A live dashboard or deployed application may need an application workflow.
Do not silently turn a requested portable report into a hosted service.
