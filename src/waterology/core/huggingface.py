"""Bounded Hugging Face Hub metadata, file tree, and small text inspection."""

import os
import re
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request

from waterology.core.errors import WaterologyError
from waterology.core.literature_providers import (
    USER_AGENT,
    read_json_without_redirects,
    read_prefix_without_redirects,
)

REPO_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)?$")
REVISION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
REPO_TYPES = ("dataset", "model", "space")
MAX_TEXT_READ_BYTES = 262_144


class HuggingFaceAccessError(WaterologyError):
    """Raised when a Hugging Face Hub request fails without exposing credentials."""

    code = "huggingface_error"


def _validate_repo(repo_id: str, repo_type: str, revision: str) -> tuple[str, str, str]:
    cleaned_id = repo_id.strip()
    if not REPO_ID.fullmatch(cleaned_id) or ".." in cleaned_id:
        raise ValueError("Invalid repository identifier")
    if repo_type not in REPO_TYPES:
        raise ValueError("repo_type must be one of " + ", ".join(REPO_TYPES))
    cleaned_rev = revision.strip()
    if (
        not REVISION.fullmatch(cleaned_rev)
        or any(part in {"", ".", ".."} for part in cleaned_rev.split("/"))
    ):
        raise ValueError("Invalid revision")
    return cleaned_id, repo_type, cleaned_rev


def _validate_subpath(subpath: str, *, allow_empty: bool) -> str:
    cleaned = subpath.strip().strip("/")
    if not cleaned:
        if allow_empty:
            return ""
        raise ValueError("Invalid file path")
    parts = cleaned.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Invalid file path")
    return "/".join(parts)


def _request(url: str) -> Request:
    headers = {"User-Agent": USER_AGENT}
    token = os.environ.get("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return Request(url, headers=headers)


def _call(reader, url: str, bound: int):
    try:
        return reader(_request(url), bound)
    except HTTPError as error:
        raise HuggingFaceAccessError(f"Hugging Face Hub returned HTTP {error.code}") from None
    except (URLError, HTTPException, OSError) as error:
        raise HuggingFaceAccessError(
            f"Hugging Face Hub request failed ({type(error).__name__})"
        ) from None


def hf_dataset_info(repo_id: str, revision: str = "main") -> dict:
    """Inspect bounded Hugging Face dataset card, config, split, and feature metadata."""
    cleaned_id, _, cleaned_rev = _validate_repo(repo_id, "dataset", revision)
    encoded_id = quote(cleaned_id, safe="/")
    suffix = "" if cleaned_rev == "main" else f"/revision/{quote(cleaned_rev, safe='')}"
    payload = _call(
        read_json_without_redirects,
        f"https://huggingface.co/api/datasets/{encoded_id}{suffix}",
        4_000_000,
    )
    if not isinstance(payload, dict):
        raise TypeError("Unexpected Hugging Face dataset metadata payload")
    card = payload.get("cardData") if isinstance(payload.get("cardData"), dict) else {}
    tags = [t for t in (payload.get("tags") or []) if isinstance(t, str)]
    tag_license = next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), None)
    siblings = payload.get("siblings") if isinstance(payload.get("siblings"), list) else []
    return {
        "id": payload.get("id") or cleaned_id,
        "revision": cleaned_rev,
        "sha": payload.get("sha"),
        "url": f"https://huggingface.co/datasets/{cleaned_id}",
        "private": bool(payload.get("private")),
        "gated": payload.get("gated", False),
        "disabled": bool(payload.get("disabled")),
        "license": card.get("license") or tag_license,
        "downloads": payload.get("downloads"),
        "likes": payload.get("likes"),
        "used_storage": payload.get("usedStorage"),
        "last_modified": payload.get("lastModified"),
        "tags": tags[:50],
        "configs": card.get("configs"),
        "dataset_info": card.get("dataset_info"),
        "sibling_count": len(siblings),
    }


def hf_repo_files(
    repo_id: str,
    repo_type: str = "dataset",
    revision: str = "main",
    path: str = "",
    limit: int = 200,
) -> dict:
    """List files and directories at one path inside a Hugging Face Hub repository."""
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    cleaned_id, cleaned_type, cleaned_rev = _validate_repo(repo_id, repo_type, revision)
    cleaned_path = _validate_subpath(path, allow_empty=True)
    path_suffix = f"/{quote(cleaned_path, safe='/')}" if cleaned_path else ""
    url = (
        f"https://huggingface.co/api/{cleaned_type}s/"
        f"{quote(cleaned_id, safe='/')}/tree/{quote(cleaned_rev, safe='')}{path_suffix}"
    )
    payload = _call(read_json_without_redirects, url, 4_000_000)
    if not isinstance(payload, list):
        raise TypeError("Unexpected Hugging Face tree payload")
    files = []
    for entry in payload[:limit]:
        if not isinstance(entry, dict):
            continue
        files.append(
            {
                "path": entry.get("path"),
                "type": entry.get("type"),
                "size": entry.get("size"),
                "lfs": bool(entry.get("lfs")),
            }
        )
    return {
        "repo_id": cleaned_id,
        "repo_type": cleaned_type,
        "revision": cleaned_rev,
        "path": cleaned_path,
        "files": files,
        "truncated": len(payload) > limit,
    }


def hf_repo_read_file(
    repo_id: str,
    file_path: str,
    repo_type: str = "dataset",
    revision: str = "main",
    max_bytes: int = 65_536,
) -> dict:
    """Read a bounded UTF-8 text file directly from a Hugging Face Hub repository."""
    if not 1 <= max_bytes <= MAX_TEXT_READ_BYTES:
        raise ValueError(f"max_bytes must be between 1 and {MAX_TEXT_READ_BYTES}")
    cleaned_id, cleaned_type, cleaned_rev = _validate_repo(repo_id, repo_type, revision)
    cleaned_file = _validate_subpath(file_path, allow_empty=False)
    prefix = "" if cleaned_type == "model" else f"{cleaned_type}s/"
    url = (
        f"https://huggingface.co/{prefix}{quote(cleaned_id, safe='/')}/raw/"
        f"{quote(cleaned_rev, safe='')}/{quote(cleaned_file, safe='/')}"
    )
    sample, truncated = _call(read_prefix_without_redirects, url, max_bytes)
    if b"\x00" in sample:
        raise ValueError("Refusing to read binary file; inspect small text files only")
    try:
        content = sample.decode("utf-8")
    except UnicodeDecodeError as error:
        if truncated and error.start >= len(sample) - 3:
            content = sample[: error.start].decode("utf-8")
        else:
            raise ValueError(
                "Refusing to read binary or non-UTF-8 file; inspect small text files only"
            ) from error
    return {
        "repo_id": cleaned_id,
        "repo_type": cleaned_type,
        "revision": cleaned_rev,
        "path": cleaned_file,
        "content": content,
        "returned_bytes": len(content.encode("utf-8")),
        "truncated": truncated,
    }
