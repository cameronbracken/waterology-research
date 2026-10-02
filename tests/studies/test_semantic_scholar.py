import json
import subprocess
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core import literature
from waterology.core.project import initialize_project
from waterology.core.zotero import reference_status


@pytest.fixture
def project(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    return tmp_path


def paper(identifier="abc", **kwargs):
    return {
        "paperId": identifier,
        "title": "Reservoir operations",
        "externalIds": {"DOI": "10.1/ABC"},
        "authors": [{"name": "Author"}],
        "publicationDate": "2024-05-10",
        "venue": "Journal",
        "url": "https://www.semanticscholar.org/paper/abc",
        "openAccessPdf": {"url": "https://example.org/paper.pdf"},
        **kwargs,
    }


def test_request_auth_bounds_and_year_filter(monkeypatch):
    import urllib.request

    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "SECRET")
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            assert size == 4_000_001
            return b'{"data": []}'

    class Opener:
        def open(self, request, timeout):
            assert timeout == 30
            requests.append(request)
            return Response()

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
    assert literature.fetch_semantic_scholar(
        "reservoir operations", after="2024-03-01", before=None, limit=3
    ) == {"data": []}
    request = requests[0]
    assert request.get_header("X-api-key") == "SECRET"
    assert "SECRET" not in request.full_url
    parameters = parse_qs(urlparse(request.full_url).query)
    assert parameters["year"] == ["2024-"]
    assert parameters["limit"] == ["3"]
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY")
    with pytest.warns(RuntimeWarning, match="SEMANTIC_SCHOLAR_API_KEY"):
        literature.fetch_semantic_scholar("fixture", after=None, before=None, limit=1)
    assert requests[-1].get_header("X-api-key") is None


def test_recorded_search_provenance_and_zotero_inclusion(project):
    result = literature.search_literature(
        project,
        "reservoir",
        provider="semantic-scholar",
        fetcher=lambda *a, **kw: {"data": [paper(), paper("def")]},
    )
    assert result["status"] == "complete"
    assert result["provider"] == "semantic-scholar"
    assert len(result["sources"]) == 1
    source = result["sources"][0]
    assert source["doi"] == "10.1/abc"
    assert source["authors"] == ["Author"]
    assert source["pdf_url"] == "https://example.org/paper.pdf"
    assert not source["full_text_read"]
    assert len(source["provenance"]) == 2
    assert all(p["provider"] == "semantic-scholar" for p in source["provenance"])
    saved = json.loads((project / ".waterology/literature" / f"{result['id']}.json").read_text())
    assert saved == result
    literature.record_source_decision(
        project, result["id"], "abc", decision="include", note="Relevant method"
    )
    assert reference_status(project)[0]["source"]["provider"] == "semantic-scholar"


def test_exact_dates_and_missing_metadata():
    sources = literature.normalize_semantic_scholar(
        [
            paper(),
            paper("old", publicationDate="2024-01-01"),
            paper("unknown", publicationDate=None, year=2024),
        ],
        after="2024-05-01",
        before="2024-05-31",
    )
    assert len(sources) == 1
    assert sources[0]["id"] == "abc"
    unknown = literature.normalize_semantic_scholar(
        [paper(externalIds=None, authors=None, openAccessPdf=None, publicationDate=None)]
    )[0]
    assert unknown["publication_date"] is None
    assert unknown["doi"] is None
    assert unknown["authors"] == []


@pytest.mark.parametrize(
    "payload", [{}, {"data": [None]}, {"data": [paper(paperId=None, externalIds=None)]}]
)
def test_malformed_provider_response_retained(project, payload):
    result = literature.search_literature(
        project, "fixture", provider="semantic-scholar", fetcher=lambda *a, **kw: payload
    )
    assert result["status"] == "unverified"


def test_rate_limit_failure_does_not_leak_credentials(project):
    def fail(*args, **kwargs):
        raise HTTPError("https://example.org/SECRET", 429, "SECRET", {}, None)

    result = literature.search_literature(
        project, "fixture", provider="semantic-scholar", fetcher=fail
    )
    assert result["status"] == "unverified"
    assert result["error"] == "HTTPError"
    assert "SECRET" not in str(result)


def test_cli_provider_selection(project, monkeypatch):
    monkeypatch.setattr(literature, "fetch_semantic_scholar", lambda *a, **kw: {"data": [paper()]})
    result = CliRunner().invoke(
        app, ["discover", "reservoir", "--provider", "semantic-scholar", "--path", str(project)]
    )
    assert result.exit_code == 0, result.output
    assert "semantic-scholar" in result.output
    assert "Reservoir operations" in result.output
    with pytest.raises(ValueError, match="Provider"):
        literature.search_literature(project, "fixture", provider="unknown")
