CREATE TABLE deps (
      id TEXT NOT NULL, number INTEGER NOT NULL,
      depends_on INTEGER NOT NULL,
      PRIMARY KEY (id, depends_on)
    );
CREATE TABLE feedback (
      repo TEXT, typ TEXT, done INTEGER DEFAULT 0, open INTEGER DEFAULT 0,
      PRIMARY KEY (repo, typ)
    );
CREATE TABLE issues (
      id         TEXT PRIMARY KEY,
      repo       TEXT NOT NULL,
      number     INTEGER NOT NULL,
      state      TEXT NOT NULL,
      title      TEXT,
      url        TEXT,
      created_at TEXT,
      updated_at TEXT,
      labels     TEXT,
      author     TEXT,
      comments   INTEGER DEFAULT 0,
      body       TEXT,
      type       TEXT,
      project    TEXT,
      agent      TEXT,
      weight     REAL,
      local_path TEXT,
      priority   INTEGER DEFAULT 2,
      note       TEXT,
      fetched_at TEXT DEFAULT (datetime('now'))
    );
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE repos (
      repo TEXT PRIMARY KEY, pushed_at TEXT, private INTEGER DEFAULT 0
    );
