# sync-canon

Multi-device SQLite synchronization via GitHub.

## Principle

- **GitHub is the sync hub** (not the DB source of truth)
- **SQLite `.db` files are never committed** (binary, unmergeable)
- **Canonical = `schema.sql` + `table.jsonl`** (text, line-diffable, git-friendly)
- Each device exports its local DB to `.devices/<device>/`, pushes, and other devices pull + import

## Directory Structure

```
sync-canon/
├── .gitignore              # ignores *.db, *.sqlite3
├── README.md
├── .devices/
│   ├── wsl/
│   │   ├── talk-db/
│   │   │   ├── schema.sql
│   │   │   ├── works.jsonl
│   │   │   ├── passages.jsonl
│   │   │   └── ...
│   │   ├── wf-errors/
│   │   │   ├── schema.sql
│   │   │   └── ...
│   │   └── .agents/
│   │       ├── schema.sql
│   │       └── ...
│   └── home-pc/            # created from home PC
│       └── ...
└── scripts/
    ├── export.py           # DB → schema.sql + table.jsonl
    └── import.py           # schema.sql + table.jsonl → DB
```

## Workflow

### Export (local → canonical)

```bash
cd sync-canon

# talk-db
python scripts/export.py ~/repos/talk-db/db/talk.db wsl talk-db

# wf-errors
python scripts/export.py ~/repos/wf-errors/wferr.db wsl wf-errors

# .agents
python scripts/export.py ~/.agents/data/triage.db wsl .agents

git add .devices/wsl/
git commit -m "sync(wsl): export talk-db + wf-errors + .agents"
git push origin main
```

### Import (canonical → local)

```bash
cd sync-canon
git pull origin main

# talk-db
python scripts/import.py wsl talk-db ~/repos/talk-db/db/talk.db

# wf-errors
python scripts/import.py wsl wf-errors ~/repos/wf-errors/wferr.db

# .agents
python scripts/import.py wsl .agents ~/.agents/data/triage.db
```

## Merging Conflicts

When two devices edit the same DB:

1. Both export + push → GitHub
2. Pull → conflict in `.jsonl` files
3. Resolve line-by-line conflicts (each line is independent row)
4. Re-import on both devices

If schema changed on one device:
1. The other device's `.jsonl` may have missing columns
2. Apply schema migration script before import
3. Or drop + recreate DB with new schema

## Devices

| Device | Status | Last Sync |
|--------|--------|-----------|
| WSL (this PC) | ✅ | now |
| Home PC | ⏳ | pending |

## Supported DBs

| DB | Path (this PC) | Device | Rows (approx) |
|----|---------------|--------|---------------|
| talk-db | `~/repos/talk-db/db/talk.db` | wsl | 3,129 |
| wf-errors | `~/repos/wf-errors/wferr.db` | wsl | 5 |
| .agents | `~/.agents/data/triage.db` | wsl | 3,327 |
