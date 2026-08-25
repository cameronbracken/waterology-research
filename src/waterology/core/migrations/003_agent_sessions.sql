CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    runtime TEXT NOT NULL CHECK (runtime IN ('claude', 'codex', 'opencode')),
    role TEXT NOT NULL,
    compute_profile TEXT NOT NULL,
    worktree TEXT NOT NULL,
    task_path TEXT NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN ('created', 'running', 'waiting', 'completed', 'failed', 'cancelled', 'lost')
    ),
    native_session_id TEXT,
    supervisor_pid INTEGER,
    process_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT,
    exit_code INTEGER,
    initial_commit TEXT NOT NULL,
    resulting_commits_json TEXT NOT NULL DEFAULT '[]'
);

CREATE UNIQUE INDEX sessions_active_worktree_idx
ON sessions(worktree)
WHERE state IN ('created', 'running', 'waiting');

CREATE INDEX sessions_experiment_idx ON sessions(experiment_id, created_at);

CREATE TABLE session_attempts (
    session_id TEXT NOT NULL REFERENCES sessions(id),
    number INTEGER NOT NULL,
    state TEXT NOT NULL,
    prompt_path TEXT NOT NULL,
    events_path TEXT NOT NULL,
    stderr_path TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    supervisor_pid INTEGER,
    process_id INTEGER,
    native_session_id TEXT,
    exit_code INTEGER,
    initial_commit TEXT NOT NULL,
    resulting_commit TEXT,
    PRIMARY KEY (session_id, number)
);

CREATE TABLE session_notes (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    text TEXT NOT NULL,
    author TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX session_notes_session_idx ON session_notes(session_id, created_at);

CREATE TABLE evidence (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    claim TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT,
    run_id TEXT REFERENCES runs(id),
    session_id TEXT REFERENCES sessions(id),
    created_at TEXT NOT NULL
);

CREATE INDEX evidence_experiment_idx ON evidence(experiment_id, created_at);

CREATE TABLE artifact_references (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    path TEXT NOT NULL,
    label TEXT,
    run_id TEXT REFERENCES runs(id),
    session_id TEXT REFERENCES sessions(id),
    created_at TEXT NOT NULL
);

CREATE INDEX artifact_references_experiment_idx
ON artifact_references(experiment_id, created_at);
