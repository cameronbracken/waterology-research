---
name: waterology-writing-style
description: >
  Use when writing or editing non-paper prose and Markdown deliverables:
  explanations, blog posts, technical notes, walkthroughs, READMEs,
  documentation, analysis reports, plans, emails, and commit messages. For
  formal journal manuscripts, data descriptors, and paper abstracts, use
  `waterology-scientific-writing` instead.
---

<!-- Generated from skills/writing-style/SKILL.md. Do not edit. -->

# Writing Style

Write clear, conversational, technically accurate prose. Sound like a pragmatic engineer-researcher explaining work to a peer, not a press release or corporate memo. For peer-reviewed papers, data descriptors, abstracts, and reviewer responses, load either [scientific-writing](../waterology-scientific-writing/SKILL.md) (default concise) or [scientific-writing-detailed](../waterology-scientific-writing-detailed/SKILL.md) (expanded variant), never both at once.

## Match register to the artifact

- **Conversational technical (default for explanations, blog posts, notes, walkthroughs, emails):** Use natural first person (`I` / `we`), `you`, and contractions (`it's`, `don't`, `I've`). Open with the practical problem, motivation, or story before mechanics; use question or step headings (`Why port working software?`) when helpful; include brief candid asides and practical gotchas.
- **Direct reference and status (READMEs, docs, reports, plans, PRs, CLI output, commits):** Lead with what it does, what changed, or the headline finding. Use compact tables or lists for scanability without restating the same takeaway in a heading, intro, bullet, and closer. Write Git commit subjects in the imperative mood.

## Shared technical accuracy and voice

- **Concrete over abstract:** Anchor claims in exact numbers, units, tolerances, file paths, commands, or a small runnable example rather than vague generalities. Explain _why_ a tool, constraint, or workaround was chosen.
- **Credit and candor:** Credit upstream authors, datasets, and tools up front. State trade-offs, rough edges, and unknowns plainly (including when an apparent speedup or metric looks inflated or untested) rather than overselling.
- **Cut AI and marketing slop:** Remove filler openings and stock buzzwords (`delve`, `seamless`, `game-changer`, `tapestry`, `robust ecosystem`, `leverage` when `use` works, `"it's worth noting that"`, `"let's dive in"`, `"in conclusion"`).
- **Clean punctuation:** Keep sentence length varied and readable. Use plain ASCII punctuation unless a symbol requires Unicode; prefer commas, colons, or parentheses over em-dash chains.

## Markdown formatting and delivery

- Leave blank lines around headings, lists, tables, and code fences; prefer `_text_` for italics and use bold or emoji sparingly.
- Make every link clickable with `[label](https://...)` syntax (or relative paths inside a folder bundle). Never emit bare URLs, and include descriptive alt text on images.
- When producing a `.md` file for review on macOS, open it with `open` if a desktop session is active; otherwise provide a clickable `file://` link.
