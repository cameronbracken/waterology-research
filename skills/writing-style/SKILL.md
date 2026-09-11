---
name: writing-style
description: Use when writing or editing prose people will read, including documentation, plans, messages, comments, reports, manuscripts, abstracts, captions, and research summaries.
---

# Writing Style

Write concise prose that preserves technical meaning. Apply the base layer to
all prose. For research artifacts, also read
[scientific-prose.md](references/scientific-prose.md).

If the CLI is unavailable, use the shared
[local preferences resolver](../project-conventions/references/local-preferences.md)
with this skill name, including common preferences and matching local guidance.

## Base layer

- Lead with the result, decision, or claim. Add process details only when they
  help the reader judge or reproduce it.
- Prefer active voice, concrete nouns, and direct verbs. Remove repeated
  conclusions, throat clearing, and words that do no work.
- Keep sentences short enough to carry one clear thought. Split clause chains.
- Use the fewest headings and lists needed for navigation. Do not restate the
  same point in a heading, introduction, list, and conclusion.
- Match confidence to evidence. Do not turn a tentative result into a fact.
- Cite factual claims and credit source authors when sources are available.
  Prefer scholarly citations; otherwise cite the repository or a stable URL.
- Preserve the user's vocabulary and level of formality.

## Local writing guidance

Run `waterology config context writing-style` to include optional local
preferences, writing instructions and a user-selected style corpus. Local
settings guide tone and formatting when the user and project leave them open.
The package does not select an author's papers or punctuation preferences for
new users. If the CLI is unavailable, read `preferences.files`, `writing.files`, `writing.papers`
and `guidance.writing-style` from the global Waterology configuration directly.
Resolve file paths relative to that configuration. Missing configuration means
use the shared base layer. Do not publish private guidance or infer that papers
have been read from their presence in a list. Read supplied local summaries or
retrieve sources with the user's normal access rules before drawing on them.

## Editing pass

1. Check accuracy, caveats, terms, numbers, and source support.
2. Put the main point first and restore any missing logical connection.
3. Cut repetition, nominalizations, filler, and decorative formatting.
4. Read once for sentence length, grammar, punctuation, and Markdown spacing.
