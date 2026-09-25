#!/usr/bin/env python3
"""extract_sessions.py — Mine agent session DBs into canonical JSONL fragments.

Targets (read-only, never synced as .db):
    ~/.opencode/logs/conversations.db   → messages.content
    ~/.cline/data/db/sessions.db        → hub_events / messages (TBD schema)
    ~/.codex/history.jsonl              → JSONL already
    ~/.cagent/session.db (Windows)      → session_items.message_json

Output: .sessions/<device>/<agent>/<session>.jsonl
Each line: {"source":"opencode","session_id":"...","role":"user","content":"...","tool_name":null,"created_at":"..."}
"""
import argparse, json, os, sqlite3, sys
from datetime import datetime, timezone

# Config: which DBs to mine on which device
SOURCES = {
    "opencode": {
        "db": "/home/bons/.opencode/logs/conversations.db",
        "type": "sqlite",
        "sql": "SELECT m.session_id, s.title, m.role, m.content, m.model, m.tool_name, m.created_at FROM messages m JOIN sessions s ON m.session_id = s.id WHERE m.role IN ('user','assistant') AND length(m.content) > 20 ORDER BY m.created_at",
        "map": lambda row: {
            "source": "opencode",
            "session_id": row[0],
            "session_title": row[1],
            "role": row[2],
            "content": row[3],
            "model": row[4],
            "tool_name": row[5],
            "created_at": row[6],
        }
    },
    "cagent": {
        "db": "/mnt/c/Users/0501JP/.cagent/session.db",
        "type": "sqlite",
        "sql": "SELECT si.session_id, s.title, si.item_type, si.agent_name, si.message_json, s.created_at FROM session_items si JOIN sessions s ON s.id=si.session_id WHERE si.item_type='message' AND si.message_json IS NOT NULL ORDER BY s.created_at, si.position",
        "map": lambda row: _parse_cagent(row)
    },
    "codex": {
        "db": "/home/bons/.codex/history.jsonl",
        "type": "jsonl",
        "map": None  # handled inline
    }
}

def _parse_cagent(row):
    try:
        msg = json.loads(row[4])
        return {
            "source": "cagent",
            "session_id": row[0],
            "session_title": row[1],
            "role": msg.get("role", "unknown"),
            "content": msg.get("content", ""),
            "model": None,
            "tool_name": msg.get("tool_name") if isinstance(msg.get("tool_name"), str) else None,
            "created_at": msg.get("created_at", row[5]),
        }
    except Exception:
        return None

def _should_include(fragment):
    """Heuristic: skip short/system/tool responses, shell transcripts, keep substantive exchanges."""
    content = fragment.get("content", "")
    if not content or len(content) < 40:
        return False
    if fragment.get("role") == "tool":
        return False
    # Skip shell transcripts (PowerShell, docker build logs, etc)
    shell_markers = ["PS C:\\", "=> [internal]", "=> exporting", "=> => ", "Error response", "failed to connect", ": no such file"]
    if any(m in content[:200] for m in shell_markers):
        return False
    # Skip common filler
    filler = ["i'll help", "i can help", "how can i help", "sure, i can", "let me know", "i'll debug", "my plan", "let me check"]
    lower = content[:80].lower()
    if any(f in lower for f in filler):
        return False
    # Cap max length (truncate in output, not skip)
    if len(content) > 4000:
        fragment["content"] = content[:4000] + "\n...[truncated]"
    return True

def mine_sqlite(name, cfg, out_dir):
    db_path = cfg["db"]
    if not os.path.exists(db_path):
        print(f"  [{name}] not found: {db_path}")
        return 0
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = con.execute(cfg["sql"])
    count = 0
    out_path = os.path.join(out_dir, f"{name}.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for row in cur.fetchall():
            frag = cfg["map"](row)
            if frag is None:
                continue
            if not _should_include(frag):
                continue
            frag["extracted_at"] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(frag, ensure_ascii=False) + "\n")
            count += 1
    con.close()
    print(f"  [{name}] => {count} fragments -> {out_path}")
    return count

def mine_jsonl(name, cfg, out_dir):
    db_path = cfg["db"]
    if not os.path.exists(db_path):
        print(f"  [{name}] not found: {db_path}")
        return 0
    count = 0
    out_path = os.path.join(out_dir, f"{name}.jsonl")
    with open(db_path, "r", encoding="utf-8") as fin, \
         open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                frag = {
                    "source": "codex",
                    "session_id": msg.get("session_id", ""),
                    "session_title": None,
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                    "model": msg.get("model"),
                    "tool_name": None,
                    "created_at": msg.get("created_at"),
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                if _should_include(frag):
                    fout.write(json.dumps(frag, ensure_ascii=False) + "\n")
                    count += 1
            except Exception:
                continue
    print(f"  [{name}] => {count} fragments -> {out_path}")
    return count

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device", help="Device name (e.g. wsl, home-pc)")
    ap.add_argument("--out-root", default=os.path.join(os.path.dirname(__file__), "..", ".memories"))
    args = ap.parse_args()

    out_dir = os.path.join(args.out_root, args.device)
    os.makedirs(out_dir, exist_ok=True)

    total = 0
    for name, cfg in SOURCES.items():
        if cfg.get("type") == "jsonl":
            total += mine_jsonl(name, cfg, out_dir)
        else:
            total += mine_sqlite(name, cfg, out_dir)

    print(f"\nTotal session fragments: {total}")

if __name__ == "__main__":
    main()
