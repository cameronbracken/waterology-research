import subprocess
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core import literature
from waterology.core.atomic import read_record
from waterology.core.project import initialize_project
from waterology.core.zotero import reference_status


@pytest.fixture
def project(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    return tmp_path


def hit(identifier="2610.20640", **kwargs):
    return {
        "paperId": identifier,
        "title": "Global streamflow forecasting with lead-aware probabilistic machine learning",
        "abstract": "Global streamflow forecasting supports flood preparedness.",
        "publicationDate": "2026-10-02T14:58:31.000Z",
        "votes": 0,
        "snippets": [{"pageNumber": 1, "snippet": "Matched full text that is not retained."}],
        **kwargs,
    }


@pytest.mark.parametrize(
    ("fetch", "strategy"),
    [("fetch_alphaxiv", "embedding"), ("fetch_alphaxiv_keyword", "keyword")],
)
def test_request_strategy_dates_and_bounds(monkeypatch, fetch, strategy):
    import urllib.request

    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            assert size == 4_000_001
            return b'[{"paperId": "2610.20640"}]'

    class Opener:
        def open(self, request, timeout):
            assert timeout == 30
            requests.append(request)
            return Response()

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
    payload = getattr(literature, fetch)(
        "streamflow forecasting", after="2021-03-01", before="2022-06-30", limit=3
    )
    # alphaXiv returns a bare list. The fetcher wraps it like the other providers.
    assert payload == {"results": [{"paperId": "2610.20640"}]}
    url = urlparse(requests[0].full_url)
    assert url.netloc == "api.alphaxiv.org"
    assert url.path == f"/search/v2/paper/discover/{strategy}"
    parameters = parse_qs(url.query)
    assert parameters["q"] == ["streamflow forecasting"]
    assert parameters["prioritize"] == ["default"]
    assert parameters["publishedAfter"] == ["2021-03-01"]
    assert parameters["publishedBefore"] == ["2022-06-30"]
    getattr(literature, fetch)("fixture", after=None, before=None, limit=1)
    parameters = parse_qs(urlparse(requests[-1].full_url).query)
    assert "publishedAfter" not in parameters
    assert "publishedBefore" not in parameters


def test_recorded_search_provenance_and_zotero_inclusion(project):
    result = literature.search_literature(
        project,
        "streamflow",
        provider="alphaxiv",
        fetcher=lambda *a, **kw: {"results": [hit(), hit("2610.20640v2")]},
    )
    assert result["status"] == "complete"
    assert result["provider"] == "alphaxiv"
    assert len(result["sources"]) == 1
    source = result["sources"][0]
    assert source["id"] == "2610.20640"
    assert source["doi"] == "10.48550/arxiv.2610.20640"
    assert source["item_type"] == "preprint"
    assert source["publication_date"] == "2026-10-02"
    assert source["venue"] == "arXiv"
    assert source["authors"] == []
    assert source["url"] == "https://www.alphaxiv.org/abs/2610.20640"
    assert source["pdf_url"] == "https://arxiv.org/pdf/2610.20640"
    assert not source["full_text_read"]
    assert "not retained" not in str(result)
    assert len(source["provenance"]) == 2
    assert all(p["provider"] == "alphaxiv" for p in source["provenance"])
    saved = read_record(project / ".waterology/literature" / f"{result['id']}.yaml")
    assert saved == result
    literature.record_source_decision(
        project, result["id"], "2610.20640", decision="include", note="Relevant method"
    )
    assert reference_status(project)[0]["source"]["provider"] == "alphaxiv"


def test_keyword_provider_is_recorded_separately(project):
    result = literature.search_literature(
        project,
        "LSTM",
        provider="alphaxiv-keyword",
        fetcher=lambda *a, **kw: {"results": [hit()]},
    )
    assert result["status"] == "complete"
    assert result["sources"][0]["provider"] == "alphaxiv-keyword"


def test_old_style_identifier_dates_and_missing_metadata():
    sources = literature.normalize_alphaxiv(
        [
            hit(),
            hit("2601.00001", publicationDate="2026-01-01T00:00:00.000Z"),
            hit("2601.00002", publicationDate=None),
        ],
        after="2026-10-01",
        before="2026-10-31",
    )
    assert [s["id"] for s in sources] == ["2610.20640"]
    old = literature.normalize_alphaxiv([hit("math/0211159v1", publicationDate=None)])[0]
    assert old["id"] == "math/0211159"
    assert old["doi"] == "10.48550/arxiv.math/0211159"
    assert old["publication_date"] is None
    assert old["url"] == "https://www.alphaxiv.org/abs/math/0211159"
    # Only arXiv identifiers receive a derived DOI.
    other = literature.normalize_alphaxiv([hit("not-an-arxiv-id")])[0]
    assert other["doi"] is None
    assert other["pdf_url"] is None


@pytest.mark.parametrize("payload", [{}, {"results": [None]}, {"results": [hit(paperId=None)]}])
def test_malformed_provider_response_retained(project, payload):
    result = literature.search_literature(
        project, "fixture", provider="alphaxiv", fetcher=lambda *a, **kw: payload
    )
    assert result["status"] == "unverified"


def test_rate_limit_failure_is_recorded(project):
    def fail(*args, **kwargs):
        raise HTTPError("https://api.alphaxiv.org/search", 429, "Too Many Requests", {}, None)

    result = literature.search_literature(project, "fixture", provider="alphaxiv", fetcher=fail)
    assert result["status"] == "unverified"
    assert result["error"] == "HTTPError"


def test_cli_provider_selection(project, monkeypatch):
    monkeypatch.setattr(literature, "fetch_alphaxiv_keyword", lambda *a, **kw: {"results": [hit()]})
    result = CliRunner().invoke(
        app, ["discover", "LSTM", "--provider", "alphaxiv-keyword", "--path", str(project)]
    )
    assert result.exit_code == 0, result.output
    assert "provider: alphaxiv-keyword" in result.output
    assert "Global streamflow forecasting" in result.output
