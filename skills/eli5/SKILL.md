---
name: eli5
description: >
  Explain research, papers, or technical ideas in plain English with minimal
  jargon, concrete analogies, and clear takeaways. Use when the user says "ELI5
  this", asks for a simple explanation of a paper or result, wants jargon
  removed, or asks what something technically dense actually means.
---

# ELI5

Use `writing-style` for the explanation.

Explain a paper or idea simply, without dumbing down what it actually shows.

When the user names a specific paper, arXiv ID, DOI, or URL, read it first
with the runtime's available page or scholarly source reader before explaining.
For a long source, use `source-summarization` to create an on-disk summary
first. If the user gives only a topic, anchor the explanation on the 1-3
clearest representative papers.

Structure the answer with:
- `One-Sentence Summary`
- `Big Idea`
- `How It Works`
- `Why It Matters`
- `What To Be Skeptical Of`
- `If You Remember 3 Things`

Guidelines:
- Short sentences, concrete words.
- Define jargon immediately or remove it.
- One good analogy beats several weak ones.
- Keep what the paper actually shows separate from interpretation or speculation.
- Keep it inline unless the user asks to save it as an artifact.
