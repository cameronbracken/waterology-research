import json
import subprocess
from urllib.parse import parse_qs, urlparse

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core import literature
from waterology.core.atomic import read_record
from waterology.core.project import ProjectInitializationError, initialize_project


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "initialized"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    initialize_project(root)
    return root


def _mock_opener(monkeypatch, payloads):
    import urllib.request

    requests = []
    queue = list(payloads)

    class Response:
        def __init__(self, body: bytes):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size=-1):
            return self._body[:size] if size >= 0 else self._body

    class Opener:
        def open(self, request, timeout):
            assert timeout == 30
            requests.append(request)
            body = queue.pop(0) if len(queue) > 1 else queue[0]
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            return Response(body)

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
    return requests


def test_uninitialized_directory_search_succeeds_without_persisting_state(tmp_path, project):
    plain = tmp_path / "ad_hoc_notes"
    plain.mkdir()
    result = literature.search_literature(
        plain,
        "hydropower",
        provider="openalex",
        fetcher=lambda *a, **kw: {
            "results": [{"id": "W1", "doi": "10.1/npd", "display_name": "Non-powered dams"}]
        },
    )
    assert result["status"] == "complete"
    assert result["recorded"] is False
    assert len(result["sources"]) == 1
    assert not (plain / ".waterology").exists()

    # Repo with committed waterology.toml but no local .waterology directory also works unrecorded.
    cloned = tmp_path / "cloned_repo"
    cloned.mkdir()
    (cloned / "waterology.toml").write_text('name = "cloned"\n', encoding="utf-8")
    cloned_result = literature.search_literature(
        cloned,
        "hydropower",
        provider="openalex",
        fetcher=lambda *a, **kw: {"results": [{"id": "W2", "display_name": "Cloned search"}]},
    )
    assert cloned_result["recorded"] is False
    assert not (cloned / ".waterology").exists()

    # Symlinked .waterology state directory must still fail validation rather than fall back.
    outside = tmp_path / "outside"
    outside.mkdir()
    (cloned / ".waterology").symlink_to(outside)
    with pytest.raises(ProjectInitializationError):
        literature.search_literature(
            cloned, "hydropower", fetcher=lambda *a, **kw: {"results": []}
        )

    # Initialized project records state and keeps saved == result parity.
    recorded = literature.search_literature(
        project,
        "hydropower",
        provider="openalex",
        fetcher=lambda *a, **kw: {"results": [{"id": "W3", "display_name": "Recorded search"}]},
    )
    assert recorded["recorded"] is True
    saved = read_record(project / ".waterology/literature" / f"{recorded['id']}.yaml")
    assert saved == recorded


