# Source Coverage

Consider all 11 sources on every run. Query relevant sources and explain each
skip. Do not run irrelevant searches merely to fill the checklist. For a
scholarly topic, normally query alphaXiv, Semantic Scholar, OpenAlex, and the
web. A narrower choice requires a topic-specific justification.

## Plan before access

Add a `Source coverage` table to the plan before requesting approval. Include
every source below with planned use, relevance, and owner. Do not search,
fetch, or contact external services before approval. Local credential inspection
is not an external access check. Preserve the workflow's approval and delegation
gates.

| Source | Tool and supported use |
| --- | --- |
| alphaXiv | `alpha_search`; inspect decisive papers with `alpha_get_paper` or `alpha_ask_paper`, and code with `alpha_read_code` when needed |
| Semantic Scholar | `feynman_science_database_search`, `source: "semanticscholar"`; prefer default citation sorting, newest-first only for recency questions |
| OpenAlex | `feynman_science_database_search`, `source: "openalex"`; keyword/conceptual discovery and citation/reference graphs |
| arXiv | `feynman_science_database_search`, `source: "arxiv"`; known arXiv ID lookup, not topic search; discover IDs through alphaXiv, other databases, or web search |
| PubMed | `feynman_science_database_search`, `source: "pubmed"`; biomedical discovery, metadata, and identifier conversion |
| Europe PMC | `feynman_science_database_search`, `source: "europepmc"`; biomedical discovery and available open-access full-text sections |
| bioRxiv | `feynman_science_database_search`, `source: "biorxiv"`; supported preprint DOI lookup or bounded date/category retrieval for relevant biology topics |
| medRxiv | `feynman_science_database_search`, `source: "medrxiv"`; supported preprint DOI lookup or bounded date/category retrieval for relevant health topics |
| Crossref | `feynman_science_database_search`, `source: "crossref"`; title/DOI metadata checks; preserve returned DOI and endpoint provenance |
| Web | `web_search` with varied queries, then `fetch_content` / `get_search_content` for primary sources |
| Hugging Face | Discover relevant Hub repositories through web search; use `hf_dataset_info` before claiming dataset usability, `hf_repo_files` before `hf_repo_read_file`; inspect only small text files |

These are native Pi tool names. In another supported runtime, record its actual
native tool and the equivalent supported operation. If the required source
capability is unavailable, mark it blocked. In Pi, do not substitute standalone
Feynman commands for a missing native alphaXiv tool. Tool registration does not
prove endpoint access. Access, authentication, rate limits, or tool loading
failures require the exact observed error. Fallback evidence from another source
does not make the blocked source searched.

## Evidence ledger

After approval, maintain `docs/.drafts/<slug>-source-coverage.md` with exactly
one row for each source and these columns:

`Source | Status | Tool and query/ID | Date | Evidence reference | Reason or error`

Use pending rows while gathering evidence. Every row must have one of these
final statuses before delivery:

- `searched`: a native tool call completed successfully. Record its exact
  query, identifier, or retrieval operation, result count when returned, and a
  saved research-note or artifact reference containing tool-call evidence.
  Zero results count as searched but do not prove a paper or project is absent.
- `skipped`: a concrete topic-specific justification, not an access failure.
- `blocked`: an attempted call failed, or the required native capability is
  unavailable. Record the error or missing capability and any fallback
  separately. Do not claim that an unavailable tool was called.

Metadata lookup or Hub inspection counts only as that operation, not as broad
literature or repository discovery. Mark full-text claims unverified unless the
relevant content was read. If dataset features or splits are missing, mark its
schema or availability unverified. Preserve stable identifiers, source URLs,
and returned endpoint provenance in research notes.

## Direct and delegated runs

Apply this policy to direct research and researcher subagents. Coverage is
required across the run, not separately for each child. Include assigned
sources, actual native tool names, and status reporting requirements in every
saved researcher brief. After consuming results, the parent fills relevant gaps
and merges coverage into the single ledger. Do not expand an approved scope or
budget without the workflow's required approval.

## Review and provenance

Before delivery, check that the ledger contains exactly these 11 sources, every
row has a final status, and searched rows have actual tool-call evidence. Resolve
omitted relevant sources or record the blocked checks. Include the complete
coverage table and a link to the ledger in the final provenance sidecar. List
blocked sources and their effect on conclusions in the final brief. A required
source or verification blocked by missing access prevents an unqualified
verification PASS. Justified topic-specific skips are not failures.

This checklist guides agent behavior. It is not a runtime tool-call gate. Never
claim complete source coverage solely because the skill was loaded.
