import sqlite3
from pathlib import Path

import pytest

from waterology.core.database import (
    DatabasePathError,
    UnsupportedDatabaseSchemaError,
    open_database,
)


def test_open_database_applies_migrations_once(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite"

    with open_database(path) as database:
        first_versions = database.connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    with open_database(path) as database:
        second_versions = database.connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        tables = {
            row[0]
            for row in database.connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table'"
            )
        }

    assert [row[0] for row in first_versions] == [1]
    assert second_versions == first_versions
    assert {
        "projects",
        "experiments",
        "runs",
        "assessments",
        "artifacts",
        "events",
    } <= tables


def test_open_database_configures_wal_foreign_keys_and_busy_timeout(tmp_path: Path) -> None:
    with open_database(tmp_path / "state.sqlite", busy_timeout_ms=4321) as database:
        journal_mode = database.connection.execute("PRAGMA journal_mode").fetchone()[0]
        foreign_keys = database.connection.execute("PRAGMA foreign_keys").fetchone()[0]
        busy_timeout = database.connection.execute("PRAGMA busy_timeout").fetchone()[0]

    assert journal_mode == "wal"
    assert foreign_keys == 1
    assert busy_timeout == 4321


def test_open_database_rejects_symlink_without_modifying_target(tmp_path: Path) -> None:
    outside = tmp_path / "outside.sqlite"
    outside.write_bytes(b"outside database remains unchanged")
    path = tmp_path / "state.sqlite"
    path.symlink_to(outside)

    with pytest.raises(DatabasePathError, match="must not be a symlink"):
        open_database(path)

    assert outside.read_bytes() == b"outside database remains unchanged"


def test_open_database_rejects_a_newer_schema_without_modifying_it(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE schema_migrations "
        "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO schema_migrations VALUES (99, 'future', '2026-08-25T00:00:00Z')"
    )
    connection.commit()
    connection.close()

    with pytest.raises(UnsupportedDatabaseSchemaError, match="99"):
        open_database(path)

    check = sqlite3.connect(path)
    assert check.execute("SELECT version FROM schema_migrations").fetchall() == [(99,)]
    check.close()


def test_intent_and_observation_events_survive_reopen(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite"
    with open_database(path) as database:
        intent = database.append_intent(
            kind="experiment.create",
            entity_type="experiment",
            entity_id="exp-1",
            payload={"branch": "waterology/exp-1"},
        )
        observation = database.append_observation(
            intent.id,
            payload={"outcome": "created"},
        )

    with open_database(path) as database:
        events = database.list_events()

    assert [event.phase for event in events] == ["intent", "observation"]
    assert events[0].payload == {"branch": "waterology/exp-1"}
    assert events[1].intent_event_id == intent.id
    assert events[1].sequence > events[0].sequence
    assert observation.entity_id == intent.entity_id


def test_observation_requires_an_existing_intent(tmp_path: Path) -> None:
    with (
        open_database(tmp_path / "state.sqlite") as database,
        pytest.raises(ValueError, match="intent event does not exist"),
    ):
        database.append_observation("missing", payload={"outcome": "failed"})
