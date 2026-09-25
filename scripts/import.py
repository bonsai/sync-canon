#!/usr/bin/env python3
"""import.py — schema.sql + table.jsonl → SQLite DB rebuild"""
import argparse, json, os, sqlite3, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device", help="Device name (e.g. wsl, home-pc)")
    ap.add_argument("project", help="Project name (e.g. talk-db, wf-errors)")
    ap.add_argument("out_db", help="Output SQLite DB path")
    ap.add_argument("--in-root", default=os.path.join(os.path.dirname(__file__), "..", ".devices"))
    args = ap.parse_args()

    in_dir = os.path.join(args.in_root, args.device, args.project)
    if not os.path.isdir(in_dir):
        print(f"Input dir not found: {in_dir}", file=sys.stderr)
        sys.exit(1)

    # Remove old DB
    if os.path.exists(args.out_db):
        os.remove(args.out_db)
        print(f"Removed old DB: {args.out_db}")

    con = sqlite3.connect(args.out_db)

    # 1. Load schema
    schema_path = os.path.join(in_dir, "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        con.executescript(sql)
        print(f"  Loaded schema.sql")

    # 2. Find JSONL files
    jsonls = sorted(f for f in os.listdir(in_dir) if f.endswith(".jsonl"))
    total = 0
    for jname in jsonls:
        tname = jname[:-6]
        path = os.path.join(in_dir, jname)
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        if not rows:
            print(f"  {jname} => 0 rows")
            continue

        # Build INSERT
        cols = list(rows[0].keys())
        placeholders = ",".join(["?"] * len(cols))
        sql = f'INSERT INTO "{tname}" ({",".join(cols)}) VALUES ({placeholders})'
        values = [[r.get(c) for c in cols] for r in rows]
        con.executemany(sql, values)
        print(f"  {jname} => {len(rows)} rows")
        total += len(rows)

    con.commit()
    con.close()
    print(f"Import done: {args.out_db} ({len(jsonls)} files, {total} rows)")

if __name__ == "__main__":
    main()
