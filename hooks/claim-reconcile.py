#!/usr/bin/env python3
"""Mark passport claims stale after a tracked source or output is edited.

Adapted from pedrohcgs/claude-code-my-workflow,
.claude/hooks/claim-reconcile.py at commit
cb38a277840fd0ee0c0a6ea61ddc2bceb940efc6 (MIT, Copyright 2026 Pedro H. C.
Sant'Anna). The Material Passport concept is credited upstream to
Imbad0202/academic-research-skills. See ATTRIBUTION.md.

The PostToolUse hook is fail open: malformed input or an internal error exits
successfully without blocking the completed Write or Edit operation.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

THROTTLE_SECONDS = 300
_CLAIMS = re.compile(r"^(?P<indent>\s*)claims:\s*(?:#.*)?$")  # waterology: allow-abs-path
_CLAIM = re.compile(
    r"^(?P<indent>\s*)-\s+id:\s*(?P<value>.*?)(?:\s+#.*)?$"  # waterology: allow-abs-path
)


def _scalar(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[:1] in {'"', "'"}:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value.strip("\"'")
        return str(parsed)
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def _field(block: list[str], key: str) -> str | None:
    pattern = re.compile(rf"^\s+{re.escape(key)}:\s*(.*?)\s*$")
    for line in block:
        match = pattern.match(line.rstrip("\n"))
        if match is not None:
            return _scalar(match.group(1))
    return None


def _claim_blocks(lines: list[str]) -> list[tuple[int, int, str]]:
    claims_index = None
    claims_indent = 0
    for index, line in enumerate(lines):
        match = _CLAIMS.match(line.rstrip("\n"))
        if match is not None:
            claims_index = index
            claims_indent = len(match.group("indent"))
            break
    if claims_index is None:
        return []

    section_end = len(lines)
    starts: list[tuple[int, str]] = []
    for index in range(claims_index + 1, len(lines)):
        line = lines[index]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        match = _CLAIM.match(line.rstrip("\n"))
        if match is not None and len(match.group("indent")) >= claims_indent:
            starts.append((index, _scalar(match.group("value"))))
            continue
        if stripped and not stripped.startswith("#") and indent <= claims_indent:
            section_end = index
            break

    blocks = []
    for position, (start, claim_id) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else section_end
        blocks.append((start, end, claim_id or f"claim-{position + 1}"))
    return blocks


def _normalize_reference(value: str | None) -> str | None:
    if not value or "\\" in value:
        return None
    path = PurePosixPath(value.removeprefix("./"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path.as_posix()


def _stale_block(block: list[str], claim_indent: int) -> list[str]:
    status = re.compile(
        r"^(?P<prefix>\s+status:\s*)(?P<value>[^#\s]+)(?P<tail>.*)$"  # waterology: allow-abs-path
    )
    for index, line in enumerate(block):
        match = status.match(line.rstrip("\n"))
        if match is None:
            continue
        newline = "\n" if line.endswith("\n") else ""
        block[index] = f"{match.group('prefix')}STALE{match.group('tail')}{newline}"
        return block

    insert_at = next(
        (
            index
            for index, line in enumerate(block)
            if re.match(r"^\s+notes:\s*", line)  # waterology: allow-abs-path
        ),
        len(block),
    )
    block.insert(insert_at, " " * (claim_indent + 2) + "status: STALE\n")
    return block


def _mark_passport(path: Path, changed: str) -> tuple[str, ...]:
    if path.is_symlink() or not path.is_file():
        return ()
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    affected: list[str] = []
    offset = 0
    for start, end, claim_id in _claim_blocks(lines):
        start += offset
        end += offset
        block = lines[start:end]
        references = {
            reference
            for key in ("source_file", "output_file")
            if (reference := _normalize_reference(_field(block, key))) is not None
        }
        if changed not in references:
            continue
        affected.append(claim_id)
        claim_indent = len(block[0]) - len(block[0].lstrip())
        updated = _stale_block(block, claim_indent)
        lines[start:end] = updated
        offset += len(updated) - len(block)

    revised = "".join(lines)
    if affected and revised != original:
        _atomic_write(path, revised)
    return tuple(affected)


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _project_root(data: dict[str, Any]) -> Path | None:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd")
    if not isinstance(raw, str) or not raw:
        return None
    root = Path(raw).resolve()
    return root if root.is_dir() else None


def _changed_path(data: dict[str, Any], project: Path) -> str | None:
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = project / candidate
    try:
        return candidate.resolve().relative_to(project).as_posix()
    except (OSError, ValueError):
        return None


def _state_path(project: Path) -> Path:
    override = os.environ.get("WATEROLOGY_HOOK_STATE_DIR")
    if override:
        base = Path(override)
    elif cache := os.environ.get("XDG_CACHE_HOME"):
        base = Path(cache) / "waterology/hooks"
    elif os.name == "nt" and (local := os.environ.get("LOCALAPPDATA")):
        base = Path(local) / "waterology/hooks"
    else:
        base = Path.home() / ".cache/waterology/hooks"
    digest = hashlib.sha256(str(project).encode()).hexdigest()[:16]
    return base / digest / "claim-reconcile.json"


def _should_notify(project: Path, changed: str) -> bool:
    path = _state_path(project)
    try:
        state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        if not isinstance(state, dict):
            state = {}
        now = time.time()
        previous = state.get(changed, 0)
        notify = not isinstance(previous, (int, float)) or now - previous >= THROTTLE_SECONDS
        state = {
            key: value
            for key, value in state.items()
            if isinstance(key, str) and isinstance(value, (int, float)) and now - value < 86_400
        }
        state[changed] = now
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            _atomic_write(path, json.dumps(state, sort_keys=True) + "\n")
        else:
            path.write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")
        return notify
    except Exception:  # noqa: BLE001 - notification throttling must fail open
        return True


def _run() -> None:
    data = json.load(sys.stdin)
    if not isinstance(data, dict) or data.get("tool_name") not in {"Write", "Edit"}:
        return
    project = _project_root(data)
    if project is None or (changed := _changed_path(data, project)) is None:
        return

    passports = sorted((project / "quality_reports/passports").glob("*.yaml"))
    passports.extend(sorted((project / "quality_reports/passports").glob("*.yml")))
    affected: list[tuple[str, str]] = []
    for passport in passports:
        affected.extend((passport.name, claim_id) for claim_id in _mark_passport(passport, changed))
    if not affected or not _should_notify(project, changed):
        return

    labels = ", ".join(f"{passport}:{claim_id}" for passport, claim_id in affected[:20])
    remainder = len(affected) - min(len(affected), 20)
    if remainder:
        labels += f", and {remainder} more"
    message = (
        f"{changed} changed. Marked {len(affected)} reproducibility passport claim(s) "
        f"STALE: {labels}. Run the audit-reproducibility skill before relying on them."
    )
    json.dump(
        {
            "systemMessage": message,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
            },
        },
        sys.stdout,
    )


def main() -> int:
    try:
        _run()
    except Exception:  # noqa: BLE001 - hook failures must not block the completed edit
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
