---
description: Run a literature review on a topic, lab, PI, or author using paper search and primary-source synthesis.
argument-hint: <topic-or-lab-or-author>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT); multi-hop search from openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See ATTRIBUTION.md. -->

Investigate the following as a literature review: $ARGUMENTS

Tools: `WebSearch`/`web_search_exa` for the web, `WebFetch` to read sources, the Consensus MCP (when connected) plus arXiv/OpenAlex/Semantic Scholar/Crossref for papers, and the `Task` tool to launch the `researcher`, `verifier`, and `reviewer` agents.

Derive a short slug from the topic (lowercase, hyphens, no filler words, at most 5 words). Use it for all files in this run.

## Workflow

1. **Plan** — Outline scope: key questions, source types (papers, web, repos), time period, expected sections, a small task ledger, and a verification log. When the input names a lab, PI, author, or institution page, run it as a publication-corpus review: resolve the lab/author identity first, collect the reachable publication list, then map the research trajectory across that corpus. Write the plan to `docs/.plans/<slug>.md`. Summarize it briefly and continue immediately — do not wait for confirmation unless the user explicitly asked to review the plan. If a plan edit fails to apply, rewrite the full corrected plan file rather than forcing a fragile edit.
2. **Gather** — Search in hops; do not stop after one pass. Hop 1: run 2-3 distinct phrasings of the topic, skim titles and abstracts, and read the 3-5 most relevant papers. Next hop: from those, extract cited papers, author names, method and benchmark names, and field terminology the plan did not start with, and turn them into new queries. Repeat until a hop surfaces nothing relevantly new (typically 2-4 hops), tracking which papers have already been read. Use the `researcher` subagent when the sweep is wide enough to benefit from delegated triage; for narrow topics, search directly. Researcher outputs go to `<slug>-research-*.md`. For publication-corpus reviews, the lead owns identity resolution and writes `notes/<slug>-publications.md` (titles, years, venues, URLs/DOIs, gaps) before delegating trajectory synthesis. Prefer lab pages, author profiles, arXiv/OpenReview/Semantic Scholar, and results that expose stable source URLs. Mark assigned questions `done`, `blocked`, or `superseded` — never silently skip.
3. **Synthesize** — Organize by theme, not by paper: for each theme, the load-bearing papers, what they claim, and where they agree and disagree. Separate consensus, disagreements, and open questions. End the review with a short "start here" reading list of the 3-5 papers that carry the most weight. For publication-corpus reviews, identify 3-5 research trajectories and the 3-5 papers that most changed the corpus direction; rank by contrastive originality, methodology strength, and relationship to prior art, not author prestige. Where useful, propose concrete next experiments or follow-up reading. Use a source-backed comparison table, or a Mermaid diagram for taxonomies or trajectory maps when the structure is source-supported and changes a research decision.
4. **Cite** — Launch the `verifier` agent to add inline citations and verify every source URL in the draft.
5. **Verify** — Launch the `reviewer` agent to check the cited draft for unsupported claims, logical gaps, zombie sections, and single-source critical findings. Fix FATAL issues before delivering; note MAJOR issues in Open Questions; if FATAL issues were found, run one more pass after fixes.
6. **Deliver** — Save the final review to `docs/<slug>.md` and a provenance record to `docs/<slug>.provenance.md` (date; sources consulted vs. accepted vs. rejected; verification status; intermediate research files; for corpus reviews, the publication-log path and unresolved gaps). Verify on disk that both files exist before stopping — do not stop at an intermediate cited draft.
