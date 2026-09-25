# GitHub as Canon — SQLite の分散と再統合について

> これは `sync-canon` を設計した時の考えをまとめたエッセイである。問題、仮説、実装、残された問いの四部構成。

---

## 1. 問題：SQLite はバイナリである

SQLite は「サーバーレス」の名に反して、最も手強いファイル形式の一つだ。`.db` はバイナリ bloB である。Git で diff できない。二台のマシンで同時に書くと、後から `push` した者が勝手に `merge` を試み、冲突は解決不能になる。

私の `~/repos/` には `talk.db`、`wferr.db`、`.reposync/repos.db`、`.agents/data/triage.db` などがあり、それぞれ数百〜数千行を抱えている。家の PC でも同じ構造を使いたい。だが USB を刺したり Dropbox を頼ったりするのは、2008年の感覚だ。

**問い：SQLite を「git で diff 可能」にするにはどうすればいいか。**

---

## 2. 仮説：Canon = schema.sql + table.jsonl

答えは SQLite の内部構造そのものにあった。SQLite はテーブル定義を `sqlite_master` に格納し、実データは B-tree ページに書き込む。私たちが本当に同期したいのは「ページ」ではなく「意味」、すなわち **スキーマと行** である。

そこで次の二層構造を考案した。

```
┌─────────────────────────────────────┐
│  Layer 1: schema.sql                │
│  CREATE TABLE works (...);          │
│  CREATE INDEX ...;                  │
│  CREATE TRIGGER ...;                │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  Layer 2: works.jsonl               │
│  {"id":"wk01","title":"..."}        │
│  {"id":"wk02","title":"..."}        │
│  ...                                │
└─────────────────────────────────────┘
```

`schema.sql` は DDL のフルダンプ。`table.jsonl` は各行を JSON Lines 形式で並べたもの。両方ともプレーンテキストであり、Git の line-based diff が完全に機能する。

この二層を合わせて **canon（正典）** と呼ぶ。GitHub は canon のホスティング場であり、個々の `.db` は「canon から生成される一時キャッシュ」に過ぎない。

### 2.1 なぜ JSONL か

JSONL を選んだ理由は三つある。

1. **行独立性**：各行は独立した JSON object。ファイルの先頭にヘッダがないため、diff/patch が行単位で完結する。CSV 同様に merge-friendly だが、型安全性（null, number, boolean の区別）が高い。
2. **SQLite 親和性**：`sqlite3` CLI から `.mode json` で出力できる。逆に `jq` や Python の `json.loads` で読める。
3. **JEV / BQMLite との連続性**：talk-db のパイプラインでは既に JSONL を canonical format として採用している（`works.jsonl`, `relations.jsonl` 等）。今回の sync-canon はその思想を他の DB に拡張したに過ぎない。

---

## 3. 実装：export / import の黄金の回廊

実装は驚くほど小さく済んだ。`export.py` と `import.py`、合わせて 100行程度。

### 3.1 export：DB → canon

```python
schema = dump_sqlite_master(db)
dump_to(schema_path, schema)

for table in tables:
    rows = db.execute(f"SELECT * FROM {table}")
    write_jsonl(f"{table}.jsonl", rows)
```

FTS5 の内部テーブル（`passages_fts_data`, `passages_fts_idx` 等）は `name LIKE '%_fts%'` で除外する。FTS5 は仮想テーブルであり、データソース（`passages` テーブル）から自動生成される。canon に含める必要はない。import 後に `INSERT INTO passages_fts SELECT rowid, text FROM passages` で再構築すればよい。

### 3.2 import：canon → DB

```python
execute_script("schema.sql")

for jsonl in sorted(glob("*.jsonl")):
    table = stem(jsonl)
    rows = [json.loads(line) for line in open(jsonl)]
    db.executemany(f"INSERT INTO {table} (cols) VALUES (placeholders)", rows)
```

ラウンドトリップを諸 DB で検証した結果は次の通り。

| DB | export 行数 | import 行数 | 一致 |
|----|------------|------------|------|
| talk-db | 3,129 | 3,129 | ✅ |
| wf-errors | 5 | 5 | ✅ |
| .agents | 3,327 | 3,327 | ✅ |

**lossless** であることが確認できた。

### 3.3 設計の制約

この方法には制約がある。列の追加（ALTER TABLE ADD COLUMN）は `schema.sql` で表現できるが、**既存の table.jsonl に新列が含まれていないと import 時にエラーになる**。そのため、列追加が発生した場合は次の手順を踏む。

1. export 側で新列を含んだ JSONL を生成（自動的にその通りになる）
2. import 側は schema.sql で新列が `DEFAULT NULL` になっているため、古い JSONL でも互換性が保たれる
3. **DEFAULT 値を持たない NOT NULL 列を追加した場合のみ破綻する** → これはマイグレーションスクリプト（`scripts/migrate.py`）を別途用意することで解決する予定

