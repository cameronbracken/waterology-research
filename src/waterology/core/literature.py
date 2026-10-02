"""Recorded scholarly discovery and explicit local source inclusion decisions."""

import json
import os
import warnings
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from waterology.core.atomic import write_json
from waterology.core.project import discover_project, project_state_lock


def fetch_openalex(query: str, *, after: str | None, before: str | None, limit: int) -> dict:
    if not os.environ.get("OPENALEX_API_KEY"):
        warnings.warn(
            "OPENALEX_API_KEY is not available; trying unauthenticated OpenAlex access",
            RuntimeWarning,
            stacklevel=2,
        )
    parameters = {"search": query, "per_page": limit}
    filters = []
    if after:
        filters.append(f"from_publication_date:{after}")
    if before:
        filters.append(f"to_publication_date:{before}")
    if filters:
        parameters["filter"] = ",".join(filters)
    if os.environ.get("OPENALEX_API_KEY"):
        parameters["api_key"] = os.environ["OPENALEX_API_KEY"]
    request = Request(
        "https://api.openalex.org/works?" + urlencode(parameters),
        headers={"User-Agent": "Waterology literature discovery"},
    )
    with urlopen(request, timeout=30) as response:
        payload = response.read(4_000_001)
    if len(payload) > 4_000_000:
        raise ValueError("Provider response exceeds the bounded read limit")
    return json.loads(payload)


def fetch_semantic_scholar(
    query: str, *, after: str | None, before: str | None, limit: int
) -> dict:
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if not key:
        warnings.warn(
            "SEMANTIC_SCHOLAR_API_KEY is not available; trying unauthenticated Semantic Scholar access",
            RuntimeWarning,
            stacklevel=2,
        )
    parameters = {
        "query": query,
        "limit": limit,
        "fields": "title,externalIds,url,authors,venue,publicationDate,year,openAccessPdf,publicationTypes",
    }
    if after or before:
        parameters["year"] = f"{after[:4] if after else ''}-{before[:4] if before else ''}"
    headers = {"User-Agent": "Waterology literature discovery"}
    if key:
        headers["x-api-key"] = key
    request = Request(
        "https://api.semanticscholar.org/graph/v1/paper/search?" + urlencode(parameters),
        headers=headers,
    )
    from urllib.request import HTTPRedirectHandler, build_opener

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        payload = response.read(4_000_001)
    if len(payload) > 4_000_000:
        raise ValueError("Provider response exceeds the bounded read limit")
    return json.loads(payload)


def normalize_semantic_scholar(results: list[dict], *, after=None, before=None) -> list[dict]:
    converted = []
    for item in results:
        if not isinstance(item, dict):
            raise TypeError("Provider result must be an object")
        publication_date = item.get("publicationDate")
        if publication_date:
            date.fromisoformat(publication_date)
        # Never invent a day for papers whose provider knows only the year.
        if (after or before) and (
            not publication_date
            or (after and publication_date < after)
            or (before and publication_date > before)
        ):
            continue
        converted.append(
            {
                "id": item.get("paperId"),
                "doi": (item.get("externalIds") or {}).get("DOI"),
                "title": item.get("title"),
                "publication_date": publication_date,
                "authorships": [
                    {"author": {"display_name": a.get("name")}} for a in (item.get("authors") or [])
                ],
                "primary_location": {
                    "source": {"display_name": item.get("venue") or ""},
                    "landing_page_url": item.get("url"),
                },
                "best_oa_location": {"pdf_url": (item.get("openAccessPdf") or {}).get("url")},
                "type": "preprint"
                if "Preprint" in (item.get("publicationTypes") or [])
                else "article",
            }
        )
    sources = normalize_sources(converted)
    for source in sources:
        source["provider"] = "semantic-scholar"
        for provenance in source["provenance"]:
            provenance["provider"] = "semantic-scholar"
    return sources


def _directory(start: Path) -> Path:
    path = discover_project(start).paths.state / "literature"
    if path.is_symlink():
        raise ValueError("Literature directory must not be a symlink")
    path.mkdir(exist_ok=True)
    return path


def normalize_sources(results: list[dict]) -> list[dict]:
    combined = {}
    for item in results:
        if not isinstance(item, dict):
            raise TypeError("Provider result must be an object")
        doi = item.get("doi")
        doi = (
            doi.lower().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
            if isinstance(doi, str)
            else None
        )
        identifier = item.get("id")
        identity = doi or identifier
        if not isinstance(identity, str) or not identity:
            raise ValueError("Source lacks an identifier")
        source = {
            "provider": "openalex",
            "id": identifier,
            "doi": doi,
            "title": item.get("display_name") or item.get("title"),
            "item_type": {
                "article": "journalArticle",
                "preprint": "preprint",
                "book": "book",
                "book-chapter": "bookSection",
                "dissertation": "thesis",
                "report": "report",
                "dataset": "dataset",
            }.get(item.get("type"), "journalArticle"),
            "publication_date": item.get("publication_date"),
            "authors": [
                a["author"]["display_name"]
                for a in item.get("authorships", [])
                if a.get("author", {}).get("display_name")
            ],
            "venue": ((item.get("primary_location") or {}).get("source") or {}).get(
                "display_name", ""
            ),
            "pdf_url": (item.get("best_oa_location") or {}).get("pdf_url"),
            "url": (item.get("primary_location") or {}).get("landing_page_url"),
            "open_access": item.get("open_access"),
            "full_text_read": False,
            "decision": "unreviewed",
            "note": None,
        }
        if identity not in combined:
            combined[identity] = {**source, "provenance": [source.copy()]}
        else:
            combined[identity]["provenance"].append(source)
    return list(combined.values())


