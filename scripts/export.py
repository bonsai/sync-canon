#!/usr/bin/env python3
"""export.py — SQLite DB → schema.sql + table.jsonl for sync-canon"""
import argparse, json, os, sqlite3, sys

def schema(db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%' ORDER BY name")
    lines = []
    for row in cur.fetchall():
        if row[0]:
            lines.append(row[0] + ";\n")
    con.close()
    return "".join(lines)

def table_to_jsonl(db_path, table_name, out_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cur = con.execute(f'SELECT * FROM "{table_name}"')
        cols = [d[0] for d in cur.description]
        count = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for row in cur.fetchall():
                f.write(json.dumps(dict(zip(cols, row)), ensure_ascii=False) + "\n")
                count += 1
        return count
    finally:
        con.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db", help="Path to SQLite DB")
    ap.add_argument("device", help="Device name (e.g. wsl, home-pc)")
    ap.add_argument("project", help="Project name (e.g. talk-db, wf-errors)")
    ap.add_argument("--out-root", default=os.path.join(os.path.dirname(__file__), "..", ".devices"))
    args = ap.parse_args()

    out_dir = os.path.join(args.out_root, args.device, args.project)
    os.makedirs(out_dir, exist_ok=True)

    # 1. schema.sql
    s = schema(args.db)
    schema_path = os.path.join(out_dir, "schema.sql")
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"  schema.sql => {len(s)} chars")

    # 2. tables → jsonl
    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    con.close()

    total = 0
    for tname in tables:
        out = os.path.join(out_dir, f"{tname}.jsonl")
        n = table_to_jsonl(args.db, tname, out)
        total += n
        print(f"  {tname}.jsonl => {n} rows")

    print(f"Export done: {out_dir} ({len(tables)} tables, {total} rows)")

if __name__ == "__main__":
    main()
