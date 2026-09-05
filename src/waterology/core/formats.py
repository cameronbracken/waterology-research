"""Human-authored NestedText, with explicit typed validation at service boundaries."""

import json
import tomllib
from pathlib import Path

import nestedtext as nt

from waterology.core.atomic import write_text


def load_document(path: Path) -> dict:
    if path.suffix == ".nt":
        try:
            value = nt.loads(path.read_text(encoding="utf-8"), top="dict")
        except nt.NestedTextError as error:
            raise ValueError(f"Invalid NestedText document: {path.name}") from error
    elif path.suffix == ".toml":
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    elif path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError("Use a .nt, .toml or legacy .json document")
    if not isinstance(value, dict):
        raise TypeError("Document must contain a mapping")
    # A schema version is typed metadata, never a domain identifier.
    if value.get("schema_version") == "1":
        value["schema_version"] = 1
    return value


def _strings(value):
    if isinstance(value, dict):
        return {str(k): _strings(v) for k, v in value.items() if v is not None}
    if isinstance(value, (tuple, list)):
        return [_strings(v) for v in value]
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def readable(value) -> str:
    """Display data without inventing implicit scalar types. Absent fields are omitted."""
    return nt.dumps(_strings(value), indent=4) + "\n"


def write_document(path: Path, value: dict) -> None:
    write_text(path, readable(value))
