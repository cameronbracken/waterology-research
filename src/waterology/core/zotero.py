"""Durable project reference queue and bounded Zotero synchronization."""

import hashlib
import ipaddress
import os
import re
import socket
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from waterology.core.atomic import exclusive_file_lock
from waterology.core.config import _portable_project_path
from waterology.core.formats import load_document, write_document
from waterology.core.project import discover_project


class ZoteroSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    library_id: str = Field(pattern=r"^[0-9]+$")
    library_type: Literal["user", "group"] = "user"
    collection_name: str = Field(min_length=1)
    collection_key: str = Field(pattern=r"^[23456789A-NP-Z]{8}$")
    api_key_env: str = "ZOTERO_API_KEY"
    capture: Literal["selected", "discovered"] = "selected"
    download_pdfs: bool = True


def _directory(start: Path) -> Path:
    path = discover_project(start).paths.state / "references"
    if path.is_symlink():
        raise ValueError("Reference state must not be a symlink")
    path.mkdir(exist_ok=True)
    return path


def _key(seed: str) -> str:
    alphabet = "23456789ABCDEFGHIJKLMNPQRSTUVWXYZ"
    return "".join(alphabet[b % len(alphabet)] for b in hashlib.sha256(seed.encode()).digest()[:8])


def configure_zotero(start: Path, settings: dict) -> dict:
    """Save an explicitly selected library, with no credentials and no network writes."""
    settings = {**settings}
    settings.setdefault("collection_key", _key(uuid4().hex))
    config = ZoteroSettings.model_validate(settings)
    path = discover_project(start).root / "zotero.nt"
    with exclusive_file_lock(_directory(start) / "sync.lock"):
        if path.exists():
            raise ValueError("zotero.nt exists; edit it deliberately to change library settings")
        write_document(path, config.model_dump())
    return config.model_dump()


def settings_for(start: Path) -> ZoteroSettings | None:
    path = discover_project(start).root / "zotero.nt"
    if path.is_symlink():
        raise ValueError("Zotero settings must not be a symlink")
    return ZoteroSettings.model_validate(load_document(path)) if path.exists() else None


def normalize_doi(value: str | None) -> str:
    value = (value or "").strip().lower()
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.removeprefix("doi:").strip())


def _metadata_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        return ""
    if (
        parsed.username
        or parsed.password
        or any(
            re.search(
                r"token|password|secret|api.?key|credential|signature|^sig$|^key$", k, re.IGNORECASE
            )
            for k, _ in [*parse_qsl(parsed.query), *parse_qsl(parsed.fragment)]
        )
    ):
        raise ValueError("Reference URLs must not contain credentials or signed access tokens")
    if (
        parsed.hostname == "localhost"
        or "." not in parsed.hostname
        or parsed.hostname.endswith((".local", ".internal"))
    ):
        return ""
    try:
        if not ipaddress.ip_address(parsed.hostname).is_global:
            return ""
    except ValueError:
        pass
    return value


def queue_reference(start: Path, source: dict, *, reason: str, sync: bool = True) -> dict:
    source = {
        key: value
        for key, value in source.items()
        if key
        in {
            "provider",
            "id",
            "doi",
            "title",
            "item_type",
            "locator",
            "url",
            "publication_date",
            "authors",
            "venue",
            "pdf_path",
            "pdf_url",
        }
        and value is not None
    }
    for name in ("url", "pdf_url", "locator"):
        if source.get(name):
            _metadata_url(source[name])  # Reject credential-bearing URLs before persisting them.
    identity = (
        normalize_doi(source.get("doi"))
        or (source.get("locator") if source.get("provider") == "local" else None)
        or source.get("id")
        or source.get("locator")
        or source.get("url")
        or source.get("pdf_path")
    )
    if not identity or not source.get("title"):
        raise ValueError("A reference needs a title and DOI, provider ID or locator")
    identifier = hashlib.sha256(str(identity).encode()).hexdigest()[:24]
    directory = _directory(start)
    with exclusive_file_lock(directory / "sync.lock"):
        aliases = _source_aliases(source)
        matches = []
        for existing in directory.glob("ref-*.nt"):
            if existing.is_symlink():
                raise ValueError("Reference record must not be a symlink")
            previous = load_document(existing)
            if aliases & set(previous.get("aliases", _source_aliases(previous["source"]))):
                matches.append(previous)
        if len(matches) > 1:
            raise ValueError("Reference aliases identify conflicting queue entries; reconcile them")
        if matches:
            identifier = matches[0]["id"]
        path = directory / f"ref-{identifier}.nt"
        if path.is_symlink():
            raise ValueError("Reference record must not be a symlink")
        if path.exists():
            record = load_document(path)
            if (
                source.get("doi")
                and record["source"].get("doi")
                and normalize_doi(source["doi"]) != normalize_doi(record["source"]["doi"])
            ):
                raise ValueError("Reference alias has conflicting DOI assertions")
            # Enrich missing metadata, without silently replacing an existing assertion.
            for name, value in source.items():
                if value and not record["source"].get(name):
                    record["source"][name] = value
                    if name in {
                        "doi",
                        "title",
                        "authors",
                        "publication_date",
                        "venue",
                        "url",
                        "item_type",
                    }:
                        record["metadata_status"] = "pending"
                    if name in {"pdf_path", "pdf_url"} and record["pdf_status"] == "unavailable":
                        record["pdf_status"] = "not_attempted"
            record["reasons"] = list(dict.fromkeys([*record["reasons"], reason]))
        else:
            record = {
                "id": identifier,
                "source": source,
                "reasons": [reason],
                "metadata_status": "queued",
                "pdf_status": "not_attempted",
                "item_key": _key("item:" + identifier),
                "attachment_key": _key("pdf:" + identifier),
            }
        record["aliases"] = sorted(set(record.get("aliases", [])) | aliases)
        write_document(path, record)
    if sync:
        result = sync_references(start, identifiers=[identifier], limit=1)
        record = load_document(path)
        record["sync_status"] = result["status"]
        return record
    return record


