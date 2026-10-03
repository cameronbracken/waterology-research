import json
import math
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import yaml

_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
_DUMPER = getattr(yaml, "CSafeDumper", yaml.SafeDumper)


def _plain(value):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Durable records cannot contain NaN or infinite values")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported durable record value: {type(value).__name__}")


def dump_record(payload: object) -> str:
    """Typed block YAML. The dumper quotes strings that would otherwise load as other types."""
    return yaml.dump(
        _plain(payload),
        Dumper=_DUMPER,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )


def load_record(text: str | bytes) -> object:
    try:
        return yaml.load(text, Loader=_LOADER)
    except yaml.YAMLError as error:
        raise ValueError("Invalid YAML record") from error


def read_record(path: Path) -> object:
    return load_record(path.read_text(encoding="utf-8"))


def write_record(path: Path, payload: object) -> None:
    write_text(path, dump_record(payload))


def write_json(path: Path, payload: object) -> None:
    """Only for files whose format a specification or another tool fixes."""
    write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, content: str) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing to replace symlinked durable record: {path}")
    descriptor, staged_name = tempfile.mkstemp(
        prefix=f".{path.name}.waterology-stage-",
        dir=path.parent,
    )
    staged = Path(staged_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
        _sync_directory(path.parent)
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


@contextmanager
def exclusive_file_lock(path: Path) -> Iterator[None]:
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "a+b", closefd=True) as stream:
        if os.name == "nt":
            import msvcrt

            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
