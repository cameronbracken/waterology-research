# Deep Research Workflow

Execute the investigation and leave durable files. Do not answer by explaining
this protocol.

## Artifacts and plan approval

Derive a lowercase, hyphenated slug with no filler words and at most five
words. Every approved run leaves:

- `docs/.plans/<slug>.md`
- `docs/.drafts/<slug>-draft.md`
- `docs/.drafts/<slug>-cited.md`
- `docs/<slug>.md` or `papers/<slug>.md`
- `docs/<slug>.provenance.md` or `papers/<slug>.provenance.md`

Create the plan first. Record the research questions, evidence needs, scale
decision, task ledger, verification log, and decision log. Summarize it and ask
for explicit confirmation before searching, fetching, delegating, drafting, or
reviewing. Apply requested plan changes and ask again.

After approval, continue in degraded mode if a capability fails. Record the
failure and still write a partial or blocked final artifact plus provenance.
Use `Verification: BLOCKED` for checks that could not run. Do not end with chat
only output after plan approval.

## Scale and ownership

Choose scale before assigning work:

- Use direct search for a narrow question, a single fact, or work likely to
  need no more than about ten search and fetch operations.
- Use two `researcher` agents for a direct comparison when separate ownership
  helps.
- Use three or four researchers for a broad survey with distinct facets.
- Use more only for a complex investigation whose domains can be separated
  without duplicate work.

For a narrow explainer, keep direct ownership unless the user requests broad
coverage, current benchmarks, or a comprehensive landscape. When delegating,
write each brief first under `docs/.plans/`. Give it a question, source scope,
file ownership, output path, and return contract. Launch agents through the
runtime's available delegation mechanism.

## Gather evidence

For direct search, use at least three distinct queries that cover definition or
history, mechanism, and current usage or comparison. Save exact queries and
notes to `docs/.drafts/<slug>-research-direct.md`.

For delegated research, keep the detailed instructions in each written brief.
Prefer primary papers, official documentation, repositories, stable metadata,
and readable HTML. If only a PDF is available and extraction fails, cite the
PDF URL and mark full text inspection blocked.

Update the task ledger and verification log when evidence gathering finishes.
Record failed or incomplete research and continue to a partial draft.

## Draft and claim check

Write `docs/.drafts/<slug>-draft.md` with a concise summary, findings organized
by question or theme, supported caveats and disagreements, and open questions.
Do not invent sources, results, figures, benchmarks, or tables.

Before citation, map each critical claim, number, figure, table, and benchmark
to a source URL, research note, or artifact path. Remove or weaken unsupported
claims and label inferences.

## Cite, then review

For direct search, verify each URL and write the cited draft yourself. Also
write `docs/.drafts/<slug>-verification.md` with FATAL, MAJOR, and MINOR
findings plus the checks performed.

When researchers were used, run the `verifier` after the complete draft exists.
Give it the draft, research files, and `docs/.drafts/<slug>-cited.md` as its
output. Confirm that file exists before continuing.

Only after citation completes, run the `reviewer` on the cited draft. Do not run
citation and review concurrently. Fix fatal findings and perform one more
review pass. Record unresolved major findings under Open Questions.

Use localized edits for a few simple corrections. For a larger rewrite, write
`docs/.drafts/<slug>-revised.md`. Check on disk that corrected text is present
and replaced text is absent. The revised file is the final candidate when it
exists; otherwise use the cited file.

## Deliver and verify

Copy the final candidate to `papers/<slug>.md` for a paper style draft or
`docs/<slug>.md` otherwise. Write the provenance sidecar next to it. Record:

- Date and research rounds.
- Consulted, accepted, and rejected sources.
- Verification status.
- Plan and research file paths.
- Blocked checks and unresolved gaps.

Confirm every required artifact exists and that claimed fixes appear in the
final candidate. Respond with links to the final artifact and provenance plus a
short list of blocked checks.
