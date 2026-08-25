import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from types import TracebackType
from typing import Self
from uuid import uuid4

from waterology.core.errors import WaterologyError

_MIGRATION_NAME = re.compile(r"^(?P<version>[0-9]{3})_(?P<name>[a-z0-9_]+)\.sql$")


class UnsupportedDatabaseSchemaError(WaterologyError):
    code = "unsupported_database_schema"


class DatabasePathError(WaterologyError):
    code = "database_path_invalid"


@dataclass(frozen=True)
class EventRecord:
    sequence: int
    id: str
    kind: str
    entity_type: str
    entity_id: str
    phase: str
    payload: dict[str, object]
    created_at: str
    intent_event_id: str | None


class Database:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def append_intent(
        self,
        *,
        kind: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, object],
    ) -> EventRecord:
        event_id = str(uuid4())
        created_at = _utc_now()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO events (
                    id, kind, entity_type, entity_id, phase, payload_json, created_at
                ) VALUES (?, ?, ?, ?, 'intent', ?, ?)
                """,
                (
                    event_id,
                    kind,
                    entity_type,
                    entity_id,
                    _json_payload(payload),
                    created_at,
                ),
            )
        return EventRecord(
            sequence=cursor.lastrowid,
            id=event_id,
            kind=kind,
            entity_type=entity_type,
            entity_id=entity_id,
            phase="intent",
            payload=payload,
            created_at=created_at,
            intent_event_id=None,
        )

    def append_observation(
        self,
        intent_event_id: str,
        *,
        payload: dict[str, object],
    ) -> EventRecord:
        intent = self.connection.execute(
            """
            SELECT kind, entity_type, entity_id
            FROM events
            WHERE id = ? AND phase = 'intent'
            """,
            (intent_event_id,),
        ).fetchone()
        if intent is None:
            raise ValueError(f"intent event does not exist: {intent_event_id}")

        event_id = str(uuid4())
        created_at = _utc_now()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO events (
                    id, kind, entity_type, entity_id, phase, payload_json,
                    created_at, intent_event_id
                ) VALUES (?, ?, ?, ?, 'observation', ?, ?, ?)
                """,
                (
                    event_id,
                    intent["kind"],
                    intent["entity_type"],
                    intent["entity_id"],
                    _json_payload(payload),
                    created_at,
                    intent_event_id,
                ),
            )
        return EventRecord(
            sequence=cursor.lastrowid,
            id=event_id,
            kind=intent["kind"],
            entity_type=intent["entity_type"],
            entity_id=intent["entity_id"],
            phase="observation",
            payload=payload,
            created_at=created_at,
            intent_event_id=intent_event_id,
        )

    def list_events(self) -> tuple[EventRecord, ...]:
        rows = self.connection.execute(
            """
            SELECT sequence, id, kind, entity_type, entity_id, phase,
                   payload_json, created_at, intent_event_id
            FROM events
            ORDER BY sequence
            """
        ).fetchall()
        return tuple(
            EventRecord(
                sequence=row["sequence"],
                id=row["id"],
                kind=row["kind"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                phase=row["phase"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
                intent_event_id=row["intent_event_id"],
            )
            for row in rows
        )


def open_database(path: Path, busy_timeout_ms: int = 5000) -> Database:
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_database_path(path)
    connection = sqlite3.connect(path, timeout=busy_timeout_ms / 1000)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
        connection.execute("PRAGMA journal_mode = WAL")
        _apply_migrations(connection)
    except BaseException:
        connection.close()
        raise
    return Database(connection)


def validate_database_path(path: Path) -> None:
    for candidate in (
        path,
        path.with_name(path.name + "-wal"),
        path.with_name(path.name + "-shm"),
    ):
        if candidate.is_symlink():
            raise DatabasePathError(f"Database path must not be a symlink: {candidate}")


def _apply_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {
        row[0] for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
    }
    migrations = _migration_files()
    latest = migrations[-1][0] if migrations else 0
    newer = sorted(version for version in applied if version > latest)
    if newer:
        raise UnsupportedDatabaseSchemaError(
            f"Database schema version {newer[-1]} is newer than supported version {latest}"
        )

    for version, name, sql in migrations:
        if version in applied:
            continue
        try:
            connection.executescript("BEGIN IMMEDIATE;\n" + sql)
            connection.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (version, name, _utc_now()),
            )
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


def _migration_files() -> tuple[tuple[int, str, str], ...]:
    migrations = []
    for resource in files("waterology.core.migrations").iterdir():
        match = _MIGRATION_NAME.match(resource.name)
        if match is None:
            continue
        migrations.append(
            (
                int(match.group("version")),
                match.group("name"),
                resource.read_text(encoding="utf-8"),
            )
        )
    return tuple(sorted(migrations, key=lambda item: item[0]))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
