import hashlib
import subprocess

import pytest

from waterology.core.formats import load_document, write_document
from waterology.core.project import initialize_project
from waterology.core.zotero import (
    configure_zotero,
    queue_reference,
    reference_status,
    settings_for,
    sync_references,
)

LEGACY_SETTINGS = "library_id: 123\ncollection_name: Legacy fixture\ncollection_key: ABCDEFGH\n"


@pytest.fixture
def project(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    configure_zotero(tmp_path, {"library_id": "123", "collection_name": "Fixture"})
    return tmp_path


class Gateway:
    def __init__(self):
        self.items = set()
        self.attachments = set()
        self.collections = 0

    def collection(self, settings):
        self.collections += 1

    def item(self, record, collection):
        self.items.add(record["item_key"])
        return record["item_key"]

    def attachment(self, record, path):
        self.attachments.add(record["attachment_key"])
        pytest.fail("PDF uploads are forbidden")


def test_configure_writes_canonical_hidden_settings_file(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)

    configure_zotero(tmp_path, {"library_id": "123", "collection_name": "Fixture"})

    assert (tmp_path / ".zotero.toml").is_file()
    assert not (tmp_path / "zotero.nt").exists()


def test_settings_read_legacy_file_when_canonical_file_is_absent(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    (tmp_path / "zotero.nt").write_text(LEGACY_SETTINGS)

    assert settings_for(tmp_path).collection_name == "Legacy fixture"


def test_settings_prefer_canonical_file_over_legacy_file(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    settings = {
        "library_id": "123",
        "collection_name": "Legacy fixture",
        "collection_key": "ABCDEFGH",
    }
    (tmp_path / "zotero.nt").write_text(LEGACY_SETTINGS)
    write_document(
        tmp_path / ".zotero.toml",
        {**settings, "library_id": "456", "collection_name": "Canonical fixture"},
    )

    loaded = settings_for(tmp_path)

    assert loaded.library_id == "456"
    assert loaded.collection_name == "Canonical fixture"


def test_doi_dedup_caches_pdf_without_upload(project):
    source = {
        "title": "Fixture",
        "doi": "https://doi.org/10.1234/ABC",
        "pdf_url": "https://example.org/paper.pdf",
    }
    first = queue_reference(project, source, reason="read", sync=False)
    second = queue_reference(project, {**source, "doi": "10.1234/abc"}, reason="cited", sync=False)
    assert first["id"] == second["id"]
    gateway = Gateway()
    downloads = []

    def download(url):
        downloads.append(url)
        return b"%PDF-1.7\nfixture"

    result = sync_references(project, gateway=gateway, downloader=download)
    assert result["status"] == "complete"
    record = result["references"][0]
    assert record["metadata_status"] == "synced"
    assert record["pdf_status"] == "downloaded"
    cached = project / ".waterology/references/pdfs" / f"{record['pdf_sha256']}.pdf"
    assert cached.read_bytes() == b"%PDF-1.7\nfixture"
    assert not gateway.attachments
    result = sync_references(
        project, gateway=gateway, downloader=lambda u: pytest.fail("must reuse bytes")
    )
    assert result["status"] == "complete"
    assert result["references"] == []
    assert len(gateway.items) == len(downloads) == 1


@pytest.mark.parametrize("legacy_status", ["pending", "downloaded"])
def test_failed_upload_resumes_from_pinned_local_pdf(project, legacy_status):
    source = project / "fixture.pdf"
    source.write_bytes(b"%PDF-1.7\nfixture")
    record = queue_reference(
        project, {"title": "Fixture", "pdf_path": "fixture.pdf"}, reason="read", sync=False
    )
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    directory = project / ".waterology/references"
    (directory / "pdfs").mkdir()
    cached = directory / "pdfs" / f"{digest}.pdf"
    cached.write_bytes(source.read_bytes())
    record.update(pdf_sha256=digest, pdf_status=legacy_status, error="RequestEntityTooLargeError")
    write_document(directory / f"ref-{record['id']}.yaml", record)
    source.unlink()
    gateway = Gateway()
    result = sync_references(project, gateway=gateway)
    assert result["status"] == "complete"
    assert result["references"][0]["pdf_status"] == "downloaded"
    assert "error" not in reference_status(project)[0]
    assert cached.read_bytes() == b"%PDF-1.7\nfixture"
    assert not gateway.attachments


def test_pending_work_not_starved_by_finished_records(project):
    gateway = Gateway()
    for n in range(3):
        queue_reference(
            project, {"title": f"Paper {n}", "doi": f"10.1234/{n}"}, reason="cited", sync=False
        )
    for _ in range(3):
        sync_references(project, limit=1, gateway=gateway)
    assert len(gateway.items) == 3


def test_library_change_blocks_before_remote_mutation(project):
    queue_reference(project, {"title": "Paper", "doi": "10.1234/test"}, reason="cited", sync=False)
    gateway = Gateway()
    sync_references(project, gateway=gateway)
    settings = load_document(project / ".zotero.toml")
    settings["library_id"] = "456"
    write_document(project / ".zotero.toml", settings)
    result = sync_references(project, gateway=gateway)
    assert result["status"] == "partial"
    assert result["references"][0]["status"] == "blocked"
    assert gateway.collections == 1


def test_same_agency_locator_is_one_reference(project):
    for identifier in ("source-one", "source-two"):
        queue_reference(
            project,
            {
                "provider": "local",
                "id": identifier,
                "title": "Agency report",
                "locator": "notes/report.pdf",
            },
            reason="read",
            sync=False,
        )
    assert len(reference_status(project)) == 1


def test_reference_without_doi_uses_stable_url(project):
    first = queue_reference(
        project,
        {"title": "Agency report", "url": "https://example.org/report#first"},
        reason="read",
        sync=False,
    )
    second = queue_reference(
        project,
        {"title": "Agency report", "url": "https://example.org/report#second"},
        reason="cited",
        sync=False,
    )
    assert first["id"] == second["id"]


def test_html_is_not_accepted_as_pdf(project):
    queue_reference(
        project,
        {"title": "Paper", "doi": "10.1234/test", "pdf_url": "https://example.org/paywall"},
        reason="read",
        sync=False,
    )
    result = sync_references(project, gateway=Gateway(), downloader=lambda u: b"<html>login</html>")
    assert result["status"] == "partial"
    assert result["references"][0]["pdf_status"] == "pending"
    assert result["references"][0]["metadata_status"] == "synced"


def test_sensitive_url_refused_before_persistence(project):
    with pytest.raises(ValueError, match="credentials"):
        queue_reference(
            project,
            {"title": "Paper", "url": "https://example.org?api_key=PRIVATE", "doi": "10.1234/test"},
            reason="read",
            sync=False,
        )
    assert reference_status(project) == []


def test_enrichment_preserves_reference_and_attachment_identity(project):
    source = {"provider": "openalex", "id": "https://openalex.org/W123", "title": "Paper"}
    first = queue_reference(project, source, reason="read", sync=False)
    enriched = queue_reference(
        project, {**source, "doi": "10.1234/test"}, reason="cited", sync=False
    )
    assert first["id"] == enriched["id"]
    assert first["item_key"] == enriched["item_key"]
    assert first["attachment_key"] == enriched["attachment_key"]
    assert len(reference_status(project)) == 1


def test_completed_metadata_is_resynced_when_doi_is_discovered(project):
    source = {"provider": "openalex", "id": "https://openalex.org/W123", "title": "Paper"}
    first = queue_reference(project, source, reason="read", sync=False)
    gateway = Gateway()
    assert sync_references(project, gateway=gateway)["status"] == "complete"
    enriched = queue_reference(
        project, {**source, "doi": "10.1234/test"}, reason="cited", sync=False
    )
    assert enriched["metadata_status"] == "pending"
    assert (
        sync_references(project, gateway=gateway)["references"][0]["source"]["doi"]
        == "10.1234/test"
    )
    assert len(gateway.items) == 1
    assert reference_status(project)[0]["item_key"] == first["item_key"]


def test_credential_fragment_is_rejected(project):
    with pytest.raises(ValueError, match="credentials"):
        queue_reference(
            project,
            {
                "title": "Paper",
                "doi": "10.1234/test",
                "url": "https://example.org/#access_token=PRIVATE",
            },
            reason="read",
            sync=False,
        )


def test_bounded_sync_reports_remaining_and_rotates_failed_records(project):
    gateway = Gateway()
    for n in range(3):
        queue_reference(
            project,
            {"title": f"Paper {n}", "doi": f"10.1234/{n}", "pdf_url": "https://example.org/p.pdf"},
            reason="read",
            sync=False,
        )
    visited = []

    def fail(record, collection):
        visited.append(record["id"])
        raise TimeoutError("unavailable")

    gateway.item = fail
    for _ in range(3):
        result = sync_references(project, limit=1, gateway=gateway)
        assert result["status"] == "partial"
        assert result["remaining"] == 3
    assert len(set(visited)) == 3


def test_bad_optional_settings_preserve_search_result(project):
    from waterology.core.literature import search_literature

    (project / ".zotero.toml").write_text("invalid = [broken\n")
    result = search_literature(project, "fixture", fetcher=lambda *a, **kw: {"results": []})
    assert result["status"] == "complete"
    assert result["zotero"]["status"] == "blocked"
    assert (project / ".waterology/literature" / f"{result['id']}.yaml").is_file()


def test_one_bad_source_does_not_drop_later_capture(project, monkeypatch):
    from waterology.core import zotero
    from waterology.core.literature import search_literature

    settings = load_document(project / ".zotero.toml")
    settings["capture"] = "discovered"
    write_document(project / ".zotero.toml", settings)
    monkeypatch.setattr(zotero, "sync_references", lambda *a, **kw: {"status": "fixture"})
    payload = {
        "results": [
            {
                "id": "W1",
                "display_name": "Bad URL",
                "primary_location": {"landing_page_url": "https://example.org/?token=PRIVATE"},
            },
            {"id": "W2", "display_name": "Valid paper"},
        ]
    }
    result = search_literature(project, "fixture", fetcher=lambda *a, **kw: payload)
    assert len(result["capture_errors"]) == 1
    assert reference_status(project)[0]["source"]["title"] == "Valid paper"


@pytest.mark.parametrize("missing", ["pyzotero", "unrelated_dependency"])
def test_missing_sdk_reports_safe_action_and_preserves_queue(project, monkeypatch, missing):
    import builtins

    original_import = builtins.__import__

    def missing_sdk(name, *args, **kwargs):
        if name == "pyzotero":
            raise ModuleNotFoundError("SECRET provider detail", name=missing)
        return original_import(name, *args, **kwargs)

    queue_reference(
        project, {"doi": "10.1234/test", "title": "Fixture"}, reason="read", sync=False
    )
    monkeypatch.setattr(builtins, "__import__", missing_sdk)
    result = sync_references(project)
    assert result["status"] == "blocked"
    assert result["remaining"] == 1
    assert "SECRET" not in str(result)
    if missing == "pyzotero":
        assert result["missing_dependency"] == "pyzotero"
        assert "zotero" in result["hint"]
    else:
        assert "missing_dependency" not in result
    assert reference_status(project)[0]["metadata_status"] == "queued"
