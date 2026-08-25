---
name: pdf-explore
description: >
  Read, extract, and cross-check content across scientific PDFs. Use when a task
  needs methods, figures, tables, citations, data accessions, or claims from
  more than one place in one or more papers.
---

# PDF Explore

<!-- Adapted from companion-inc/feynman, skills/pdf-explore/SKILL.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT). See ATTRIBUTION.md. -->

Use `writing-style` for extracted notes, comparisons, and summaries.

Use when a PDF answer depends on more than one page or section.

1. Parse the PDF enough to map its structure — title, abstract, methods,
   figures, tables, supplement references, and citations. Extract text with
   `pdftotext` (or a layout-aware tool for tables) before reasoning over it, so
   the content sits on disk rather than only in a single visible page.
2. Extract the exact pages and regions that support the answer. Keep table
   values, figure labels, accession IDs, and quoted snippets tied to their page
   numbers.
3. Cross-check claims against methods, captions, supplement text, and cited
   papers when the conclusion depends on them.
4. Save extracted notes and provenance as artifacts under `notes/` or `docs/`.

Do not answer from a single visible page when the question spans methods,
figures, or supplements. For a whole-document summary of a long PDF, use
`source-summarization`, which keeps the text on disk and reads bounded windows.

---
*Adapted from Feynman (companion-inc/feynman, MIT). See `ATTRIBUTION.md`.*
