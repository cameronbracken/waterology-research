---
name: literature-review
description: >
  Run a literature review using paper search and primary-source synthesis. Use
  when the user asks for a lit review, paper survey, state of the art, or the
  research landscape on a topic, or a publication corpus review of a specific
  lab, PI, or author.
metadata:
  claude-command:
    name: lit
    argument-hint: <topic-or-lab-or-author>
---

# Literature Review

<!-- Adapted from companion-inc/feynman, skills/literature-review/SKILL.md at
commit 8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT), with multi-hop search from
alphaXiv/openresearch-cli, agent-skills/orx-lit-review/SKILL.md at commit
13049867497de8fd5e15253cd818462629edd690 (MIT per Cargo.toml). See
ATTRIBUTION.md. -->

Use `writing-style` for the review and source synthesis.

At entry, run `waterology research-access` or MCP `research_access`. Use
`OPENALEX_API_KEY` and `ZOTERO_API_KEY` from the environment when present. Warn
clearly when the relevant key is missing. Do not print keys, request them in
chat, or treat their presence as verified provider access.

Derive a short slug from the topic. Write `docs/.plans/<slug>.md` with the
questions, source types, period, expected themes, task ledger, and verification
log. For a lab, PI, author, or institution, plan a publication corpus review:
resolve the identity, collect the reachable publication list, then map the
research trajectory. Briefly summarize the plan and continue unless the user
asked to review it first.

When working in an initialized Waterology project, record retrieval through
`waterology discover "QUERY"` or MCP `literature_search`. Save explicit date
bounds only when the question calls for them. The service retains exact queries,
provider failures and DOI provenance. Use `source-decision` to append inclusion
or exclusion reasons, and `source-add` for agency reports or local sources.
Search records establish retrieval history, not full-text access or claim support.
Use existing bibliography validation for DOI checks before citation.

Build the project Zotero collection as sources become relevant. An include
decision and `source-add` automatically queue the source and sync when configured.
For papers found through another search tool, call MCP `zotero_capture` or
`waterology zotero capture source.nt` when reading or citing them. Supply DOI,
title, authors, publication date, stable URL, and a lawful PDF URL or an existing
project-relative PDF path when available. The configured library applies across
iterations without further approval. Do not substitute a different library.

By default, raw search hits remain discovery records until selected. A project
can explicitly use `capture: discovered` to save every returned source. Before
delivery, run `waterology zotero sync` and retain pending metadata/PDF states in
the handoff. A downloaded PDF is not proof it was read or supports a claim.

Search in hops rather than stopping after one query pass:

1. Use two or three topic phrasings. Read the most relevant primary papers.
2. Extract cited papers, authors, methods, benchmarks, and field terms that were
   absent from the initial plan. Turn them into the next hop's queries.
3. Repeat until a hop finds nothing relevantly new. Track papers already read
   and mark assigned questions `done`, `blocked`, or `superseded`.

Delegate wide triage to the `researcher` through the runtime's available agent
mechanism. For a publication corpus review, the lead owns identity resolution
and writes `notes/<slug>-publications.md` before delegating trajectory work.

Synthesize by theme, not by paper. Separate consensus, disagreement, and open
questions. Identify the papers that carry each theme and end with a three to
five item `Start Here` list. For a publication corpus, identify the research
trajectories and papers that changed its direction based on originality,
methodology, and relationship to prior work rather than author prestige.

After drafting, use the `verifier` for inline citations and source URL checks,
then the `reviewer` for unsupported claims, logical gaps, incomplete sections,
and critical findings supported by only one source. Run these sequentially. Fix
fatal findings before delivery and record unresolved major findings as open
questions.

Save the review to `docs/<slug>.md` and provenance to
`docs/<slug>.provenance.md`. Record consulted, accepted, and rejected sources,
verification status, intermediate files, and unresolved gaps. Confirm both
files exist before reporting completion.

Agents used: `researcher`, `verifier`, `reviewer`.
Output: `docs/<slug>.md` with `docs/<slug>.provenance.md`.

---
*Adapted from Feynman (companion-inc/feynman, MIT); multi-hop search from
openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See
`ATTRIBUTION.md`.*
