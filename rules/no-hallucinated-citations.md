---
name: no-hallucinated-citations
description: Verify bibliography records and DOI metadata before citing them
paths:
  - "**/*.bib"
  - "**/*.tex"
  - "**/*.qmd"
---

# Verify citations before writing

Do not add a bibliography record from memory. Verify that the work exists and
that its DOI resolves to the intended title, first author, and year. Use the
free OpenAlex and Crossref path in `bib-validate`.

- A resolving DOI is evidence for a record, not proof that every field is correct.
- A DOI that resolves to another work is a failure.
- A title match without author and year agreement remains uncertain.
- A work with no DOI may be valid. Record an accession, repository identifier, ISBN, report number, or explicit `DOI unavailable` note when applicable.
- Network failure, rate limiting, and unavailable metadata are UNVERIFIED. Do not turn them into PASS.
- Never invent a citation key. Use only a key present in the selected `.bib` file.

Run the validator before rendering or release and retain its report with the
other reproducibility evidence.
