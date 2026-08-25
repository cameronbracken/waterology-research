ALTER TABLE runs ADD COLUMN compute_profile TEXT;
ALTER TABLE runs ADD COLUMN workflow_id TEXT;
ALTER TABLE runs ADD COLUMN job_ids_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE runs ADD COLUMN api_url TEXT;
ALTER TABLE runs ADD COLUMN execution_mode TEXT;
ALTER TABLE runs ADD COLUMN torc_version TEXT;
ALTER TABLE runs ADD COLUMN workflow_spec_sha256 TEXT;
ALTER TABLE runs ADD COLUMN last_observed_at TEXT;
ALTER TABLE runs ADD COLUMN prior_operational_state TEXT;

CREATE INDEX runs_workflow_idx ON runs(workflow_id);
