---
name: documentation
description: >
  Write or update documentation accompanying code: README files, installation
  and usage guides, API references, configuration docs, tutorials, developer
  guides, and docstrings. Distinct from analysis reports and personal notes.
---

# Documentation

Use [writing-style](../writing-style/SKILL.md) and, for Markdown files,
[Markdown delivery](../writing-style/references/markdown-artifacts.md).
Read optional local guidance with `waterology config context documentation`,
or use the [local resolver](../project-conventions/references/local-preferences.md).

- Read the owning code, CLI help, configuration schema, tests, and existing
  documentation before describing behavior. Separate supported behavior from
  proposals, and label untested examples.
- Match the reader's task: getting started, completing a specific operation,
  looking up an option, or understanding the design. Keep the smallest useful
  page and link related material instead of duplicating maintained instructions.
- Use Markdown by default and preserve the project's documentation framework.
  Put material beside its owning code or in the established docs tree, and add
  an index link when creating a page users need to discover.
- Give the prerequisites and a runnable minimal example. Explain consequential
  inputs, defaults, outputs, and limitations. Use portable example paths and
  environment-managed commands. Verify commands when practical without making
  unintended external changes.
- Keep examples and documented names consistent with current interfaces.
  Treat generated API documentation as generated; edit its source rather than
  the rendered output. Do not present an implementation detail as a user step
  unless it helps the reader complete the task.
- Attribute human sources where relevant, including ORCID when available.
  Follow the project's AI use statement convention; use actual model identities
  when known and never invent attribution.
- Check links, snippets, navigation, and the relevant docs build. State which
  examples or environment-dependent steps could not be verified.

Only load [diagrams](../diagrams/SKILL.md) when authoring conceptual diagrams,
or [data-visualization](../data-visualization/SKILL.md) when creating data plots.
Code documentation does not need report or interactive-report guidance merely
because the docs site renders HTML. Interactive examples use
[interactive-graphics](../interactive-graphics/SKILL.md) only when requested.
