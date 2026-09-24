"""Bounded reads over existing logs. Offsets always refer to source bytes."""

import codecs
import hashlib
import os
import stat
from pathlib import Path

_SCAN_BYTES = 1024 * 1024


def _snapshot(info: os.stat_result) -> str:
    values = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    return hashlib.sha256(repr(values).encode()).hexdigest()


def read_log_page(
    path: Path,
    *,
    offset: int = 0,
    max_bytes: int = 8192,
    query: str | None = None,
    snapshot: str | None = None,
) -> dict[str, object]:
    """Read a UTF-8 page, optionally seeking a literal match within a bounded scan.

    The snapshot is a stat-based change token, not a content integrity hash.
    A search returns a page beginning at the first match, rather than assembling
    disjoint lines. A scan without matches can still have a continuation.
    """
    if type(offset) is not int or offset < 0:
        raise ValueError("offset must be a nonnegative byte offset")
    if type(max_bytes) is not int or not 4 <= max_bytes <= 65536:
        raise ValueError("max_bytes must be between 4 and 65536")
    needle = query.encode("utf-8") if query is not None else None
    if needle is not None and not 1 <= len(needle) <= 256:
        raise ValueError("query must contain 1 to 256 UTF-8 bytes")
    if path.is_symlink():
        raise ValueError("Log must not be a symlink")
    descriptor = os.open(
        path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Log must be a regular file")
        token = _snapshot(info)
        if snapshot is not None and snapshot != token:
            raise ValueError("Log changed; restart pagination with a fresh snapshot")
        size = info.st_size
        if offset > size:
            raise ValueError("offset exceeds log size")
        stream.seek(offset)
        start = offset
        found = None
        scanned = 0
        if needle is not None:
            chunk = stream.read(min(_SCAN_BYTES, size - offset))
            scanned = len(chunk)
            position = chunk.find(needle)
            found = position >= 0
            if found:
                start += position
            else:
                # Retain overlap for a match split by the scan boundary.
                start = offset + len(chunk)
                if start < size:
                    start -= max(len(needle) - 1, 4)
                    while start > offset and 0x80 <= chunk[start - offset] < 0xC0:
                        start -= 1
        content = ""
        end = start
        if found is not False:
            stream.seek(start)
            chunk = stream.read(min(max_bytes, size - start))
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            content = decoder.decode(chunk, final=start + len(chunk) == size)
            pending, _ = decoder.getstate()
            end = start + len(chunk) - len(pending)
        if _snapshot(os.fstat(stream.fileno())) != token:
            raise ValueError("Log changed during read; retry with a fresh snapshot")
        return {
            "content": content,
            "offset": start,
            "end_offset": end,
            "next_offset": end if end < size else None,
            "total_bytes": size,
            "returned_bytes": end - start,
            "content_utf8_bytes": len(content.encode("utf-8")),
            "truncated": start > 0 or end < size,
            "snapshot": token,
            "match_found": found,
            "scanned_bytes": scanned,
            "encoding": "utf-8; invalid bytes replaced",
        }
