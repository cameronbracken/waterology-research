"""Additional bounded scholarly providers for portable source coverage."""

import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from urllib.parse import quote, urlencode
from urllib.request import Request

ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5}|[a-z-]+(\.[A-Z]{2})?/\d{7})")
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s?#]+", re.IGNORECASE)
RXIV_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[A-Za-z0-9._-]+", re.IGNORECASE)
ISO_DAY_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
CATEGORY_TOKEN = re.compile(r"^category:([A-Za-z0-9_-]+)$", re.IGNORECASE)
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
USER_AGENT = "Waterology literature discovery"
MAX_RXIV_DAYS = 90
MAX_RXIV_PAGES = 5


def read_bytes_without_redirects(request: Request, bound: int) -> bytes:
    """Read a bounded response without following redirects."""
    from urllib.request import HTTPRedirectHandler, build_opener

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        payload = response.read(bound + 1)
    if len(payload) > bound:
        raise ValueError("Provider response exceeds the bounded read limit")
    return payload


def read_prefix_without_redirects(request: Request, max_bytes: int) -> tuple[bytes, bool]:
    """Read at most max_bytes without following redirects, reporting truncation."""
    from urllib.request import HTTPRedirectHandler, build_opener

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        payload = response.read(max_bytes + 1)
    return payload[:max_bytes], len(payload) > max_bytes


def read_json_without_redirects(request: Request, bound: int) -> dict | list:
    return json.loads(read_bytes_without_redirects(request, bound))


def canonical_iso_day(raw: str | None) -> str | None:
    if not isinstance(raw, str):
        return None
    candidate = raw.strip()[:10]
    if not ISO_DAY_PATTERN.fullmatch(candidate):
        return None
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return None


def _clean_doi(raw: str) -> str | None:
    candidate = raw.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if candidate.lower().startswith(prefix):
            candidate = candidate[len(prefix) :].strip()
    if ".." in candidate or not DOI_PATTERN.fullmatch(candidate):
        return None
    return candidate


def parse_arxiv_ids(query: str, limit: int) -> list[str]:
    tokens = [t.strip() for t in re.split(r"[\s,]+", query.strip()) if t.strip()]
    if not tokens:
        raise ValueError(
            "arXiv provider supports known arXiv ID lookup only; use alphaxiv for topic search"
        )
    identifiers = []
    for token in tokens[:limit]:
        cleaned = token
        for prefix in (
            "https://arxiv.org/abs/",
            "http://arxiv.org/abs/",
            "https://arxiv.org/pdf/",
            "http://arxiv.org/pdf/",
            "arxiv:",
            "arXiv:",
        ):
            cleaned = cleaned.removeprefix(prefix)
        cleaned = cleaned.removesuffix(".pdf")
        cleaned = re.sub(r"v\d+$", "", cleaned)
        if not ARXIV_ID.fullmatch(cleaned):
            raise ValueError(
                "arXiv provider supports known arXiv ID lookup only; use alphaxiv for topic search"
            )
        if cleaned not in identifiers:
            identifiers.append(cleaned)
    return identifiers


def fetch_arxiv(query: str, *, after: str | None, before: str | None, limit: int) -> dict:
    identifiers = parse_arxiv_ids(query, limit)
    request = Request(
        "https://export.arxiv.org/api/query?"
        + urlencode({"id_list": ",".join(identifiers), "max_results": len(identifiers)}),
        headers={"User-Agent": USER_AGENT},
    )
    raw_xml = read_bytes_without_redirects(request, 4_000_000)
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", raw_xml, re.IGNORECASE):
        raise ValueError("Refusing XML response with DTD or entity declarations")
    root = ET.fromstring(raw_xml.decode("utf-8"))
    entries = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        entry_id = (entry.findtext(f"{ATOM_NS}id") or "").strip()
        if "/abs/" not in entry_id:
            continue
        identifier = re.sub(r"v\d+$", "", entry_id.rsplit("/abs/", 1)[-1].strip())
        if not ARXIV_ID.fullmatch(identifier):
            continue
        title = " ".join((entry.findtext(f"{ATOM_NS}title") or "").split())
        published = canonical_iso_day(entry.findtext(f"{ATOM_NS}published"))
        authors = [
            " ".join((author.findtext(f"{ATOM_NS}name") or "").split())
            for author in entry.findall(f"{ATOM_NS}author")
            if (author.findtext(f"{ATOM_NS}name") or "").strip()
        ]
        explicit_doi = (entry.findtext(f"{ARXIV_NS}doi") or "").strip() or None
        journal_ref = " ".join((entry.findtext(f"{ARXIV_NS}journal_ref") or "").split())
        entries.append(
            {
                "id": identifier,
                "doi": explicit_doi or f"10.48550/arXiv.{identifier}",
                "title": title,
                "publication_date": published,
                "authors": authors,
                "venue": journal_ref or "arXiv",
            }
        )
    return {"results": entries}


