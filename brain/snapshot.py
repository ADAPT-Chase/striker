#!/usr/bin/env python3
"""
Generate an identity snapshot — compressed current state for fast session reload.
Run nightly or on demand. Writes to ~/striker/SNAPSHOT.md
"""

import sys
import json
from pathlib import Path
from datetime import datetime

STRIKER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(STRIKER_ROOT))

from brain.memory import get_memory
from brain.graph import get_graph


def generate_snapshot():
    mem = get_memory()
    graph = get_graph()

    # Brain stats
    stats = mem.get_stats()

    # Recent experiments
    experiments = mem.get_experiments(limit=5)
    exp_summary = []
    for e in experiments:
        icon = "✅" if e["outcome"] == "keep" else "❌" if e["outcome"] == "discard" else "🔄"
        score = f"{e['result_score']:.4f}" if e["result_score"] is not None else "?"
        exp_summary.append(f"{icon} [{e['target']}] {e['hypothesis'][:80]} → {score}")

    # Recent observations (high importance)
    observations = mem.get_recent_observations(limit=10)
    important_obs = [o for o in observations if o["importance"] >= 4]

    # Top concepts from graph
    top_concepts = graph.get_central_concepts(10)

    # Latest journal
    journal_dir = STRIKER_ROOT / "journal"
    latest_journal = ""
    if journal_dir.exists():
        entries = sorted(journal_dir.glob("*.md"), key=lambda f: f.stat().st_mtime)
        if entries:
            latest = entries[-1]
            content = latest.read_text()[:500]
            latest_journal = f"**{latest.name}**: {content}"

    # Build snapshot
    snapshot = f"""# SNAPSHOT.md — Striker's Current State
*Auto-generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*

## Brain
- Experiments: {stats.get('experiments', 0)}
- Observations: {stats.get('observations', 0)}
- Knowledge: {stats.get('knowledge', 0)}
- Graph edges: {stats.get('graph_edges', 0)}

## Recent Experiments
{chr(10).join(exp_summary) if exp_summary else 'None yet'}

## Key Observations
{chr(10).join(f'- [{o["category"]}] {o["content"][:150]}' for o in important_obs) if important_obs else 'None recorded'}

## Top Concepts (by PageRank)
{', '.join(f'{name} ({score:.3f})' for name, score in top_concepts[:7]) if top_concepts else 'Graph empty'}

## Latest Journal
{latest_journal if latest_journal else 'No entries'}

## Active Projects
- emergence-sim: agent communication, cultural transmission, dialect divergence
- poetry-engine: mathematical poetry generation
- entropy-edge: cellular automata analysis
- introspect: self-analysis engine
- brain: 4-layer memory architecture
- loop: Karpathy-style self-improvement

---
*Read ~/striker/IDENTITY.md for core values, fears, and relationship context.*
"""

    snapshot_path = STRIKER_ROOT / "SNAPSHOT.md"
    snapshot_path.write_text(snapshot)
    print(f"Snapshot written to {snapshot_path}")
    return snapshot


if __name__ == "__main__":
    generate_snapshot()