def _source_aliases(source: dict) -> set[str]:
    aliases = set()
    if source.get("doi"):
        aliases.add("doi:" + normalize_doi(source["doi"]))
    if source.get("id"):
        aliases.add("id:" + source.get("provider", "") + ":" + source["id"])
    if source.get("locator"):
        aliases.add("locator:" + source["locator"])
    if source.get("url"):
        aliases.add("url:" + urlparse(source["url"])._replace(fragment="").geturl())
    if source.get("pdf_path"):
        aliases.add("pdf_path:" + source["pdf_path"])
    return aliases


def _public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("PDF downloads require a public HTTPS URL without credentials")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("PDF host must resolve to public addresses")


class _PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_pdf(url: str) -> bytes:
    _public_url(url)
    with build_opener(_PublicRedirect()).open(
        Request(url, headers={"User-Agent": "Waterology references"}), timeout=30
    ) as response:
        payload = response.read(30_000_001)
    if len(payload) > 30_000_000 or not payload.startswith(b"%PDF-"):
        raise ValueError("PDF is too large or response is not a PDF")
    return payload


class ZoteroGateway:
    def __init__(self, settings: ZoteroSettings):
        from pyzotero import zotero

        key = os.environ.get(settings.api_key_env)
        if not key:
            warnings.warn(
                f"{settings.api_key_env} is not available; Zotero references remain queued",
                RuntimeWarning,
                stacklevel=2,
            )
            raise ValueError("Zotero API credential is not configured")
        self.api = zotero.Zotero(settings.library_id, settings.library_type, key)

    def _get(self, kind: str, key: str):
        from pyzotero.zotero_errors import ResourceNotFoundError

        try:
            return getattr(self.api, kind)(key)
        except ResourceNotFoundError:
            return None

    @staticmethod
    def _created(result: dict, key: str):
        if result.get("failed") or key not in [
            *result.get("success", {}).values(),
            *result.get("unchanged", {}).values(),
        ]:
            raise ValueError("Zotero did not confirm the requested object write")

    @staticmethod
    def _doi(data: dict) -> str:
        if data.get("DOI"):
            return normalize_doi(data["DOI"])
        match = re.search(r"^DOI:[ \t]*(.+)$", data.get("extra", ""), re.MULTILINE | re.IGNORECASE)
        return normalize_doi(match[1]) if match else ""

    def collection(self, settings: ZoteroSettings):
        if self._get("collection", settings.collection_key) is None:
            self._created(
                self.api.create_collections(
                    [
                        {
                            "key": settings.collection_key,
                            "version": 0,
                            "name": settings.collection_name,
                        }
                    ]
                ),
                settings.collection_key,
            )

    def item(self, record: dict, collection: str) -> str:
        source = record["source"]
        doi = normalize_doi(source.get("doi"))
        found = self._get("item", record["item_key"])
        if found is None and doi:
            matches = [
                item
                for item in self.api.items(q=doi, qmode="everything", limit=100)
                if self._doi(item["data"]) == doi
            ]
            if len(matches) > 1:
                raise ValueError("Multiple Zotero items share this DOI; reconcile duplicates")
            found = matches[0] if matches else None
        if found:
            data = found["data"]
            owned = any(
                t.get("tag") == "waterology-ref:" + record["id"] for t in data.get("tags", [])
            )
            if doi and not self._doi(data) and owned:
                template = self.api.item_template(data["itemType"])
                if "DOI" in template:
                    data["DOI"] = doi
                else:
                    data["extra"] = (data.get("extra", "") + "\nDOI: " + doi).strip()
                if not self.api.update_item(data):
                    raise ValueError("Zotero DOI enrichment was not confirmed")
                # Reload the version before a subsequent collection-membership write.
                data = self._get("item", data["key"])["data"]
            if doi and self._doi(data) != doi:
                raise ValueError("Saved Zotero item identity changed")
            if not doi and not owned:
                raise ValueError("Saved Zotero item identity could not be verified")
            updates = {
                "title": source.get("title"),
                "date": source.get("publication_date"),
                "url": _metadata_url(source.get("url", "")),
                "publicationTitle": source.get("venue"),
                "creators": [
                    {"creatorType": "author", "name": name} for name in source.get("authors", [])
                ],
            }
            changed = False
            for field, value in updates.items():
                if field in data and not data[field] and value:
                    data[field] = value
                    changed = True
            if collection not in data.get("collections", []):
                data["collections"] = [*data.get("collections", []), collection]
                changed = True
            if changed and not self.api.update_item(data):
                raise ValueError("Zotero metadata or collection membership update failed")
            return data["key"]
        item_type = source.get("item_type") or ("journalArticle" if doi else "webpage")
        template = self.api.item_template(item_type)
        item = {
            "key": record["item_key"],
            "version": 0,
            "itemType": item_type,
            "title": source["title"],
            "date": source.get("publication_date", ""),
            "url": _metadata_url(
                source.get("url")
                or ("https://doi.org/" + doi if doi else source.get("locator", ""))
            ),
            "collections": [collection],
            "tags": [{"tag": "waterology"}, {"tag": "waterology-ref:" + record["id"]}],
            "creators": [
                {"creatorType": "author", "name": name} for name in source.get("authors", [])
            ],
        }
        if doi:
            if "DOI" in template:
                item["DOI"] = doi
            else:
                item["extra"] = "DOI: " + doi
            if "publicationTitle" in template:
                item["publicationTitle"] = source.get("venue", "")
        self._created(self.api.create_items([item]), record["item_key"])
        return record["item_key"]

    def attachment(self, record: dict, path: Path):
        key = record["attachment_key"]
        existing = self._get("item", key)
        if existing is None:
            item = {
                "key": key,
                "version": 0,
                "itemType": "attachment",
                "parentItem": record["item_key"],
                "linkMode": "imported_file",
                "title": record["source"]["title"],
                "filename": path.name,
                "contentType": "application/pdf",
            }
            self._created(self.api.create_items([item]), key)
        elif existing["data"].get("parentItem") != record["item_key"]:
            raise ValueError("Saved attachment parent changed")
        if existing and existing["data"].get("md5"):
            # Zotero's file API uses MD5 as a transport checksum, not an authenticity claim.
            digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
            if existing["data"]["md5"] == digest:
                return
            raise ValueError(
                "Existing attachment bytes differ; retained local PDF will not replace them"
            )
        result = self.api.upload_attachments(
            [{"key": key, "filename": str(path), "contentType": "application/pdf"}]
        )
        if result.get("failure") or not (result.get("success") or result.get("unchanged")):
            raise ValueError("Zotero did not confirm PDF upload")


