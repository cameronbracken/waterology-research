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


def work(identifier="148140180", **kwargs):
    return {
        "id": identifier,
        "title": "Advancing reservoir operations modelling in SWAT",
        "doi": "10.1016/J.ENVSOFT.2022.105527",
        "authors": [{"name": "Castelletti, A"}, {"name": "Zaniolo, M"}],
        "publishedDate": "2022-03-15T00:00:00+00:00",
        "yearPublished": 2022,
        "journals": [{"title": "Environmental Modelling & Software", "identifiers": []}],
        "publisher": "Elsevier",
        "downloadUrl": "https://core.ac.uk/download/567635389.pdf",
        "fullText": "Long parsed text that must not be retained.",
        "documentType": "research",
        "links": [{"type": "display", "url": "https://core.ac.uk/works/148140180"}],
        **kwargs,
    }


def test_request_auth_bounds_and_year_filter(monkeypatch):
    import urllib.request

    monkeypatch.setenv("CORE_API_KEY", "SECRET")
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            assert size == 32_000_001
            return b'{"results": []}'

    class Opener:
        def open(self, request, timeout):
            assert timeout == 30
            requests.append(request)
            return Response()

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
    assert literature.fetch_core(
        "reservoir operations", after="2021-03-01", before="2022-06-30", limit=3
    ) == {"results": []}
    request = requests[0]
    assert request.get_header("Authorization") == "Bearer SECRET"
    assert "SECRET" not in request.full_url
    assert urlparse(request.full_url).path == "/v3/search/works/"
    parameters = parse_qs(urlparse(request.full_url).query)
    assert parameters["q"] == [
        "(reservoir operations) AND yearPublished>=2021 AND yearPublished<=2022"
    ]
    assert parameters["limit"] == ["3"]
    monkeypatch.delenv("CORE_API_KEY")
    with pytest.warns(RuntimeWarning, match="CORE_API_KEY"):
        literature.fetch_core("fixture", after=None, before=None, limit=1)
    assert requests[-1].get_header("Authorization") is None
    assert parse_qs(urlparse(requests[-1].full_url).query)["q"] == ["fixture"]


def test_recorded_search_provenance_and_zotero_inclusion(project):
    result = literature.search_literature(
        project,
        "reservoir",
        provider="core",
        fetcher=lambda *a, **kw: {"results": [work(), work("999")]},
    )
    assert result["status"] == "complete"
    assert result["provider"] == "core"
    assert len(result["sources"]) == 1
    source = result["sources"][0]
    assert source["doi"] == "10.1016/j.envsoft.2022.105527"
    assert source["authors"] == ["Castelletti, A", "Zaniolo, M"]
    assert source["publication_date"] == "2022-03-15"
    assert source["venue"] == "Environmental Modelling & Software"
    assert source["pdf_url"] == "https://core.ac.uk/download/567635389.pdf"
    assert source["url"] == "https://core.ac.uk/works/148140180"
    assert not source["full_text_read"]
    assert "must not be retained" not in str(result)
    assert len(source["provenance"]) == 2
    assert all(p["provider"] == "core" for p in source["provenance"])
    saved = read_record(project / ".waterology/literature" / f"{result['id']}.yaml")
    assert saved == result
    literature.record_source_decision(
        project, result["id"], "148140180", decision="include", note="Relevant method"
    )
    assert reference_status(project)[0]["source"]["provider"] == "core"


def test_exact_dates_and_missing_metadata():
    sources = literature.normalize_core(
        [
            work(),
            work("old", doi="10.1/old", publishedDate="2022-01-01T00:00:00+00:00"),
            work("unknown", doi="", publishedDate="", yearPublished=2022),
        ],
        after="2022-03-01",
        before="2022-03-31",
    )
    assert [s["id"] for s in sources] == ["148140180"]
    unknown = literature.normalize_core(
        [
            work(
                doi="",
                authors=None,
                journals=[],
                publisher="",
                downloadUrl="",
                publishedDate=None,
                links=None,
                documentType="thesis",
            )
        ]
    )[0]
    assert unknown["publication_date"] is None
    assert unknown["doi"] is None
    assert unknown["authors"] == []
    assert unknown["venue"] == ""
    assert unknown["pdf_url"] is None
    assert unknown["url"] is None
    assert unknown["item_type"] == "thesis"


@pytest.mark.parametrize("payload", [{}, {"results": [None]}, {"results": [work(id=None, doi="")]}])
def test_malformed_provider_response_retained(project, payload):
    result = literature.search_literature(
        project, "fixture", provider="core", fetcher=lambda *a, **kw: payload
    )
    assert result["status"] == "unverified"


def test_rate_limit_failure_does_not_leak_credentials(project):
    def fail(*args, **kwargs):
        raise HTTPError("https://example.org/SECRET", 429, "SECRET", {}, None)

    result = literature.search_literature(project, "fixture", provider="core", fetcher=fail)
    assert result["status"] == "unverified"
    assert result["error"] == "HTTPError"
    assert "SECRET" not in str(result)


def test_cli_provider_selection(project, monkeypatch):
    monkeypatch.setattr(literature, "fetch_core", lambda *a, **kw: {"results": [work()]})
    result = CliRunner().invoke(
        app, ["discover", "reservoir", "--provider", "core", "--path", str(project)]
    )
    assert result.exit_code == 0, result.output
    assert "provider: core" in result.output
    assert "Advancing reservoir operations" in result.output
