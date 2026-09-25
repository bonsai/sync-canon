# sync-db

**Toolkit only** — CLI scripts for multi-device SQLite sync. No data included.

Data lives in a private repo (e.g. `kankyou-dashboard/sync-data/`), set via `SC_DATA_ROOT`.

## Quick Start

```bash
# Install CLI
ln -s ~/repos/sync-db/bin/sc ~/.local/bin/sc

# Set environment identity
export SC_DEVICE=wsl           # device label (wsl, win, docker, cloud...)
export SC_ENV_ID=pc1-wsl       # environment ID (pc1-wsl, pc2-wsl, pc1-win, etc)
export SC_DATA_ROOT=~/repos/kankyou-dashboard/sync-data

# Export DBs
cd ~/repos/kankyou-dashboard
sc export ~/repos/talk-db/db/talk.db $SC_ENV_ID talk-db
sc export ~/repos/.agents/data/triage.db $SC_ENV_ID .agents

# Extract chat memories
sc memory extract $SC_ENV_ID

# Capture environment diff
sc env capture $SC_ENV_ID

# Push all data (device + memory + env)
sc push $SC_ENV_ID
```

## Multi-Environment Scale

| Env ID | OS | Type | Example Use |
|--------|-----|------|-------------|
| `pc1-wsl` | Linux/WSL | Dev | Main development PC |
| `pc1-win` | Windows | Native | Windows-side tools |
| `pc2-wsl` | Linux/WSL | Home | Home PC |
| `pc2-win` | Windows | Native | Home Windows |
| `docker` | Linux | Container | CI/test environment |
| `cloud` | Linux | VM | Cloud instance |

### Directory Layout (in SC_DATA_ROOT)

```
sync-data/
├── .devices/
│   ├── pc1-wsl/
│   │   ├── talk-db/
│   │   ├── .agents/
│   │   └── wf-errors/
│   ├── pc2-wsl/
│   └── docker/
├── .memories/
│   ├── pc1-wsl/
│   └── pc2-wsl/
└── .env/                 ← NEW: diff-env layer
    ├── pc1-wsl/
    │   ├── hostname
    │   ├── os-release
    │   ├── paths.txt
    │   ├── env.json      # $PATH, $HOME, etc
    │   └── packages.json # pip, npm, apt lists
    ├── pc2-wsl/
    └── docker/
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  sync-db (public) — toolkit                             │
│  bin/sc, scripts/*.py, README, SKILL.md                 │
│  No data. .devices/ .memories/ .env/ are .gitignored.   │
└─────────────────────────────────────────────────────────┘
                          │
                          │ SC_DATA_ROOT env var
                          ▼
┌─────────────────────────────────────────────────────────┐
│  kankyou-dashboard/sync-data/ (private)                      │
│  ├── .devices/<env>/       ← DB exports                 │
│  ├── .memories/<env>/      ← Chat memories              │
│  └── .env/<env>/           ← Environment diffs          │
└─────────────────────────────────────────────────────────┘
                          │
                          │ ds ingest
                          ▼
┌─────────────────────────────────────────────────────────┐
│  kankyou-dashboard engine                                    │
│  Receives → Analyzes → Discovers → Renders              │
│  dashboard.db + dashboard.html + insights.md            │
└─────────────────────────────────────────────────────────┘
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `sc export <db> [env] [name]` | DB → canonical |
| `sc import <name> [env] [db]` | canonical → DB |
| `sc memory extract [env]` | Mine agent sessions |
| `sc memory ingest [env]` | → talk-db JSONL |
| `sc env capture [env]` | **NEW**: snapshot env diff |
| `sc env diff <env1> <env2>` | **NEW**: compare environments |
| `sc push [env]` | git commit + push |
| `sc pull` | git pull |
| `sc status` | Show state |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SC_DEVICE` | `wsl` | Legacy device label |
| `SC_ENV_ID` | `$SC_DEVICE` | Environment identifier |
| `SC_DATA_ROOT` | `$PWD` | Data repository root |
| `SC_DIFFENV` | `1` | Enable env capture |
