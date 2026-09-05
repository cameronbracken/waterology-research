import pytest


def test_access_reports_missing_names_without_values(monkeypatch):
    from waterology.core.research_access import research_access

    monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    assert len(research_access()["warnings"]) == 2
    monkeypatch.setenv("ZOTERO_API_KEY", "SECRET-ZOTERO")
    monkeypatch.setenv("OPENALEX_API_KEY", "SECRET-OPENALEX")
    result = research_access()
    assert result["warnings"] == []
    assert "SECRET" not in str(result)


def test_openalex_uses_environment_key(monkeypatch):
    import json

    from waterology.core import literature

    monkeypatch.setenv("OPENALEX_API_KEY", "fixture-key")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return json.dumps({"results": []}).encode()

    requests = []
    monkeypatch.setattr(
        literature,
        "urlopen",
        lambda request, timeout: requests.append(request.full_url) or Response(),
    )
    literature.fetch_openalex("fixture", after=None, before=None, limit=1)
    assert "api_key=fixture-key" in requests[0]
    monkeypatch.delenv("OPENALEX_API_KEY")
    with pytest.warns(RuntimeWarning, match="OPENALEX_API_KEY"):
        literature.fetch_openalex("fixture", after=None, before=None, limit=1)


def test_zotero_uses_environment_key_without_exposing_it(monkeypatch):
    from pyzotero import zotero

    from waterology.core.zotero import ZoteroGateway, ZoteroSettings

    settings = ZoteroSettings(
        library_id="123", collection_name="Fixture", collection_key="ABCDEFGH"
    )
    monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
    with pytest.warns(RuntimeWarning, match="ZOTERO_API_KEY"), pytest.raises(ValueError):
        ZoteroGateway(settings)
    monkeypatch.setenv("ZOTERO_API_KEY", "fixture-key")
    calls = []
    monkeypatch.setattr(zotero, "Zotero", lambda *args: calls.append(args))
    ZoteroGateway(settings)
    assert calls == [("123", "user", "fixture-key")]
