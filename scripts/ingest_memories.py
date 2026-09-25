#!/usr/bin/env python3
"""ingest_memories.py — Ingest .memories/ into talk-db compatible JSONL.

Reads .memories/<device>/*.jsonl (chat memory layer),
produces talk-db compatible works.jsonl + passages.jsonl snippets.

These can be merged into talk-db via standard pipeline:
    python scripts/ingest.py  # or manual sqlite insert
"""
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone

MEMORIES_DIR = os.path.join(os.path.dirname(__file__), "..", ".memories")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "memory_ingest")

def hash_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device", help="Device name (e.g. wsl, home-pc)")
    ap.add_argument("--memories-root", default=MEMORIES_DIR)
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()

    mem_dir = os.path.join(args.memories_root, args.device)
    if not os.path.isdir(mem_dir):
        print(f"No memories found: {mem_dir}")
        sys.exit(0)

    os.makedirs(args.out_dir, exist_ok=True)

    works = []
    passages = []
    work_ids = set()
    passage_count = 0

    for fname in sorted(f for f in os.listdir(mem_dir) if f.endswith(".jsonl")):
        src = fname[:-6]  # opencode, cagent, codex, ...
        path = os.path.join(mem_dir, fname)
        print(f"Processing {fname}...")

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                frag = json.loads(line)
                sid = frag.get("session_id", "unknown")
                title = frag.get("session_title") or f"{src}-{sid[:8]}"

                # Create work per (source, session)
                work_id = f"mem-{src}-{hash_id(sid)}"
                if work_id not in work_ids:
                    works.append({
                        "id": work_id,
                        "repo": f"sync-canon/.memories/{args.device}",
                        "path": f"{src}/{sid}.jsonl",
                        "title": title,
                        "author": src,
                        "type": "note",
                        "genre": json.dumps(["session", src]),
                        "language": "ja",
                        "summary": f"Extracted {src} session memory",
                        "source_url": None,
                        "commit_sha": None,
                        "content_hash": None,
                        "status": "indexed",
                        "created_at": frag.get("created_at", datetime.now(timezone.utc).isoformat()),
                        "updated_at": frag.get("extracted_at", datetime.now(timezone.utc).isoformat()),
                    })
                    work_ids.add(work_id)

                passage_id = f"{work_id}-p{passage_count:04d}"
                passages.append({
                    "id": passage_id,
                    "work_id": work_id,
                    "parent_id": None,
                    "type": "sentence",
                    "ordinal": passage_count,
                    "text": frag.get("content", ""),
                    "start_line": None,
                    "end_line": None,
                    "created_at": frag.get("created_at", datetime.now(timezone.utc).isoformat()),
                })
                passage_count += 1

    # Write output
    wpath = os.path.join(args.out_dir, f"works-{args.device}.jsonl")
    ppath = os.path.join(args.out_dir, f"passages-{args.device}.jsonl")

    with open(wpath, "w", encoding="utf-8") as f:
        for w in works:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")

    with open(ppath, "w", encoding="utf-8") as f:
        for p in passages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\nGenerated:")
    print(f"  works:     {len(works)}  -> {wpath}")
    print(f"  passages:  {len(passages)} -> {ppath}")
    print(f"\nNext: merge into talk-db with standard pipeline")

if __name__ == "__main__":
    main()
