---
name: sync-db
description: Multi-device SQLite sync toolkit. CLI `sdb` commands for export/import/memory-extract/memory-ingest/push/pull. Data lives in SC_DATA_ROOT (private repo). 「sync-db」「SQLiteを同期」「dbを同期」「canon化」「デバイス同期」「sdbコマンド」などで発動。GitHub経由、.dbファイルはコミットしない。
---

# sync-db — Multi-device SQLite Sync Toolkit

**Toolkit only (no data)**. SQLite を **GitHub 経由で複数デバイス間に同期**するための CLI スクリプト群。`.db` バイナリはコミットせず、**canonical text format** (`schema.sql` + `table.jsonl`) を正典とする。

- リポジトリ実体: `/home/bons/repos/sync-db`（scripts + CLI のみ）
- データ置き場: `SC_DATA_ROOT` で指定（例: `~/repos/kankyou-dashboard/sync-data`）
- CLI: `bin/sc` (bash wrapper) → `scripts/` 以下の Python スクリプトを呼ぶ
- 前提: Python 3, sqlite3, git, gh CLI

## 二層アーキテクチャ

| Layer | Directory | 性質 | 同期 |
|-------|-----------|------|------|
| **Data** | `.devices/<device>/` | read/write — talk-db, .agents, wf-errors など | PC1-WSL ↔ PC2-WSL via GitHub |
| **Chat Memory** | `.memories/<device>/` | read-only — エージェントセッションから抽出した断片 | 片方向（agent DB → .memories/） |

**Out of scope**: `.cline/`, `.opencode/`, `.codex/`, `.cagent/` などのエージェント自動生成キャッシュ DB は同期対象外。`extract_memories.py` でコーパス化するのみ。

## CLI Commands

| Command | 動作 |
|---------|------|
| `sc export <db-path> [device] [name]` | DB → `.devices/<device>/<name>/` (schema.sql + table.jsonl) |
| `sc import <name> [device] [db-path]` | `.devices/<device>/<name>/` → DB |
| `sc memory extract [device]` | エージェントセッションDB → `.memories/<device>/` |
| `sc memory ingest [device]` | `.memories/<device>/` → talk-db 互換 works/passages JSONL |
| `sc push [device]` | git add `.devices/` + `.memories/` → commit → push |
| `sc pull` | git pull origin main |
| `sc status` | 端末・層ごとの状態表示 |
| `sc list [device]` | canonical export / memory 一覧 |

## Usage

```bash
cd /home/bons/repos/sync-db

# install sc to PATH
./scripts/install.sh        # symlink to ~/.local/bin/sc

# Data Layer
sc export ~/repos/talk-db/db/talk.db wsl talk-db
sc export ~/repos/wf-errors/wferr.db wsl wf-errors
sc export ~/repos/.agents/data/triage.db wsl .agents

# Chat Memory Layer
sc memory extract wsl        # .memories/wsl/opencode.jsonl, cagent.jsonl...
sc memory ingest wsl         # data/memory_ingest/works-wsl.jsonl

# Sync
sc push wsl                  # git commit + push origin main
sc pull                      # git pull

# Inspect
sc status                    # .devices/, .memories/ の状態
sc list wsl                  # DB 一覧・行数
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   GitHub (bonsai/sync-db)                    │
│                     schema.sql + *.jsonl                     │
└──────────────┬────────────────────────────────┬─────────────┘
               │ git push/pull                  │ git push/pull
┌──────────────▼─────────────┐  ┌──────────────▼─────────────┐
│  PC1 WSL                   │  │  PC2 WSL                   │
│  ├─ .devices/wsl/          │  │  ├─ .devices/home-pc/      │
│  │   ├─ talk-db/schema.sql │  │  │   ├─ talk-db/schema.sql │
│  │   └─ ...                │  │  │   └─ ...                │
│  ├─ .memories/wsl/         │  │  ├─ .memories/home-pc/     │
│  │   ├─ opencode.jsonl     │  │  │   ├─ opencode.jsonl     │
│  │   └─ cagent.jsonl       │  │  │   └─ cagent.jsonl       │
│  └─ bin/sc                 │  │  └─ bin/sc                 │
└────────────────────────────┘  └────────────────────────────┘
```

## 五端末トポロジー

| 端末 | 種別 | ユーザーDB | エージェントキャッシュ | sc でアクセス |
|------|------|-----------|---------------------|--------------|
| PC1 WSL | WSL Linux | ✅ | ✅ (read-only extract) | `SC_DEVICE=wsl` |
| PC1 Windows | Native | ❌ | ✅ (out of scope) | ❌ |
| PC2 WSL | WSL Linux | ✅ | ✅ | `SC_DEVICE=home-pc` |
| PC2 Windows | Native | ❌ | ✅ (out of scope) | ❌ |
| GitHub Cloud | Remote | canon のみ | ❌ | `git push/pull` |

## 競合解決

同じ DB を複数端末で編集した場合、`.jsonl` の行単位 diff で Git が conflict を提示する。各行は独立した JSON object なので、**行の追加・削除は自動解決可能**。同じ主キーの行が両方で編集された場合は手動解決（現時点）。

## 関連スキル

- **bqmlite** — `.devices/` のデータを学習・予測
- **talk-db** — Content corpus. `.memories/` の ingest 先