def search_literature(
    start: Path,
    query: str,
    *,
    after: str | None = None,
    before: str | None = None,
    limit: int = 20,
    fetcher=None,
    provider: str = "openalex",
) -> dict:
    if provider not in {"openalex", "semantic-scholar"}:
        raise ValueError("Provider must be openalex or semantic-scholar")
    if not query.strip() or not 1 <= limit <= 100:
        raise ValueError("Supply a query and limit between 1 and 100")
    if after:
        date.fromisoformat(after)
    if before:
        date.fromisoformat(before)
    if after and before and after > before:
        raise ValueError("Publication date range is reversed")
    record = {
        "schema_version": 1,
        "id": f"search-{uuid4().hex[:16]}",
        "provider": provider,
        "query": query,
        "after": after,
        "before": before,
        "limit": limit,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "status": "complete",
        "sources": [],
        "error": None,
    }
    try:
        fetch = fetch_openalex if provider == "openalex" else fetch_semantic_scholar
        payload = (fetcher or fetch)(query, after=after, before=before, limit=limit)
        results_key = "results" if provider == "openalex" else "data"
        if not isinstance(payload, dict) or not isinstance(payload.get(results_key), list):
            raise TypeError("Provider response lacks results")
        results = payload[results_key][:limit]
        record["sources"] = (
            normalize_sources(results)
            if provider == "openalex"
            else normalize_semantic_scholar(results, after=after, before=before)
        )
    except (OSError, ValueError, TypeError, AttributeError) as error:
        # HTTP exceptions can contain URLs with API keys. Never persist their message.
        record.update(status="unverified", error=type(error).__name__)
    with project_state_lock(start):
        write_json(_directory(start) / f"{record['id']}.json", record)
    from waterology.core.zotero import queue_reference, settings_for, sync_references

    try:
        settings = settings_for(start)
        if settings and settings.capture == "discovered":
            queued = []
            record["capture_errors"] = []
            for source in record["sources"]:
                try:
                    queued.append(
                        queue_reference(start, source, reason=record["id"], sync=False)["id"]
                    )
                except (OSError, ValueError, TypeError, KeyError) as error:
                    record["capture_errors"].append(
                        {"source_id": source.get("id"), "error": type(error).__name__}
                    )
            if queued:
                record["zotero"] = sync_references(
                    start, identifiers=queued, limit=min(len(queued), 100)
                )
    except (OSError, ValueError, TypeError, KeyError) as error:
        record["zotero"] = {"status": "blocked", "error": type(error).__name__}
    return record


def record_source_decision(
    start: Path, search_id: str, source_id: str, *, decision: str, note: str
) -> dict:
    if decision not in {"include", "exclude", "unresolved"} or not note.strip():
        raise ValueError("Supply an inclusion decision and a reason")
    if (
        not search_id.startswith("search-")
        or len(search_id) != 23
        or any(c not in "0123456789abcdef" for c in search_id[7:])
    ):
        raise ValueError("Invalid search identifier")
    with project_state_lock(start):
        path = _directory(start) / f"{search_id}.json"
        if path.is_symlink():
            raise ValueError("Search record must not be a symlink")
        search = json.loads(path.read_text())
        if not any(source_id in (s["id"], s["doi"]) for s in search["sources"]):
            raise ValueError("Source was not in this retrieval")
        record = {
            "id": f"decision-{uuid4().hex[:16]}",
            "search_id": search_id,
            "source_id": source_id,
            "decision": decision,
            "note": note,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        write_json(_directory(start) / f"{record['id']}.json", record)
    if decision == "include":
        from waterology.core.zotero import queue_reference

        source = next(s for s in search["sources"] if source_id in (s["id"], s["doi"]))
        try:
            record["reference"] = queue_reference(start, source, reason=f"{search_id}: {note}")
        except (OSError, ValueError, TypeError, KeyError) as error:
            record["zotero"] = {"status": "blocked", "error": type(error).__name__}
    return record


def register_local_source(start: Path, *, title: str, locator: str, note: str) -> dict:
    if not title.strip() or not locator.strip():
        raise ValueError("Supply a title and durable locator")
    record = {
        "id": f"source-{uuid4().hex[:16]}",
        "provider": "local",
        "title": title,
        "locator": locator,
        "note": note,
        "full_text_read": False,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    with project_state_lock(start):
        write_json(_directory(start) / f"{record['id']}.json", record)
    from waterology.core.zotero import queue_reference

    try:
        record["reference"] = queue_reference(start, record, reason=note or "Source consulted")
    except (OSError, ValueError, TypeError, KeyError) as error:
        record["zotero"] = {"status": "blocked", "error": type(error).__name__}
    return record
