---
name: waterology-writing-style
description: Use when writing, rewriting, or tightening prose, including paragraphs, emails, documentation, plans, reports, manuscripts, abstracts, captions, and research summaries.
---

<!-- Generated from skills/writing-style/SKILL.md. Do not edit. -->

# Writing Style

Write concise prose that preserves technical meaning. Apply the base layer below to all prose; for manuscripts, reports, and research summaries, also read [scientific-prose.md](references/scientific-prose.md).

## Base prose rules

- Lead with the result, decision, or claim. Add process details only when they help the reader judge or reproduce it.
- Prefer active voice, concrete nouns, and direct verbs. Cut throat-clearing, repeated conclusions, and words that do no work.
- Keep sentences short enough to carry one clear thought. Split long clause chains.
- Use the fewest headings and lists needed for navigation. Do not restate the same point in a heading, intro, bullet, and closer.
- Match confidence to evidence. Do not turn a tentative observation into an unqualified fact.
- Cite factual claims and credit source authors (with ORCID where applicable). Prefer scholarly citations; otherwise link the repository or a stable primary page.
- Use plain ASCII punctuation unless a scientific symbol requires Unicode. Avoid em dashes, long semicolon chains, and unnecessary hyphenated modifiers (such as "data-centric" or "analysis-ready").
- Remove sales language and stock phrasing such as "genuinely", "honestly", "load-bearing", "key", "best", "super", "gotchas", and "tuning knobs".
- Use emoji, bold text, and parenthetical asides sparingly. Write commit subjects in the imperative and keep terminal messages factual.

## Markdown artifact formatting and delivery

Apply when writing or updating `.md` files (reports, notes, READMEs, documentation, plans):

- Prefer underscores (`_text_`) over asterisks for emphasis, and leave blank lines around headings, lists, and code fences.
- Make every link clickable with named `[label](https://...)` syntax. Never emit bare URLs. Use relative paths within a portable folder bundle and descriptive alt text on images.
- When producing a Markdown file that needs user review on macOS, open the finished file directly with the `open` CLI command when a desktop session is available; otherwise provide a clickable `file://` link.

## Editing pass

1. Verify numbers, units, caveats, terminology, and citations against sources.
2. Put the main point first and cut filler, nominalizations, and decorative formatting.
3. Check sentence length, plain ASCII punctuation, named links, and Markdown spacing.
