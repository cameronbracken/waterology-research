---
name: literature-review
description: >
  Run a literature review, deep research investigation, ML/modeling recipe
  survey, or publication corpus review using multi-provider paper search,
  Hugging Face Hub inspection, and Zotero sync.
metadata:
  claude-command:
    name: lit
    argument-hint: <topic, research question, or author/lab>
---

# Literature Review and Deep Research

Use [writing-style](../writing-style/SKILL.md) for standalone Markdown notes and delivery (or [scientific-writing](../scientific-writing/SKILL.md) when drafting manuscript related-work sections), and read [source-coverage.md](references/source-coverage.md) to pick the right scholarly, dataset, and web tools.

## 1. Check access and Zotero setup

1. Call MCP `research_access` (`wgy research-access`) once to check `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `ZOTERO_API_KEY`, and `HF_TOKEN`. Warn briefly if relevant keys are missing; never print secret values.
2. Check `zotero_status` (`wgy zotero status`). When `.zotero.toml` is configured, queue relevant consulted sources via `literature_decision` (`decision: "include"`) or `zotero_capture` (`wgy zotero capture`) as you read or cite them, and run `zotero_sync` before finishing.

## 2. Scale the search without intermediate draft churn

Match effort to scope without creating `.plans/` or `.drafts/` copies:

- **Focused question or literature survey (default):** Search directly in hops:
  1. Query 2 to 3 distinct phrasings across `openalex`, `semantic-scholar`, `core`, or `alphaxiv` (`alphaxiv-keyword` for exact method names).
  2. Read decisive primary papers/PDFs directly (`openalex works download <doi>` or CORE/arXiv PDF URLs) rather than relying on titles or abstracts alone.
  3. Follow citations, benchmarks, and domain terms into a second hop until no material new work appears.
- **Broad multi-domain investigation:** Fan out 2 to 4 parallel `researcher` subagents only when sub-questions are genuinely disjoint, giving each an explicit sub-question and notes path, then synthesize directly in the main context.
- **ML / forecasting recipe lookup:** Capture concrete benchmark results, dataset splits/licenses (`hf_dataset_info`), hyperparameters, compute requirements, and repository entry points, ranked by feasibility.
- **Author, lab, or PI corpus review:** Resolve author/ORCID identity first, gather the publication list, and map research trajectories and turning-point papers.

## 3. Synthesize, verify citations, and deliver

- Synthesize **by theme, mechanism, or trade-off**, never as a paper-by-paper list. Separate consensus, active disagreements, dataset/evaluation caveats, and open gaps, and include a concise `Start Here` reading list when surveying a field.
- Verify DOIs and bibliography keys with [bib-validate](../bib-validate/SKILL.md) (`validate_bib.py --verify-doi`) when producing `.bib` references. In `strict` mode or for major syntheses, run one `reviewer` pass to catch overclaimed conclusions or single-source bottlenecks.
- Write **one** clean deliverable (`docs/<slug>.md`, or inline in chat for short lookups), ending with direct source links/DOIs and a brief note on providers queried and any paywall/access limits.
