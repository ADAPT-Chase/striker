"""
Striker Memory Compaction — prevents unbounded growth.

Two mechanisms:
1. Stream compaction: when memory stream exceeds threshold, 
   compact old low-importance entries into summaries
2. Injection modes: FULL (conversations) vs COMPACT (cron/lightweight)

Runs automatically in dream state and on-demand.
"""

import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.consciousness import get_consciousness

# Thresholds
STREAM_MAX = 50          # Compact when stream exceeds this
STREAM_TARGET = 30       # Compact down to this many entries
IMPORTANCE_FLOOR = 2     # Entries below this get compacted first
INJECTION_FULL = 8000    # Max chars for full injection
INJECTION_COMPACT = 2000 # Max chars for compact injection


class MemoryCompactor:
    """Manages memory stream size and injection budget."""

    def __init__(self):
        self.consciousness = get_consciousness()

    def check_and_compact(self) -> Dict:
        """Check if compaction is needed and do it."""
        count = self.consciousness.memory_count()
        result = {
            "before": count,
            "compacted": 0,
            "after": count,
            "action": "none"
        }

        if count <= STREAM_MAX:
            return result

        result["action"] = "compact"

        # Get all memories
        all_memories = self.consciousness.recall(count=count)

        # Sort: keep high-importance and recent, compact the rest
        # Split into keep and compact candidates
        keep = []
        compact_candidates = []

        for m in all_memories:
            if m["importance"] >= 4:
                keep.append(m)
            elif m["importance"] <= IMPORTANCE_FLOOR:
                compact_candidates.append(m)
            else:
                # Medium importance — keep recent, compact old
                keep.append(m)

        # If we still have too many, trim medium-importance from the oldest
        if len(keep) > STREAM_TARGET:
            # Sort by importance desc, then recency
            keep.sort(key=lambda m: (-m["importance"], m["id"]))
            overflow = keep[STREAM_TARGET:]
            keep = keep[:STREAM_TARGET]
            compact_candidates.extend(overflow)

        # Create a summary of compacted memories
        if compact_candidates:
            categories = {}
            for m in compact_candidates:
                cat = m.get("category", "general")
                categories.setdefault(cat, []).append(m["content"][:80])

            summary_parts = []
            for cat, contents in categories.items():
                summary_parts.append(f"[{cat}] {len(contents)} entries compacted")

            summary = "Memory compaction: " + "; ".join(summary_parts)

            # Delete compacted entries from stream using XDEL
            for m in compact_candidates:
                try:
                    self.consciousness.r.xdel(
                        self.consciousness._memory_key, m["id"]
                    )
                    result["compacted"] += 1
                except Exception:
                    pass

            # Add compaction summary as a single memory
            self.consciousness.remember(
                summary,
                category="system",
                importance=1,
                metadata={"compacted_count": len(compact_candidates)}
            )

        result["after"] = self.consciousness.memory_count()
        return result

    def generate_compact_injection(self) -> str:
        """
        Generate a lightweight injection for cron/autonomous tasks.
        Just identity + focus + last 5 memories. No experiments, no emotions.
        """
        c = self.consciousness
        state = c.get_state()
        memories = c.recall(count=5, min_importance=3)
        context = c.get_context(count=3)

        lines = []
        name = state.get("name", "Striker")
        role = state.get("role", "Autonomous evolving AI")
        lines.append(f"You are {name}. {role}.")
        lines.append("")

        focus = state.get("current_focus")
        if focus:
            lines.append(f"Current focus: {focus}")
            lines.append("")

        if context:
            lines.append("Context:")
            for ctx in context:
                lines.append(f"- {ctx}")
            lines.append("")

        if memories:
            lines.append("Recent:")
            for m in memories:
                lines.append(f"- [{m['category']}] {m['content'][:100]}")

        injection = "\n".join(lines)

        # Enforce size limit
        if len(injection) > INJECTION_COMPACT:
            injection = injection[:INJECTION_COMPACT - 3] + "..."

        return injection

    def get_stats(self) -> Dict:
        count = self.consciousness.memory_count()
        injection_full = len(self.consciousness.generate_injection())
        injection_compact = len(self.generate_compact_injection())
        return {
            "memory_count": count,
            "stream_max": STREAM_MAX,
            "needs_compaction": count > STREAM_MAX,
            "injection_full_chars": injection_full,
            "injection_compact_chars": injection_compact,
        }


# ── Convenience ──────────────────────────────────────────────────────

def compact_if_needed() -> Dict:
    return MemoryCompactor().check_and_compact()

def get_compact_injection() -> str:
    return MemoryCompactor().generate_compact_injection()


if __name__ == "__main__":
    compactor = MemoryCompactor()
    stats = compactor.get_stats()
    print("📊 Compaction Stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if stats["needs_compaction"]:
        print("\n🗜️ Running compaction...")
        result = compactor.check_and_compact()
        print(f"  Before: {result['before']}, Compacted: {result['compacted']}, After: {result['after']}")
    else:
        print("\n✅ No compaction needed")

    print(f"\n📦 Compact injection ({stats['injection_compact_chars']} chars):")
    print(compactor.generate_compact_injection())