def test_cli_discover_works_outside_initialized_project(tmp_path, monkeypatch):
    monkeypatch.setattr(
        literature,
        "fetch_openalex",
        lambda *a, **kw: {"results": [{"id": "W9", "display_name": "Ad hoc CLI discovery"}]},
    )
    result = CliRunner().invoke(app, ["discover", "hydropower", "--path", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "recorded: false" in result.output
    assert "Ad hoc CLI discovery" in result.output


def test_arxiv_known_id_lookup_and_topic_rejection(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="known arXiv ID"):
        literature.search_literature(tmp_path, "streamflow forecasting topic", provider="arxiv")

    atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2310.06825v2</id>
        <published>2023-10-10T17:58:00Z</published>
        <title>  Mistral 7B
          Technical Report </title>
        <summary>Full abstract text that is not retained in metadata records.</summary>
        <author><name>Albert Q. Jiang</name></author>
        <author><name> Alexandre Sablayrolles </name></author>
        <arxiv:journal_ref>arXiv preprint</arxiv:journal_ref>
      </entry>
    </feed>"""
    requests = _mock_opener(monkeypatch, [atom_xml])
    result = literature.search_literature(
        tmp_path, "arXiv:2310.06825v2, https://arxiv.org/abs/math/0211159", provider="arxiv"
    )
    assert result["status"] == "complete"
    url = urlparse(requests[0].full_url)
    assert url.netloc == "export.arxiv.org"
    assert parse_qs(url.query)["id_list"] == ["2310.06825,math/0211159"]
    source = result["sources"][0]
    assert source["id"] == "2310.06825"
    assert source["doi"] == "10.48550/arxiv.2310.06825"
    assert source["title"] == "Mistral 7B Technical Report"
    assert source["authors"] == ["Albert Q. Jiang", "Alexandre Sablayrolles"]
    assert source["publication_date"] == "2023-10-10"
    assert source["item_type"] == "preprint"
    assert source["url"] == "https://arxiv.org/abs/2310.06825"
    assert source["pdf_url"] == "https://arxiv.org/pdf/2310.06825"
    assert "not retained" not in str(result)

    # Reject XML payloads containing DTD/entity declarations even past 4 KiB of prolog padding.
    _mock_opener(monkeypatch, [(" " * 5000) + "<!DOCTYPE feed><feed/>"])
    blocked = literature.search_literature(tmp_path, "2310.06825", provider="arxiv")
    assert blocked["status"] == "unverified"


def test_pubmed_search_summary_and_strict_dates(tmp_path, monkeypatch):
    esearch = {"esearchresult": {"idlist": ["38000000", "38000001"]}}
    esummary = {
        "result": {
            "uids": ["38000000", "38000001"],
            "38000000": {
                "uid": "38000000",
                "title": "Fish passage survival at low-head dams.",
                "pubdate": "2023 Nov 16",
                "epubdate": "",
                "fulljournalname": "River Research and Applications",
                "authors": [{"name": "Bracken C"}, {"name": "Smith J"}],
                "articleids": [
                    {"idtype": "pubmed", "value": "38000000"},
                    {"idtype": "doi", "value": "10.1002/RRA.4001"},
                    {"idtype": "pmc", "value": "PMC11930338"},
                ],
            },
            "38000001": {
                "uid": "38000001",
                "title": "Year-only PubMed entry",
                "pubdate": "2023 Nov",
                "epubdate": "",
                "source": "J Hydrol",
                "authors": [],
                "articleids": [],
            },
        }
    }
    requests = _mock_opener(monkeypatch, [esearch, esummary])
    result = literature.search_literature(
        tmp_path, "fish passage", provider="pubmed", after="2023-01-01", before="2023-12-31"
    )
    assert result["status"] == "complete"
    assert urlparse(requests[0].full_url).path.endswith("/esearch.fcgi")
    assert parse_qs(urlparse(requests[0].full_url).query)["mindate"] == ["2023/01/01"]
    assert urlparse(requests[1].full_url).path.endswith("/esummary.fcgi")
    # Year-month entry is excluded when date bounds are active rather than inventing a day.
    assert [s["id"] for s in result["sources"]] == ["38000000"]
    source = result["sources"][0]
    assert source["doi"] == "10.1002/rra.4001"
    assert source["publication_date"] == "2023-11-16"
    assert source["authors"] == ["Bracken C", "Smith J"]
    assert source["url"] == "https://pubmed.ncbi.nlm.nih.gov/38000000/"
    assert source["pdf_url"] == "https://pmc.ncbi.nlm.nih.gov/articles/PMC11930338/pdf/"


def test_europepmc_search_and_normalization(tmp_path, monkeypatch):
    payload = {
        "resultList": {
            "result": [
                {
                    "id": "39100001",
                    "source": "MED",
                    "doi": "10.1016/j.renene.2024.01.001",
                    "title": "Environmental flows for retrofitted dams",
                    "firstPublicationDate": "2024-02-14",
                    "authorList": {"author": [{"fullName": "Doe J"}]},
                    "journalInfo": {"journal": {"title": "Renewable Energy"}},
                    "pubTypeList": {"pubType": ["research-article"]},
                    "isOpenAccess": "Y",
                    "fullTextUrlList": {
                        "fullTextUrl": [
                            {
                                "documentStyle": "pdf",
                                "availabilityCode": "OA",
                                "url": "https://europepmc.org/articles/PMC1/pdf/main.pdf",
                            }
                        ]
                    },
                    "abstractText": "Abstract text dropped from discovery records.",
                }
            ]
        }
    }
    requests = _mock_opener(monkeypatch, [payload])
    result = literature.search_literature(
        tmp_path, "retrofitted dams", provider="europepmc", after="2024-01-01"
    )
    assert result["status"] == "complete"
    query_param = parse_qs(urlparse(requests[0].full_url).query)["query"][0]
    assert "FIRST_PDATE:[2024-01-01 TO 2999-12-31]" in query_param
    source = result["sources"][0]
    assert source["id"] == "MED:39100001"
    assert source["doi"] == "10.1016/j.renene.2024.01.001"
    assert source["publication_date"] == "2024-02-14"
    assert source["pdf_url"] == "https://europepmc.org/articles/PMC1/pdf/main.pdf"
    assert "Abstract text dropped" not in str(result)


@pytest.mark.parametrize("server", ["biorxiv", "medrxiv"])
def test_biorxiv_and_medrxiv_doi_and_bounded_window(tmp_path, monkeypatch, server):
    with pytest.raises(ValueError, match="DOI.*after and before"):
        literature.search_literature(tmp_path, "unbounded topic query", provider=server)
    with pytest.raises(ValueError, match="DOI.*after and before|Invalid"):
        literature.search_literature(
            tmp_path, "10.1101/../../2015-01-01/2025-12-31", provider=server
        )
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        literature.search_literature(
            tmp_path, "*", provider=server, after="20240101", before="2024-01-02"
        )

    collection = {
        "collection": [
            {
                "doi": "10.1101/2024.01.02.573000",
                "title": "Microbial dynamics in impounded reservoirs",
                "authors": "Sinha, A. K.; Lee, C.",
                "date": "2024-01-02",
                "version": "2",
                "category": "ecology",
                "abstract": "Long abstract not retained.",
                "server": server,
            }
        ]
    }
    requests = _mock_opener(monkeypatch, [collection, collection])
    by_doi = literature.search_literature(
        tmp_path, "https://doi.org/10.1101/2024.01.02.573000", provider=server
    )
    assert f"/details/{server}/10.1101/2024.01.02.573000/na/json" in requests[0].full_url
    source = by_doi["sources"][0]
    assert source["doi"] == "10.1101/2024.01.02.573000"
    assert source["authors"] == ["Sinha, A. K.", "Lee, C."]
    assert source["item_type"] == "preprint"
    assert source["pdf_url"] == f"https://www.{server}.org/content/10.1101/2024.01.02.573000v2.full.pdf"
    assert "Long abstract" not in str(by_doi)

    by_window = literature.search_literature(
        tmp_path,
        "category:ecology reservoirs",
        provider=server,
        after="2024-01-01",
        before="2024-01-07",
    )
    assert (
        f"/details/{server}/2024-01-01/2024-01-07/0/json?category=ecology"
        in requests[1].full_url
    )
    assert len(by_window["sources"]) == 1


def test_crossref_doi_and_bibliographic_provenance(tmp_path, monkeypatch):
    work_item = {
        "DOI": "10.2172/1039957",
        "title": ["An Assessment of Energy Potential at Non-Powered Dams in the United States"],
        "author": [{"given": "Boualem", "family": "Hadjerioua"}, {"name": "ORNL"}],
        "published": {"date-parts": [[2012, 4, 1]]},
        "container-title": ["Oak Ridge National Laboratory Technical Report"],
        "type": "report",
        "URL": "https://doi.org/10.2172/1039957",
        "link": [{"content-type": "application/pdf", "URL": "https://www.osti.gov/servlets/purl/1039957"}],
    }
    year_only = {
        "DOI": "10.1000/year-only",
        "title": ["Year-only Crossref Work"],
        "issued": {"date-parts": [[2020]]},
        "type": "journal-article",
    }
    requests = _mock_opener(
        monkeypatch,
        [
            {"status": "ok", "message": work_item},
            {"status": "ok", "message": {"items": [work_item, year_only]}},
        ],
    )
    by_doi = literature.search_literature(tmp_path, "10.2172/1039957", provider="crossref")
    assert urlparse(requests[0].full_url).path == "/works/10.2172%2F1039957"
    source = by_doi["sources"][0]
    assert source["doi"] == "10.2172/1039957"
    assert source["item_type"] == "report"
    assert source["publication_date"] == "2012-04-01"
    assert source["authors"] == ["Boualem Hadjerioua", "ORNL"]
    assert source["provenance"][0]["endpoint"] == "https://api.crossref.org/works/10.2172%2F1039957"

    by_query = literature.search_literature(
        tmp_path, "non-powered dams", provider="crossref", limit=5
    )
    assert urlparse(requests[1].full_url).path == "/works"
    assert len(by_query["sources"]) == 2
    assert by_query["sources"][1]["publication_date"] is None
    assert by_query["sources"][0]["provenance"][0]["endpoint"] == "https://api.crossref.org/works"
