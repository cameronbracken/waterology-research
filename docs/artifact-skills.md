# Choosing artifact skills

Choose by the work requested, then add interaction only when requested. A link
to a skill is conditional guidance, not an instruction to load every linked
file. Read each applicable skill or reference once per task. Ordinary prompts
activate these entry points; slash commands and skill names are optional.
The primary entry points explicitly allow implicit invocation in their Codex
metadata. Descriptions front-load the user goal so they remain useful when a
host shortens the skill catalog. Matching remains a model decision, not a
deterministic keyword router. See the
[official skill activation documentation](https://developers.openai.com/plugins/concepts/skills).

| Request | Base skill | Conditional additions |
| --- | --- | --- |
| Plot, chart, map, or image encoding data | [data-visualization](../skills/data-visualization/SKILL.md) | Scientific styling or publication panel composition only when needed |
| Diagram, flow chart, schematic, architecture, or process flow | [diagrams](../skills/diagrams/SKILL.md) | TikZ flowchart by default; Mermaid, Graphviz, or existing editable source when explicitly requested |
| Report, summary report, benchmark report, or analysis report | [reports](../skills/reports/SKILL.md) | Self-contained Markdown report bundle (`reports/<slug>-<YYYY-MM-DD>/`) by default; visual creation only for new or revised figures |
| Note, meeting notes, todo, or short decision record | [markdown-notes](../skills/markdown-notes/SKILL.md) | Session handoff workflow only when explicitly requested |
| README, usage guide, API reference, tutorial, or docstring | [documentation](../skills/documentation/SKILL.md) | Visual creation only for diagrams or plots being authored |
| Interactive plot or interactive diagram | Matching visual base skill | [interactive-graphics](../skills/interactive-graphics/SKILL.md) |
| Interactive report | Reports | [interactive-reports](../skills/interactive-reports/SKILL.md); interactive graphics only if authoring widgets |

For example, "make a flow chart of this pipeline" loads diagram guidance, not
scientific plotting or reporting. "Write an analysis report using these existing
figures" loads reports and writing guidance, not figure generation. "Make an
interactive report with filterable time series" adds interactive reports,
interactive graphics, and the relevant data figure guidance. "Update the README
installation commands" loads documentation and writing guidance, not reports.

Other package defaults also have ordinary entry points: "write an R function"
selects `r-code-style`, "write a Python analysis script" selects
`project-conventions`, "set up this project's environment" selects
`setup-environment`, "tighten this paragraph" selects `writing-style`, and
"draft a blog post" selects `publish-blog-post`. These entry points route to
supporting rules without requiring the user to run a context command.

Shared Markdown formatting and delivery live in a small
[reference](../skills/writing-style/references/markdown-artifacts.md). Shared
palette, export, accessibility, and render preferences live in
[visual design](../skills/data-visualization/references/visual-design.md).
Loading either reference does not load the owning skill. Optional local
guidance uses each skill's own name; existing `figure-style`, `r-conventions`,
and `quarto-conventions` settings still apply when those resources are used.

Keep these other boundaries:

- An illustration, photograph, logo, or decorative image is not a data figure.
  Use an available image creation or editing skill for that work. Quantitative
  charts should come from plotting code and data.
- A table may be report evidence without requiring a plot. Spreadsheet editing
  belongs with spreadsheet tools when that is the requested artifact.
- Slides, manuscripts, blog posts, and websites retain their dedicated delivery
  workflows. A generic report skill does not replace those formats or imply
  permission to publish.
- A standalone HTML report differs from a live dashboard or application. Choose
  based on the required behavior and deployment, not the word "interactive"
  alone. Static HTML does not imply widgets.
- Notes capture work; session logs preserve restart context; code documentation
  explains a maintained interface; reports explain findings and evidence.

For the boundary between package defaults and private context, see
[personal configuration](local-configuration.md). These skills do not change
Waterology's reproducibility mode or require new archives for ordinary writing.
