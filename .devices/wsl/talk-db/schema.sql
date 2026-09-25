CREATE TABLE concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT,            -- theme / keyword / entity / topic
    description TEXT
);
CREATE TABLE passage_concepts (
    passage_id TEXT NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    confidence REAL,      -- 0.0 ~ 1.0
    extractor TEXT,       -- manual / keyword / llm
    PRIMARY KEY (passage_id, concept_id)
);
CREATE TABLE passage_patterns (
    passage_id TEXT NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
    pattern_id TEXT NOT NULL REFERENCES talk_patterns(id) ON DELETE CASCADE,
    confidence REAL,
    extractor TEXT,
    PRIMARY KEY (passage_id, pattern_id)
);
CREATE TABLE passages (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    parent_id TEXT REFERENCES passages(id) ON DELETE CASCADE,
    type TEXT,            -- chapter / scene / paragraph / sentence
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    created_at TEXT
);
CREATE TABLE relations (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    subject_type TEXT,    -- entity / concept
    predicate TEXT NOT NULL,
    object TEXT,
    object_type TEXT,
    passage_id TEXT REFERENCES passages(id) ON DELETE SET NULL,
    work_id TEXT REFERENCES works(id) ON DELETE CASCADE,
    confidence REAL,
    extractor TEXT
);
CREATE TABLE talk_patterns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    pattern TEXT
);
CREATE TABLE works (
    id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    path TEXT NOT NULL,
    title TEXT,
    author TEXT,
    type TEXT CHECK(type IN ('essay','fiction','dialogue','poem','note','research','script','other')),
                          -- 作品の存在論：随筆/小説/対話/詩/メモ/研究/台本/その他
    genre TEXT,           -- JSON array ["SF", "哲学"]。ジャンルは type と分離
    language TEXT,
    summary TEXT,
    source_url TEXT,
    commit_sha TEXT,
    content_hash TEXT,    -- sha256 of raw file content
    status TEXT,          -- discovered / indexed / stale
    created_at TEXT,      -- ISO8601
    updated_at TEXT
);
