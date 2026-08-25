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

Derive a short slug from the topic. Write `docs/.plans/<slug>.md` with the
questions, source types, period, expected themes, task ledger, and verification
log. For a lab, PI, author, or institution, plan a publication corpus review:
resolve the identity, collect the reachable publication list, then map the
research trajectory. Briefly summarize the plan and continue unless the user
asked to review it first.

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
