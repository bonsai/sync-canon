CREATE TABLE action_log (id INTEGER PRIMARY KEY, error_event_id INTEGER NOT NULL, action_type TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE error_event (id INTEGER PRIMARY KEY, repo TEXT NOT NULL, run_id INTEGER NOT NULL);
CREATE TABLE runtime_action_log (
		action_id TEXT PRIMARY KEY,
		action TEXT NOT NULL,
		repo TEXT NOT NULL,
		run_id INTEGER NOT NULL,
		status TEXT NOT NULL,
		error TEXT,
		created_at TEXT NOT NULL,
		updated_at TEXT NOT NULL
	);
