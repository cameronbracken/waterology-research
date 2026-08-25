---
description: Run a thorough, source-heavy investigation on a topic and produce a durable research brief with inline citations.
argument-hint: <topic>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Run deep research for: $ARGUMENTS

This is an execution request, not a request to explain the workflow. Execute it. Your first actions should be tool calls that create directories and write the plan artifact.

## Tools

- Search with `WebSearch` (or `web_search_exa` when the Exa MCP is connected).
- Fetch pages with `WebFetch`.
- For peer-reviewed papers, use the Consensus MCP when connected; otherwise search arXiv, OpenAlex, Semantic Scholar, and Crossref by URL. OpenAlex and Crossref are keyless.
- Delegate evidence gathering and verification with the `Task` tool, launching the `researcher`, `verifier`, and `reviewer` agents.

## Required artifacts

Derive a short slug from the topic: lowercase, hyphenated, no filler words, at most 5 words. Every run leaves these files on disk:
- `docs/.plans/<slug>.md`
- `docs/.drafts/<slug>-draft.md`
- `docs/.drafts/<slug>-cited.md`
- `docs/<slug>.md` or `papers/<slug>.md`
- `docs/<slug>.provenance.md` or `papers/<slug>.provenance.md`

After the user approves the plan, if any capability fails, continue in degraded mode and still write a blocked or partial final output and provenance sidecar. Never end with chat-only output after plan approval. Use `Verification: BLOCKED` when verification could not be completed.

## Step 1: Plan

Create `docs/.plans/<slug>.md` immediately. The plan includes: key questions, evidence needed, scale decision, task ledger, verification log, decision log.

Make the scale decision before assigning owners. If the topic is a narrow "what is X" explainer, use lead-owned direct search only; do not allocate researcher subagents.

After writing the plan, stop and ask for explicit confirmation before gathering evidence. Summarize the plan briefly and ask:

`Proceed with this deep research plan? Reply "yes" to continue, or tell me what to change.`

Do not run searches, fetch sources, spawn subagents, draft, cite, review, or deliver until the user confirms. If the user requests changes, update the plan first, then ask again.

## Step 2: Scale

Use direct search for a single fact or narrow question, or work you can answer with 3-10 tool calls. For "what is X" explainers you MUST NOT spawn researcher subagents unless the user explicitly asks for comprehensive coverage, current landscape, benchmarks, or deployment.

Use subagents only when decomposition clearly helps:
- Direct comparison of 2-3 items: 2 `researcher` subagents
- Broad survey or multi-faceted topic: 3-4 `researcher` subagents
- Complex multi-domain research: 4-6 `researcher` subagents

## Step 3: Gather evidence

If direct search was chosen: skip researcher spawning, search and fetch yourself, use at least 3 distinct queries covering definition/history, mechanism, and current usage/comparison. Record the exact search terms and notes in `docs/.drafts/<slug>-research-direct.md`.

If subagents were chosen: write a per-researcher brief first (e.g. `docs/.plans/<slug>-T1.md`), then launch each `researcher` via the `Task` tool pointing it at its brief and output file. Keep task instructions short; the detail lives in the brief. Prefer paper metadata, abstracts, HTML pages, official docs, and web snippets over crash-prone PDF parsing — if only a PDF exists, cite the PDF URL and mark full-text extraction as blocked.

After evidence gathering, update the plan ledger and verification log. If research failed, record exactly what failed and proceed with a blocked or partial draft.

## Step 4: Draft

Write the report yourself. Save to `docs/.drafts/<slug>-draft.md`. Include an executive summary, findings by question or theme, evidence-backed caveats and disagreements, and open questions. No invented sources, results, figures, benchmarks, or tables.

Before citation, sweep the draft: every critical claim, number, figure, table, or benchmark maps to a source URL, research note, or artifact path. Remove or downgrade unsupported claims. Mark inferences as inferences.

## Step 5: Cite

If direct search was chosen, cite yourself: verify reachable URLs, then write `docs/.drafts/<slug>-cited.md` with inline citations and a Sources section. Do not spawn the verifier for simple direct-search runs.

If researcher subagents were used, launch the `verifier` agent (via `Task`) after the draft exists. This is mandatory and completes before any reviewer runs. Point it at the draft and the research files; have it write `docs/.drafts/<slug>-cited.md`. Confirm on disk that the cited file exists afterward.

## Step 6: Review

If direct search was chosen, review the cited draft yourself: write `docs/.drafts/<slug>-verification.md` with FATAL / MAJOR / MINOR findings and the checks performed. Fix FATAL issues before delivery.

If researcher subagents were used, only after the cited draft exists, launch the `reviewer` agent against it. Do not run verifier and reviewer in the same parallel call. If the reviewer flags FATAL issues, fix them and run one more review pass. Note MAJOR issues in Open Questions; accept MINOR.

When applying fixes, use small localized edits only for 1-3 simple corrections; for larger rewrites, write a corrected full file to `docs/.drafts/<slug>-revised.md`. After applying fixes, run an explicit on-disk check (`grep`/`rg`) proving the old wording is gone and the new wording is present before claiming the fix landed.

The final candidate is `docs/.drafts/<slug>-revised.md` if it exists, otherwise `docs/.drafts/<slug>-cited.md`.

## Step 7: Deliver

Copy the final candidate to `papers/<slug>.md` for paper-style drafts, or `docs/<slug>.md` otherwise. Write provenance next to it as `<slug>.provenance.md`:

```markdown
# Provenance: [topic]

- **Date:** [date]
- **Rounds:** [number of research rounds]
- **Sources consulted:** [count and/or list]
- **Sources accepted:** [count and/or list]
- **Sources rejected:** [dead, unverifiable, or removed]
- **Verification:** [PASS / PASS WITH NOTES / BLOCKED]
- **Plan:** docs/.plans/<slug>.md
- **Research files:** [files used]
```

Before responding, verify on disk that all required artifacts exist and that any fixes claimed in the provenance are reflected in the final candidate. Keep the final response brief: link the final file, the provenance file, and any blocked checks.