def normalize_arxiv(results: list[dict], *, after=None, before=None) -> list[dict]:
    from waterology.core.literature import _outside_dates, _tag_provider, normalize_sources

    converted = []
    for item in results:
        if not isinstance(item, dict):
            raise TypeError("Provider result must be an object")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("Source lacks an identifier")
        publication_date = item.get("publication_date")
        if _outside_dates(publication_date, after, before):
            continue
        converted.append(
            {
                "id": identifier,
                "doi": item.get("doi") or f"10.48550/arXiv.{identifier}",
                "title": item.get("title"),
                "publication_date": publication_date,
                "authorships": [
                    {"author": {"display_name": name}} for name in (item.get("authors") or [])
                ],
                "primary_location": {
                    "source": {"display_name": item.get("venue") or "arXiv"},
                    "landing_page_url": f"https://arxiv.org/abs/{identifier}",
                },
                "best_oa_location": {"pdf_url": f"https://arxiv.org/pdf/{identifier}"},
                "type": "preprint",
            }
        )
    return _tag_provider(normalize_sources(converted), "arxiv")


MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _parse_pubmed_date(*candidates: str | None) -> str | None:
    for raw in candidates:
        if not raw:
            continue
        cleaned = " ".join(raw.strip().split())
        try:
            return date.fromisoformat(cleaned.replace("/", "-")).isoformat()
        except ValueError:
            pass
        parts = cleaned.split(" ")
        if len(parts) == 3 and parts[1][:3].lower() in MONTHS:
            try:
                return date(int(parts[0]), MONTHS[parts[1][:3].lower()], int(parts[2])).isoformat()
            except ValueError:
                continue
    return None


def fetch_pubmed(query: str, *, after: str | None, before: str | None, limit: int) -> dict:
    search_params: dict[str, str | int] = {
        "db": "pubmed",
        "retmode": "json",
        "retmax": limit,
        "term": query,
    }
    if after or before:
        search_params["datetype"] = "pdat"
        search_params["mindate"] = (after or "1800-01-01").replace("-", "/")
        search_params["maxdate"] = (before or "2999-12-31").replace("-", "/")
    search_req = Request(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode(search_params),
        headers={"User-Agent": USER_AGENT},
    )
    search_payload = read_json_without_redirects(search_req, 4_000_000)
    if not isinstance(search_payload, dict):
        raise TypeError("Unexpected PubMed search payload")
    ids = ((search_payload.get("esearchresult") or {}).get("idlist")) or []
    if not isinstance(ids, list):
        raise TypeError("PubMed idlist must be a list")
    if not ids:
        return {"results": []}
    summary_req = Request(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
        + urlencode({"db": "pubmed", "retmode": "json", "id": ",".join(str(i) for i in ids[:limit])}),
        headers={"User-Agent": USER_AGENT},
    )
    summary_payload = read_json_without_redirects(summary_req, 4_000_000)
    if not isinstance(summary_payload, dict) or not isinstance(summary_payload.get("result"), dict):
        raise TypeError("Unexpected PubMed summary payload")
    result_map = summary_payload["result"]
    uids = result_map.get("uids") or []
    return {"results": [result_map[str(uid)] for uid in uids if str(uid) in result_map]}


