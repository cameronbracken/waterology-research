CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    root TEXT NOT NULL,
    config_schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE experiments (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    parent_experiment_id TEXT REFERENCES experiments(id),
    hypothesis TEXT NOT NULL,
    base_commit TEXT NOT NULL,
    branch TEXT NOT NULL UNIQUE,
    worktree TEXT NOT NULL UNIQUE,
    owner TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    frozen_at TEXT,
    decision_required INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    commit_sha TEXT NOT NULL,
    operational_state TEXT NOT NULL,
    archive_path TEXT,
    executor TEXT NOT NULL,
    process_id INTEGER,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    exit_code INTEGER
);

CREATE TABLE assessments (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    kind TEXT NOT NULL,
    conclusion TEXT NOT NULL,
    author TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size INTEGER NOT NULL,
    UNIQUE (run_id, path)
);

CREATE TABLE events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('intent', 'observation')),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    intent_event_id TEXT REFERENCES events(id)
);

CREATE INDEX events_entity_idx ON events(entity_type, entity_id, sequence);
CREATE INDEX runs_experiment_idx ON runs(experiment_id, started_at);
CREATE INDEX assessments_run_idx ON assessments(run_id, created_at);