---

## 4. 拓扑：三台と一雲

現時点で私は三つの計算空間を使っている。

```
         ┌─────────────────┐
         │   GitHub Cloud  │
         │  (source of     │
         │   truth for     │
         │   canon)        │
         │  bonsai/sync-   │
         │      canon      │
         └────────┬────────┘
                  │ git push / pull
      ┌───────────┼───────────┐
      │           │           │
 ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
 │  WSL    │ │ Home PC │ │  ???    │
 │ .devices│ │.devices/│ │  (未来) │
 │  /wsl/  │ │home-pc/ │ │         │
 │talk-db  │ │talk-db  │ │         │
 └─────────┘ └─────────┘ └─────────┘
```

家の PC はまだ参加していない。だが canonial repo `bonsai/sync-canon` は既に public である。家の PC で `git clone` → `export.py` → `git push` すれば、WSL 側で `git pull` → `import.py` でその DB が再現される。

**これが "GitHub as Canon" の本質だ。** GitHub は計算機ではなく、正典のホスティング場である。各デバイスは canon を読み込み、ローカル `.db` に翻訳し、書き込んだ後に改めて canon 化して戻す。

---

## 5. 競合：行の独立と vclock

同じ `talk-db` を WSL と家の PC で両方編集し、それぞれ `git push` した場合、Git は `.jsonl` の行単位で conflict を提示する。各行は独立した JSON object であるため、原則として **行の追加・削除は自動解決可能**。

問題は**同じ主キーを持つ行が両方で編集された場合**、すなわち「行の内容が異なる」場合だ。これは古典的な distributed system の problem に帰着する。

### 5.1 解決策の階層

| 戦略 | 実装 | 制約 |
|------|------|------|
| **最新勝ち（LWW）** | `modified_at` 列を比較 | 時計同期が必要 |
| **vclock（ベクトル時計）** | 各デバイスが counter を持つ | スキーマ変更が必要 |
| **手動解決** | Git の conflict marker を人が読む | 人の介在が必要 |
| **決定論的** | device_id + timestamp のハッシュで決める | データ損失の可能性 |

現時点では**手動解決**にしている。talk-db の行数（3,129）と更新頻度（日次〜週次）から、自動 conflict resolution の必要性は低い。ただし今後 `.agents/triage.db` の `issues` テーブル（1,655行、頻繁更新）が広域化する場合は、vclock または `modified_at` + device_id の付与を検討する。

---

## 6. 残された問い

### 6.1 家の PC の参加

現時点で家の PC の OS、SQLite DB の所在、`.skills/` の有無は不明である。次の手順で情報を収集する必要がある。

```bash
# 家の PC で実行（手動 or リモートデスクトップ経由）
find ~ -name "*.db" -o -name "*.sqlite3" | sort
find ~ -name ".skills" -o -name ".config/opencode"
```

あるいは Tailscale / ZeroTier で VPN を張り、`ssh` でスキャンする方法もある。

### 6.2 自動化 cron

理想としては次の workflow。

```
每小时:
  export.py → git commit --amend → git push
  （変更がない場合は no-op）

每晚 3時:
  git pull → import.py → db integrity check
```

これを GitHub Actions ではなく、各デバイスの `cron` や `systemd timer` で動かす。GH Actions は canon のホスティングには揺るぎないが、各デバイスの `.db` にはアクセスできない。

### 6.3 暗黙の合意：どの DB を同期するか

全 SQLite DB を同期すべきではない。`reposync/repos.db` は GH 上の repo リストが truth なので不要。`kankyou-dashboard/dashboard.db` は再生成可能なので `.gitignore` で十分。

**同期対象は「他のデバイスで編集したい可能性がある DB」に限定すべきである。**

| DB | 必要性 | 理由 |
|----|--------|------|
| talk-db | 高 | 家で読書中に passage 抽出したい |
| .agents/triage | 中 | エージェントタスクを家中どこからでも参照 |
| wf-errors | 低 | エラーログは一箇所集中で十分 |
| plego/rss | ? | 未調査 |

---

## 7. 結論

SQLite を Git 管理下に置くための canonical format として、`schema.sql` + `table.jsonl` の二層構造を提案・実装した。

GitHub は canon の hub である。各デバイスは export/import の黄金の回廊を廻り、`.db` を再現する。これにより「SQLite はバイナリだから git に入れられない」という通説を覆した。

残された課題は家の PC の調査、自動化 cron、競合解決戦略の選定の三つ。これらは `sync-canon` リポジトリの issue として追跡する。

> 「 canon は一つ、解釈は多様に」