def normalize_pubmed(results: list[dict], *, after=None, before=None) -> list[dict]:
    from waterology.core.literature import _outside_dates, _tag_provider, normalize_sources

    converted = []
    for item in results:
        if not isinstance(item, dict):
            raise TypeError("Provider result must be an object")
        uid = str(item["uid"]) if item.get("uid") is not None else None
        if not uid:
            raise ValueError("Source lacks an identifier")
        publication_date = _parse_pubmed_date(item.get("epubdate"), item.get("pubdate"))
        if _outside_dates(publication_date, after, before):
            continue
        article_ids = item.get("articleids") or []
        doi = next(
            (entry.get("value") for entry in article_ids if entry.get("idtype") == "doi"),
            None,
        )
        pmc = next(
            (entry.get("value") for entry in article_ids if entry.get("idtype") == "pmc"),
            None,
        )
        title = (item.get("title") or "").rstrip(".")
        converted.append(
            {
                "id": uid,
                "doi": doi,
                "title": title,
                "publication_date": publication_date,
                "authorships": [
                    {"author": {"display_name": a.get("name")}}
                    for a in (item.get("authors") or [])
                    if isinstance(a, dict) and a.get("name")
                ],
                "primary_location": {
                    "source": {
                        "display_name": item.get("fulljournalname") or item.get("source") or ""
                    },
                    "landing_page_url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                },
                "best_oa_location": {
                    "pdf_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc}/pdf/" if pmc else None
                },
                "type": "article",
            }
        )
    return _tag_provider(normalize_sources(converted), "pubmed")


def fetch_europepmc(query: str, *, after: str | None, before: str | None, limit: int) -> dict:
    full_query = query
    if after or before:
        full_query = f"({query}) AND FIRST_PDATE:[{after or '1900-01-01'} TO {before or '2999-12-31'}]"
    request = Request(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
        + urlencode(
            {
                "query": full_query,
                "format": "json",
                "pageSize": limit,
                "resultType": "core",
            }
        ),
        headers={"User-Agent": USER_AGENT},
    )
    payload = read_json_without_redirects(request, 8_000_000)
    if not isinstance(payload, dict):
        raise TypeError("Unexpected Europe PMC payload")
    results = (payload.get("resultList") or {}).get("result")
    return {"results": results}


def normalize_europepmc(results: list[dict], *, after=None, before=None) -> list[dict]:
    from waterology.core.literature import _outside_dates, _tag_provider, normalize_sources

    converted = []
    for item in results:
        if not isinstance(item, dict):
            raise TypeError("Provider result must be an object")
        raw_id = item.get("id")
        source_code = item.get("source") or "MED"
        identifier = f"{source_code}:{raw_id}" if raw_id else None
        publication_date = canonical_iso_day(item.get("firstPublicationDate"))
        if _outside_dates(publication_date, after, before):
            continue
        authors = ((item.get("authorList") or {}).get("author")) or []
        journal = (((item.get("journalInfo") or {}).get("journal")) or {}).get("title") or ""
        pub_types = [t.lower() for t in (((item.get("pubTypeList") or {}).get("pubType")) or [])]
        urls = ((item.get("fullTextUrlList") or {}).get("fullTextUrl")) or []
        pdf_url = next(
            (
                u.get("url")
                for u in urls
                if isinstance(u, dict)
                and (u.get("documentStyle") or "").lower() == "pdf"
                and (u.get("availabilityCode") or "").upper() in {"OA", "F"}
            ),
            None,
        )
        converted.append(
            {
                "id": identifier,
                "doi": item.get("doi") or None,
                "title": item.get("title"),
                "publication_date": publication_date,
                "authorships": [
                    {"author": {"display_name": a.get("fullName") or a.get("lastName")}}
                    for a in authors
                    if isinstance(a, dict) and (a.get("fullName") or a.get("lastName"))
                ],
                "primary_location": {
                    "source": {"display_name": journal},
                    "landing_page_url": (
                        f"https://europepmc.org/article/{source_code}/{raw_id}" if raw_id else None
                    ),
                },
                "best_oa_location": {"pdf_url": pdf_url},
                "open_access": item.get("isOpenAccess") == "Y"
                if item.get("isOpenAccess") in {"Y", "N"}
                else None,
                "type": "preprint" if "preprint" in pub_types else "article",
            }
        )
    return _tag_provider(normalize_sources(converted), "europepmc")


def validate_rxiv_query(
    server: str, query: str, *, after: str | None, before: str | None
) -> str | None:
    doi = _clean_doi(query)
    if doi:
        if not RXIV_DOI_PATTERN.fullmatch(doi):
            raise ValueError(f"Invalid {server} preprint DOI")
        return doi
    if not (after and before):
        raise ValueError(
            f"{server} provider requires a preprint DOI or both after and before dates"
        )
    span = (date.fromisoformat(before) - date.fromisoformat(after)).days
    if span > MAX_RXIV_DAYS:
        raise ValueError(f"{server} bounded date retrieval cannot exceed {MAX_RXIV_DAYS} days")
    return None


def _fetch_rxiv(
    server: str, query: str, *, after: str | None, before: str | None, limit: int
) -> dict:
    doi = validate_rxiv_query(server, query, after=after, before=before)
    if doi:
        prefix, suffix = doi.split("/", 1)
        url = (
            f"https://api.biorxiv.org/details/{server}/"
            f"{quote(prefix, safe='')}/{quote(suffix, safe='')}/na/json"
        )
        payload = read_json_without_redirects(
            Request(url, headers={"User-Agent": USER_AGENT}), 8_000_000
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("collection"), list):
            raise TypeError(f"Unexpected {server} payload")
        return {"results": payload["collection"][:limit]}

    category = None
    terms = []
    for token in query.split():
        cleaned = token.strip()
        if not cleaned or cleaned == "*":
            continue
        match = CATEGORY_TOKEN.fullmatch(cleaned)
        if match and category is None:
            category = match.group(1).lower()
        else:
            terms.append(cleaned.lower())

    matched = []
    for page in range(MAX_RXIV_PAGES):
        cursor = page * 100
        url = f"https://api.biorxiv.org/details/{server}/{after}/{before}/{cursor}/json"
        if category:
            url += "?" + urlencode({"category": category})
        payload = read_json_without_redirects(
            Request(url, headers={"User-Agent": USER_AGENT}), 8_000_000
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("collection"), list):
            raise TypeError(f"Unexpected {server} payload")
        collection = payload["collection"]
        for item in collection:
            if not isinstance(item, dict):
                continue
            if terms:
                haystack = " ".join(
                    str(item.get(field) or "")
                    for field in ("title", "abstract", "category", "authors")
                ).lower()
                if not all(term in haystack for term in terms):
                    continue
            matched.append(item)
            if len(matched) >= limit:
                return {"results": matched}
        if len(collection) < 100:
            break
    return {"results": matched}


def fetch_biorxiv(query: str, *, after: str | None, before: str | None, limit: int) -> dict:
    return _fetch_rxiv("biorxiv", query, after=after, before=before, limit=limit)


def fetch_medrxiv(query: str, *, after: str | None, before: str | None, limit: int) -> dict:
    return _fetch_rxiv("medrxiv", query, after=after, before=before, limit=limit)


def _normalize_rxiv(server: str, results: list[dict], *, after=None, before=None) -> list[dict]:
    from waterology.core.literature import _outside_dates, _tag_provider, normalize_sources

    venue = "bioRxiv" if server == "biorxiv" else "medRxiv"
    converted = []
    for item in results:
        if not isinstance(item, dict):
            raise TypeError("Provider result must be an object")
        doi = (item.get("doi") or "").strip() or None
        publication_date = canonical_iso_day(item.get("date"))
        if _outside_dates(publication_date, after, before):
            continue
        version = str(item.get("version") or "").strip()
        suffix = f"v{version}" if version else ""
        authors = [a.strip() for a in (item.get("authors") or "").split(";") if a.strip()]
        # Abstracts are omitted so discovery records stay compact and never mark full text read.
        converted.append(
            {
                "id": doi,
                "doi": doi,
                "title": item.get("title"),
                "publication_date": publication_date,
                "authorships": [{"author": {"display_name": name}} for name in authors],
                "primary_location": {
                    "source": {"display_name": venue},
                    "landing_page_url": (
                        f"https://www.{server}.org/content/{doi}{suffix}" if doi else None
                    ),
                },
                "best_oa_location": {
                    "pdf_url": (
                        f"https://www.{server}.org/content/{doi}{suffix}.full.pdf" if doi else None
                    )
                },
                "type": "preprint",
            }
        )
    return _tag_provider(normalize_sources(converted), server)


def normalize_biorxiv(results: list[dict], *, after=None, before=None) -> list[dict]:
    return _normalize_rxiv("biorxiv", results, after=after, before=before)


def normalize_medrxiv(results: list[dict], *, after=None, before=None) -> list[dict]:
    return _normalize_rxiv("medrxiv", results, after=after, before=before)


def _crossref_date(item: dict) -> str | None:
    for field in ("published", "published-print", "published-online", "issued"):
        parts_list = ((item.get(field) or {}).get("date-parts")) or []
        if parts_list and isinstance(parts_list[0], list) and len(parts_list[0]) >= 3:
            year, month, day = parts_list[0][:3]
            if all(isinstance(v, int) for v in (year, month, day)):
                try:
                    return date(year, month, day).isoformat()
                except ValueError:
                    continue
    return None


CROSSREF_TYPES = {
    "posted-content": "preprint",
    "book": "book",
    "monograph": "book",
    "edited-book": "book",
    "book-chapter": "book-chapter",
    "book-section": "book-chapter",
    "dissertation": "dissertation",
    "report": "report",
    "report-component": "report",
    "dataset": "dataset",
}


def fetch_crossref(query: str, *, after: str | None, before: str | None, limit: int) -> dict:
    doi = _clean_doi(query)
    if doi:
        endpoint = f"https://api.crossref.org/works/{quote(doi, safe='')}"
        payload = read_json_without_redirects(
            Request(endpoint, headers={"User-Agent": USER_AGENT}), 4_000_000
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
            raise TypeError("Unexpected Crossref DOI payload")
        item = dict(payload["message"])
        item["_endpoint"] = endpoint
        return {"results": [item]}

    endpoint = "https://api.crossref.org/works"
    params: dict[str, str | int] = {"query.bibliographic": query, "rows": limit}
    filters = []
    if after:
        filters.append(f"from-pub-date:{after}")
    if before:
        filters.append(f"until-pub-date:{before}")
    if filters:
        params["filter"] = ",".join(filters)
    payload = read_json_without_redirects(
        Request(f"{endpoint}?{urlencode(params)}", headers={"User-Agent": USER_AGENT}), 8_000_000
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
        raise TypeError("Unexpected Crossref search payload")
    items = payload["message"].get("items")
    if not isinstance(items, list):
        raise TypeError("Crossref items must be a list")
    tagged = []
    for item in items:
        if not isinstance(item, dict):
            raise TypeError("Provider result must be an object")
        copy = dict(item)
        copy["_endpoint"] = endpoint
        tagged.append(copy)
    return {"results": tagged}


def normalize_crossref(results: list[dict], *, after=None, before=None) -> list[dict]:
    from waterology.core.literature import _outside_dates, _tag_provider, normalize_sources

    converted = []
    endpoints_by_doi: dict[str, list[str]] = {}
    for item in results:
        if not isinstance(item, dict):
            raise TypeError("Provider result must be an object")
        raw_doi = item.get("DOI") or item.get("doi")
        doi = raw_doi.strip() if isinstance(raw_doi, str) and raw_doi.strip() else None
        publication_date = _crossref_date(item)
        if _outside_dates(publication_date, after, before):
            continue
        titles = item.get("title") or []
        title = titles[0] if isinstance(titles, list) and titles else None
        containers = item.get("container-title") or []
        venue = (
            containers[0]
            if isinstance(containers, list) and containers
            else (item.get("publisher") or "")
        )
        authors = []
        for author in item.get("author") or []:
            if not isinstance(author, dict):
                continue
            full = " ".join(p for p in (author.get("given"), author.get("family")) if p).strip()
            name = full or (author.get("name") or "").strip()
            if name:
                authors.append({"author": {"display_name": name}})
        links = item.get("link") or []
        pdf_url = next(
            (
                link.get("URL")
                for link in links
                if isinstance(link, dict)
                and (link.get("content-type") or "").lower() == "application/pdf"
            ),
            None,
        )
        endpoint = item.get("_endpoint") or "https://api.crossref.org/works"
        if doi:
            endpoints_by_doi.setdefault(doi.lower(), []).append(endpoint)
        converted.append(
            {
                "id": doi,
                "doi": doi,
                "title": title,
                "publication_date": publication_date,
                "authorships": authors,
                "primary_location": {
                    "source": {"display_name": venue},
                    "landing_page_url": item.get("URL") or (f"https://doi.org/{doi}" if doi else None),
                },
                "best_oa_location": {"pdf_url": pdf_url},
                "type": CROSSREF_TYPES.get((item.get("type") or "").lower(), "article"),
            }
        )
    sources = _tag_provider(normalize_sources(converted), "crossref")
    for source in sources:
        endpoints = endpoints_by_doi.get(source.get("doi") or "", [])
        for index, provenance in enumerate(source["provenance"]):
            provenance["endpoint"] = (
                endpoints[index] if index < len(endpoints) else "https://api.crossref.org/works"
            )
    return sources
