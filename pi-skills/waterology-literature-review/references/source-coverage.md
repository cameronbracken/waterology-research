# Scholarly and Dataset Source Coverage

Use the providers relevant to the topic rather than calling every endpoint mechanically. For most computational and domain research questions, combine `openalex`, `semantic-scholar`, `core`, `alphaxiv` / `alphaxiv-keyword`, and primary web/agency sources.

| Source | Tool and supported use |
| --- | --- |
| OpenAlex | MCP `literature_search` (`provider: "openalex"`) or `wgy discover --provider openalex`; `openalex` CLI for citation graphs (`cited-by`, `references`, `related`), ORCID resolution, and OA PDF download (`openalex works download <doi>`) |
| Semantic Scholar | `literature_search` (`provider: "semantic-scholar"`) or `wgy discover --provider semantic-scholar` |
| CORE | `literature_search` (`provider: "core"`) or `wgy discover --provider core` for institutional repository copies, theses, and technical reports with PDF download links (`CORE_API_KEY` unlocks higher limits) |
| alphaXiv | `literature_search` with `provider: "alphaxiv"` (semantic search) or `"alphaxiv-keyword"` (exact method/acronym terms in full text), no login required |
| arXiv | `literature_search` (`provider: "arxiv"`) for known arXiv ID lookup; use alphaXiv for topic discovery |
| PubMed / Europe PMC | `literature_search` (`provider: "pubmed"` or `"europepmc"`) for biomedical and environmental health literature |
| bioRxiv / medRxiv | `literature_search` (`provider: "biorxiv"` or `"medrxiv"`) with a preprint DOI or bounded `after`/`before` dates (`<= 90` days) |
| Crossref | `literature_search` (`provider: "crossref"`) for bibliographic and DOI lookup |
| Hugging Face Hub | `hf_dataset_info` (`wgy hf-dataset-info`), `hf_repo_files` (`wgy hf-repo-files`), and `hf_repo_read_file` (`wgy hf-repo-read-file`, small text files only) |
| Web / Agency | Runtime web search (`kagi_search_fetch` when connected) and URL reader (`kagi_extract`) for USGS, NOAA, EIA, DOE, official docs, and code repositories |

## Provenance rules

- Metadata or abstract inspection is not full-text reading; state clearly which key papers were read in full versus triaged from abstracts.
- When `.zotero.toml` is present, searches record locally under `.waterology/literature/` (`recorded: true`) and `literature_decision` (`include`) or `zotero_capture` syncs citations and caches public PDFs under `.waterology/references/pdfs/`. Outside a `.zotero.toml` workspace, `literature_search` still runs cleanly (`recorded: false`).
- Record any blocked provider or paywalled full text explicitly rather than treating an access limit as absence of prior work.
