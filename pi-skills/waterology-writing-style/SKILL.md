---
name: waterology-writing-style
description: Use when writing, rewriting, or tightening prose, including paragraphs, emails, documentation, plans, reports, manuscripts, abstracts, captions, and research summaries.
---

<!-- Generated from skills/writing-style/SKILL.md. Do not edit. -->

# Writing Style

Write concise prose that preserves technical meaning. Apply the base layer to
all prose. For research artifacts, also read
[scientific-prose.md](references/scientific-prose.md).

If the CLI is unavailable, use the shared
[local preferences resolver](../waterology-project-conventions/references/local-preferences.md)
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
- Use plain ASCII punctuation unless a scientific symbol requires Unicode.
  Avoid em dashes, long semicolon chains, and unnecessary hyphenated phrases.
- Remove sales language and stock phrasing such as "genuinely", "key", "best",
  "super", "gotchas", and "tuning knobs" when a precise statement works.
- Use emoji, bold text, parenthetical asides, and rhetorical openings sparingly.
  Write commit subjects in the imperative and keep terminal messages factual.
- For a Markdown file, use
  [Markdown delivery](references/markdown-artifacts.md). Read it only when
  producing that artifact, rather than for every chat reply or code comment.

## Private overrides and examples

Run `waterology config context writing-style` to include optional local
context, writing overrides, and any additional style corpus. The package's
prose conventions and scientific writing reference supply the house style;
they work without local configuration. Local settings can override those
defaults when the user and project leave a choice open.
If the CLI is unavailable, read `preferences.files`, `writing.files`, `writing.papers`
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
