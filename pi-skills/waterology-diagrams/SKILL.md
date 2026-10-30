---
name: waterology-diagrams
description: >
  Create or revise diagrams, flow charts, schematics, process flows, architecture
  drawings, dependency graphs, or concept maps that represent conceptual
  relationships. Applies to static and interactive diagrams, rather than data plots.
---

<!-- Generated from skills/diagrams/SKILL.md. Do not edit. -->

# Diagrams

Make the entities, relationships, direction, and scope explicit before choosing
the layout. A network showing conceptual dependencies belongs here; a network
encoding measured quantities may also need data visualization guidance.

Read [visual design](../waterology-data-visualization/references/visual-design.md).
Use `waterology config context diagrams` for optional local guidance, or the
[local resolver](../waterology-project-conventions/references/local-preferences.md).

- Prefer Mermaid for simple flows, dependencies, and sequence diagrams that
  should remain editable in Markdown. Use TikZ for LaTeX or Beamer diagrams.
  Respect an existing SVG or other editable diagram source when extending it.
- Label nodes and meaningful edges. Distinguish sequence, dependency, data
  movement, and feedback rather than using the same arrow for every relationship.
- Group related elements and reduce crossings. Include a legend only when the
  notation is not self explanatory. Split an unreadable overview into a small
  overview and focused details.
- Save the editable source with the rendered SVG or required export. For
  Markdown delivery, use
  [Markdown delivery](../waterology-writing-style/references/markdown-artifacts.md). Embed
  Mermaid only when the target renderer supports it; otherwise provide a
  rendered image and link to the source.
- Render and inspect the chosen layout. Confirm that arrows connect the right
  entities and the diagram agrees with the supplied process or implementation.

Only for requested interaction, load
[interactive-graphics](../waterology-interactive-graphics/SKILL.md). A Mermaid block or an
SVG in an HTML page is not, by itself, an interactive diagram.
