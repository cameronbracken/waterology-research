# Source Coverage

Consider all 12 sources on every run. Query relevant sources and explain each
skip. Do not run irrelevant searches merely to fill the checklist. For a
scholarly topic, normally query alphaXiv, Semantic Scholar, OpenAlex, CORE,
and the web. A narrower choice requires a topic-specific justification.

## Plan before access

Add a `Source coverage` table to the plan before requesting approval. Include
every source below with planned use, relevance, and owner. Do not search,
fetch, or contact external services before approval. Local credential inspection
is not an external access check. Preserve the workflow's approval and delegation
gates.

| Source | Tool and supported use |
| --- | --- |
| alphaXiv | Waterology `literature_search` with `provider: "alphaxiv"` for semantic search or `"alphaxiv-keyword"` for exact terms in full text (CLI `waterology discover --provider alphaxiv`), no login needed; in Pi, `alpha_search` when logged in. Inspect decisive papers with `alpha_get_paper` or `alpha_ask_paper`, and code with `alpha_read_code` when needed |
| Semantic Scholar | Waterology `literature_search` with `provider: "semantic-scholar"` (CLI `waterology discover --provider semantic-scholar`), or in Pi `feynman_science_database_search` with `source: "semanticscholar"`; prefer default citation sorting, newest-first only for recency questions |
| OpenAlex | Waterology `literature_search` with `provider: "openalex"` (CLI `waterology discover --provider openalex`), `openalex` CLI for citation/reference graphs and OA PDF download, or in Pi `feynman_science_database_search` with `source: "openalex"` |
| CORE | Waterology `literature_search` with `provider: "core"` (CLI `waterology discover --provider core`); repository copies, theses, and reports that publisher indexes miss, with PDF download locators. Full text requires `CORE_API_KEY` |
| arXiv | Waterology `literature_search` with `provider: "arxiv"` (CLI `waterology discover --provider arxiv`), or in Pi `feynman_science_database_search` with `source: "arxiv"`; known arXiv ID lookup, not topic search; discover IDs through alphaXiv, other databases, or web search |
| PubMed | Waterology `literature_search` with `provider: "pubmed"` (CLI `waterology discover --provider pubmed`), or in Pi `feynman_science_database_search` with `source: "pubmed"`; biomedical discovery, metadata, and identifier conversion |
| Europe PMC | Waterology `literature_search` with `provider: "europepmc"` (CLI `waterology discover --provider europepmc`), or in Pi `feynman_science_database_search` with `source: "europepmc"`; biomedical discovery and available open-access full-text locators |
| bioRxiv | Waterology `literature_search` with `provider: "biorxiv"` (CLI `waterology discover --provider biorxiv`), or in Pi `feynman_science_database_search` with `source: "biorxiv"`; supported preprint DOI lookup or bounded date/category retrieval for relevant biology topics |
| medRxiv | Waterology `literature_search` with `provider: "medrxiv"` (CLI `waterology discover --provider medrxiv`), or in Pi `feynman_science_database_search` with `source: "medrxiv"`; supported preprint DOI lookup or bounded date/category retrieval for relevant health topics |
| Crossref | Waterology `literature_search` with `provider: "crossref"` (CLI `waterology discover --provider crossref`), or in Pi `feynman_science_database_search` with `source: "crossref"`; title/DOI metadata checks; preserve returned DOI and endpoint provenance |
| Web | Runtime web search (`search_web`, `WebSearch`, `web_search`, or connected Kagi/Exa MCP) with varied queries, then runtime URL extraction (`read_url_content`, `WebFetch`, `fetch_content`, `get_search_content`, or `kagi_extract`) for primary sources |
| Hugging Face | Discover relevant Hub repositories through web search; use Waterology or Pi `hf_dataset_info` (CLI `waterology hf-dataset-info`) before claiming dataset usability, and `hf_repo_files` (`waterology hf-repo-files`) before `hf_repo_read_file` (`waterology hf-repo-read-file`); inspect only small text files |

Waterology MCP (`literature_search`, `hf_dataset_info`, `hf_repo_files`,
`hf_repo_read_file`) and matching `waterology` CLI subcommands work in every
supported runtime, both inside initialized `waterology.toml` projects (where
searches record to `.waterology/literature/`) and in uninitialized directories
(where searches return `recorded: false`). Delegated subagents whose runtime
does not expose MCP tools directly should run the matching `waterology` CLI
subcommands when shell access is authorized. Record the actual MCP, CLI, or
runtime tool called and the supported operation. If the required source
capability is unavailable, mark it blocked. In Pi, do not substitute standalone
Feynman commands for a missing native alphaXiv tool; use the Waterology
provider instead. Tool registration does not
prove endpoint access. Access, authentication, rate limits, or tool loading
failures require the exact observed error. Fallback evidence from another source
does not make the blocked source searched.

## Evidence ledger

After approval, maintain `docs/.drafts/<slug>-source-coverage.md` with exactly
one row for each source and these columns:

`Source | Status | Tool and query/ID | Date | Evidence reference | Reason or error`

Use pending rows while gathering evidence. Every row must have one of these
final statuses before delivery:

- `searched`: a supported MCP, CLI, or runtime tool call completed successfully.
  Record its exact query, identifier, or retrieval operation, result count when
  returned, and a saved research-note or artifact reference containing tool-call evidence.
  Zero results count as searched but do not prove a paper or project is absent.
- `skipped`: a concrete topic-specific justification, not an access failure.
- `blocked`: an attempted call failed, or the required tool capability is
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

Before delivery, check that the ledger contains exactly these 12 sources, every
row has a final status, and searched rows have actual tool-call evidence. Resolve
omitted relevant sources or record the blocked checks. Include the complete
coverage table and a link to the ledger in the final provenance sidecar. List
blocked sources and their effect on conclusions in the final brief. A required
source or verification blocked by missing access prevents an unqualified
verification PASS. Justified topic-specific skips are not failures.

This checklist guides agent behavior. It is not a runtime tool-call gate. Never
claim complete source coverage solely because the skill was loaded.
