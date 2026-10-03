"""Human-readable YAML and TOML, with explicit typed validation at service boundaries."""

import hashlib
import json
import tomllib
from pathlib import Path

import tomlkit
import yaml

from waterology.core.atomic import write_text

YAML_SUFFIXES = {".yaml", ".yml"}


def _legacy_nestedtext(path: Path):
    # Read-only support so existing projects can migrate. Remove with the dependency.
    import nestedtext as nt

    try:
        return nt.loads(path.read_text(encoding="utf-8"), top="dict")
    except nt.NestedTextError as error:
        raise ValueError(f"Invalid NestedText document: {path.name}") from error


def load_document(path: Path) -> dict:
    if path.suffix in YAML_SUFFIXES:
        try:
            # BaseLoader keeps every scalar a string, so identifiers such as 00123 or
            # NO are never guessed into numbers or booleans. Pydantic applies types.
            value = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        except yaml.YAMLError as error:
            raise ValueError(f"Invalid YAML document: {path.name}") from error
    elif path.suffix == ".toml":
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    elif path.suffix == ".nt":
        value = _legacy_nestedtext(path)
    elif path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError("Use a .yaml or .toml document")
    if not isinstance(value, dict):
        raise TypeError("Document must contain a mapping")
    # A schema version is typed metadata, never a domain identifier.
    if value.get("schema_version") == "1":
        value["schema_version"] = 1
    return value


def _plain(value):
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items() if v is not None}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def readable(value) -> str:
    """Display data as block YAML. Absent fields are omitted."""
    return yaml.safe_dump(
        _plain(value), sort_keys=False, allow_unicode=True, default_flow_style=False, width=100
    )


def write_document(path: Path, value: dict) -> None:
    if path.suffix == ".toml":
        write_text(path, tomlkit.dumps(value))
    elif path.suffix in YAML_SUFFIXES:
        write_text(path, readable(value))
    else:
        raise ValueError("Write a .yaml or .toml document")


def migrate_nestedtext(directory: Path) -> dict[str, str]:
    """Convert legacy .nt state records in place. Returns old to new SHA-256 by file stem."""
    hashes = {}
    for legacy in sorted(directory.glob("*.nt")):
        if legacy.is_symlink():
            raise ValueError("State record must not be a symlink")
        target = legacy.with_suffix(".yaml")
        if not target.exists():
            write_document(target, load_document(legacy))
        hashes[hashlib.sha256(legacy.read_bytes()).hexdigest()] = hashlib.sha256(
            target.read_bytes()
        ).hexdigest()
        legacy.unlink()
    return hashes
