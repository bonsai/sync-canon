# sync-db

**Toolkit only** — CLI scripts for multi-device SQLite sync. No data included.

Data lives in a private repo (e.g. `ds-dashboard/sync-data/`), set via `SC_DATA_ROOT`.

## Quick Start

```bash
# Install CLI
ln -s ~/repos/sync-db/bin/sc ~/.local/bin/sc

# Set data destination (private repo)
export SC_DATA_ROOT=~/repos/ds-dashboard/sync-data

# Export DBs
cd ~/repos/ds-dashboard
sc export ~/repos/talk-db/db/talk.db wsl talk-db
sc export ~/repos/.agents/data/triage.db wsl .agents
sc export ~/repos/wf-errors/wferr.db wsl wf-errors

# Extract chat memories from agent sessions
sc memory extract wsl

# Push (inside data repo)
sc push wsl
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  sync-db (public) — toolkit                             │
│  bin/sc, scripts/*.py, README, SKILL.md                 │
│  No data. .devices/ and .memories/ are .gitignored.     │
└─────────────────────────────────────────────────────────┘
                          │
                          │ SC_DATA_ROOT env var
                          ▼
┌─────────────────────────────────────────────────────────┐
│  ds-dashboard/sync-data/ (private)                      │
│  ├── .devices/wsl/        ← PC1 pushes                  │
│  ├── .devices/home-pc/    ← PC2 pushes                  │
│  ├── .memories/wsl/                                     │
│  └── data/memory_ingest/                                │
└─────────────────────────────────────────────────────────┘
```

## Two Layers

| Layer | Dir | Sync | Content |
|-------|-----|------|---------|
| **Data** | `.devices/<device>/` | PC1 ↔ PC2 | talk-db, .agents, wf-errors |
| **Chat Memory** | `.memories/<device>/` | One-way extract | Agent session fragments |

## CLI Reference

| Command | Description |
|---------|-------------|
| `sc export <db> [dev] [name]` | DB → canonical (schema.sql + table.jsonl) |
| `sc import <name> [dev] [db]` | canonical → DB |
| `sc memory extract [dev]` | Mine agent sessions → .memories/ |
| `sc memory ingest [dev]` | .memories/ → talk-db JSONL |
| `sc push [dev]` | git add data → commit → push |
| `sc pull` | git pull |
| `sc status` | Show device state |
| `sc list [dev]` | List DBs and row counts |

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `SC_DEVICE` | `wsl` | Device label for this machine |
| `SC_DATA_ROOT` | `$PWD` | Where `.devices/` and `.memories/` live |

## Five-Device Topology

| Device | Type | User DBs | Sync Role |
|--------|------|----------|-----------|
| PC1 WSL | Linux | ✅ | `SC_DEVICE=wsl` |
| PC1 Windows | Native | ❌ | Agent cache only (out of scope) |
| PC2 WSL | Linux | ✅ | `SC_DEVICE=home-pc` |
| PC2 Windows | Native | ❌ | Agent cache only (out of scope) |
| GitHub Cloud | Remote | canon | `bonsai/ds-dashboard` |

## PC1/PC2 Independent Push

Each PC exports its own data and pushes to the shared private repo:

```bash
# On PC1 (wsl)
export SC_DEVICE=wsl
sc export ~/repos/talk-db/db/talk.db
sc push wsl

# On PC2 (home-pc)
export SC_DEVICE=home-pc
sc export ~/repos/talk-db/db/talk.db
sc push home-pc
```

GitHub stores both `.devices/wsl/` and `.devices/home-pc/` without conflict.