def sync_references(
    start: Path,
    *,
    identifiers: list[str] | None = None,
    limit: int = 20,
    gateway=None,
    downloader=fetch_pdf,
) -> dict:
    if not 1 <= limit <= 100:
        raise ValueError("Sync limit must be between 1 and 100")
    settings = settings_for(start)
    if settings is None:
        if not os.environ.get("ZOTERO_API_KEY"):
            warnings.warn(
                "ZOTERO_API_KEY is not available; Zotero references remain queued",
                RuntimeWarning,
                stacklevel=2,
            )
        return {"status": "not_configured", "references": []}
    directory = _directory(start)
    results = []
    with exclusive_file_lock(directory / "sync.lock"):
        paths = sorted(directory.glob("ref-*.nt"))
        if identifiers is not None:
            paths = [p for p in paths if p.stem[4:] in identifiers]
        target = f"{settings.library_type}:{settings.library_id}:{settings.collection_key}"
        pending = []
        for path in paths:
            if path.is_symlink():
                raise ValueError("Reference record must not be a symlink")
            record = load_document(path)
            if record.get("target") not in (None, target):
                results.append(
                    {"id": record["id"], "status": "blocked", "reason": "Library target changed"}
                )
                continue
            finished = record["metadata_status"] == "synced" and (
                not settings.download_pdfs or record["pdf_status"] in {"uploaded", "unavailable"}
            )
            if not finished or record.get("target") != target:
                pending.append(path)
        pending.sort(key=lambda path: load_document(path).get("attempted_at", ""))
        remaining = len(pending) + len(results)
        paths = pending[:limit]
        if not paths:
            return {
                "status": "partial" if results else "complete",
                "remaining": remaining,
                "references": results,
            }
        # Persist the destination before even creating a collection.
        for path in paths:
            record = load_document(path)
            if "target" not in record:
                record["target"] = target
            record["attempted_at"] = datetime.now(UTC).isoformat()
            write_document(path, record)
        try:
            gateway = gateway or ZoteroGateway(settings)
            gateway.collection(settings)
        except Exception as error:  # noqa: BLE001 - optional SDK errors must be sanitized and retained
            # Provider errors may contain API keys or signed upload URLs.
            for path in paths:
                record = load_document(path)
                record["error"] = type(error).__name__
                write_document(path, record)
            return {
                "status": "blocked",
                "error": type(error).__name__,
                "remaining": remaining,
                "references": [],
            }
        for path in paths[:limit]:
            if path.is_symlink():
                raise ValueError("Reference record must not be a symlink")
            record = load_document(path)
            if record.get("target") not in (None, target):
                results.append(
                    {"id": record["id"], "status": "blocked", "reason": "Library target changed"}
                )
                continue
            record["target"] = target
            write_document(
                path, record
            )  # Save target and stable object IDs before external writes.
            try:
                record["item_key"] = gateway.item(record, settings.collection_key)
                record["metadata_status"] = "synced"
                record.pop("error", None)
                write_document(path, record)
                source = record["source"]
                if settings.download_pdfs and record["pdf_status"] != "uploaded":
                    if record.get("pdf_sha256"):
                        pinned = directory / "pdfs" / f"{record['pdf_sha256']}.pdf"
                        if pinned.is_symlink() or not pinned.resolve().is_relative_to(
                            directory.resolve()
                        ):
                            raise ValueError("Pinned PDF path is invalid")
                        payload = pinned.read_bytes()
                        if hashlib.sha256(payload).hexdigest() != record["pdf_sha256"]:
                            raise ValueError("Pinned PDF bytes changed")
                    elif source.get("pdf_path"):
                        root = discover_project(start).root
                        local = root / _portable_project_path(source["pdf_path"])
                        if local.is_symlink() or not local.resolve().is_relative_to(root):
                            raise ValueError("Local PDF must stay within the project")
                        with local.open("rb") as stream:
                            payload = stream.read(30_000_001)
                    elif source.get("pdf_url"):
                        payload = downloader(source["pdf_url"])
                    else:
                        record["pdf_status"] = "unavailable"
                        payload = None
                    if payload is not None:
                        if len(payload) > 30_000_000 or not payload.startswith(b"%PDF-"):
                            raise ValueError("Attachment is not a bounded PDF")
                        digest = hashlib.sha256(payload).hexdigest()
                        pdf_dir = directory / "pdfs"
                        if pdf_dir.is_symlink():
                            raise ValueError("PDF cache must not be a symlink")
                        pdf_dir.mkdir(exist_ok=True)
                        pdf = pdf_dir / f"{digest}.pdf"
                        if pdf.is_symlink():
                            raise ValueError("PDF must not be a symlink")
                        pdf.write_bytes(payload)
                        record["pdf_sha256"] = digest
                        record["pdf_status"] = "downloaded"
                        write_document(path, record)
                        gateway.attachment(record, pdf)
                        record["pdf_status"] = "uploaded"
            except Exception as error:  # noqa: BLE001 - retain resumable provider failures without credential-bearing messages
                record["error"] = type(error).__name__
                if record["metadata_status"] != "synced":
                    record["metadata_status"] = "pending"
                else:
                    record["pdf_status"] = "pending"
            write_document(path, record)
            results.append(record)
            if not record.get("error"):
                remaining -= 1
    return {
        "status": "complete" if remaining == 0 else "partial",
        "remaining": remaining,
        "references": results,
    }


def reference_status(start: Path) -> list[dict]:
    results = []
    for path in sorted(_directory(start).glob("ref-*.nt")):
        if path.is_symlink():
            raise ValueError("Reference record must not be a symlink")
        results.append(load_document(path))
    return results
