#!/usr/bin/env python3
"""sage_speak.py — Deterministic sage archetype speaker.

Reads ds-insighter insights + metrics, speaks via instance voice template.

Usage:
  sage_speak.py --instance hiroyuki --input ../ds-insighter/output
  sage_speak.py --instance socrates --mode dialogue
"""
import argparse, json, os, random
from datetime import datetime, timezone
from pathlib import Path

random.seed(42)  # deterministic

def load_instance(instance_id):
    path = Path(__file__).parent.parent / "archetypes" / "sage" / "instances" / f"{instance_id}.json"
    return json.loads(path.read_text())

def load_insights(input_dir):
    insights = []
    fpath = Path(input_dir) / "insights.jsonl"
    if fpath.exists():
        with open(fpath) as f:
            for line in f:
                if line.strip():
                    insights.append(json.loads(line))
    return insights

def load_metrics(input_dir):
    metrics = []
    fpath = Path(input_dir) / "metrics.jsonl"
    if fpath.exists():
        with open(fpath) as f:
            for line in f:
                if line.strip():
                    metrics.append(json.loads(line))
    return metrics

def score_insight(ins):
    """Rank insight by speak-worthiness."""
    severity_score = {"error": 3, "warning": 2, "info": 1}
    base = severity_score.get(ins.get("severity"), 1)
    # Prefer insights with actionable data
    if ins.get("data"):
        base += 1
    # Prefer multi-device / cross-cutting
    if "multi" in ins.get("category", "") or "gap" in ins.get("category", ""):
        base += 1
    return base

def pick_template(instance, context):
    """Select voice pattern based on context."""
    patterns = instance["patterns"]
    if context == "open":
        return random.choice(patterns["open"])
    elif context == "contradiction":
        return random.choice(patterns["dismiss"] + patterns["probe"])
    elif context == "probe":
        return random.choice(patterns["probe"])
    elif context == "close":
        return random.choice(patterns["close"])
    return random.choice(patterns["connect"])

def speak_hiroyuki(insights, metrics):
    """Rapid-fire provocative monologue."""
    lines = []
    # Sort by importance
    ranked = sorted(insights, key=score_insight, reverse=True)[:5]
    
    if not ranked:
        lines.append("データがねえじゃん。何も言えないよ。")
        return "\n\n".join(lines)
    
    # Opening
    top = ranked[0]
    lines.append(f"おい、{top['category']}だけどさ。")
    lines.append(f"{top['message']}")
    lines.append("ってことは、結局何が問題なわけ？")
    
    # Middle: connect each insight
    for ins in ranked[1:]:
        connector = random.choice(["それより", "あと", "それから"])
        lines.append(f"{connector}、{ins['category']}もあるでしょ。")
        lines.append(f"{ins['message']}")
        
        # If data available, drill
        data = ins.get("data", {})
        if "missing" in data:
            lines.append(f"{data['missing']}がないって話じゃん。")
        if "devices" in data and len(data["devices"]) > 1:
            lines.append(f"{len(data['devices'])}台もあるのに同期してないの？")
    
    # Closing
    lines.append("")
    lines.append("要するに、整理しろってことよ。")
    lines.append("何が言いたいかって言うと、")
    lines.append("データ狂ってるから直せ、で終わり。")
    
    return "\n".join(lines)

def speak_socrates(insights, metrics):
    """Dialectic questioning monologue."""
    lines = []
    ranked = sorted(insights, key=score_insight, reverse=True)[:5]
    
    if not ranked:
        lines.append("友よ、私にはまだ洞察が見えない。")
        lines.append("まずデータを手に入れなければならない。")
        return "\n\n".join(lines)
    
    # Opening question
    top = ranked[0]
    lines.append(f"友よ、{top['category']}について考えてみよう。")
    lines.append(f"私たちは『{top['message']}』と述べている。")
    lines.append("しかし、これは本当に正しいのか？")
    
    # Dialectic
    for ins in ranked[1:]:
        lines.append("")
        lines.append(f"さらに、{ins['category']}についてはどうだろう？")
        lines.append(f"『{ins['message']}』——")
        
        data = ins.get("data", {})
        if "devices" in data:
            lines.append(f"{len(data['devices'])}の存在があるという。")
            lines.append("では、各々の定義は何か？")
        if "missing_dbs" in data:
            lines.append(f"{', '.join(data['missing_dbs'])}が欠けているというが、")
            lines.append("これは欠如と言えるのか、それとも不要と言えるのか？")
    
    # Closing
    lines.append("")
    lines.append("結論を急ぐべきではない。")
    lines.append("問いは残された。再考しよう。")
    
    return "\n".join(lines)

def speak(instance_id, insights, metrics):
    if instance_id == "hiroyuki":
        return speak_hiroyuki(insights, metrics)
    elif instance_id == "socrates":
        return speak_socrates(insights, metrics)
    else:
        # Generic logical sage
        lines = [f"[{instance_id}] Insights generated at {datetime.now(timezone.utc).isoformat()}", ""]
        for ins in insights[:5]:
            lines.append(f"[{ins['severity'].upper()}] {ins['category']}: {ins['message']}")
        return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="hiroyuki", help="Instance ID (hiroyuki, socrates, ...)")
    ap.add_argument("--input", default="../ds-insighter/output", help="ds-insighter output directory")
    ap.add_argument("--mode", default="monologue", choices=["monologue", "dialogue", "critique"])
    args = ap.parse_args()
    
    instance = load_instance(args.instance)
    insights = load_insights(args.input)
    metrics = load_metrics(args.input)
    
    print(f"=== sage speak: {instance['name']} ({args.mode}) ===")
    print(f"Insights: {len(insights)} | Metrics: {len(metrics)}")
    print("")
    
    utterance = speak(args.instance, insights, metrics)
    print(utterance)
    
    # Write to sync-data/.insights/ for persistence
    out_dir = Path(os.environ.get("SC_DATA_ROOT", ".")) / ".insights"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{args.instance}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    out_file.write_text(utterance, encoding="utf-8")
    print(f"\n[Saved] {out_file}")

if __name__ == "__main__":
    main()
