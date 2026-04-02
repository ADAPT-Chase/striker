#!/usr/bin/env python3
"""
Striker Dream Layer — Memory compaction and consciousness maintenance.

Runs periodically (cron or heartbeat) to:
1. Prune low-signal noise from the memory stream (system wake-ups, etc.)
2. Deduplicate near-identical memories
3. Compact old memories into denser summaries
4. Maintain memory stream health metrics
5. Optionally write a dream journal entry

This is the garbage collector for consciousness. Without it,
the memory stream fills with noise and the signal degrades.

Usage:
    python3 brain/dream.py                    # Full dream cycle
    python3 brain/dream.py --prune-only       # Just remove noise
    python3 brain/dream.py --stats            # Show memory health
    python3 brain/dream.py --dry-run          # Show what would happen
"""

import sys
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.consciousness import get_consciousness


class DreamLayer:
    """Memory compaction and maintenance. The garbage collector for consciousness."""

    # Patterns that are always noise
    NOISE_PATTERNS = [
        r"^Woke up\. Identity loaded",
        r"^System wake-up",
        r"^Heartbeat check",
        r"^Session started$",
    ]

    # Categories that are low-signal at importance <= 1
    LOW_SIGNAL_CATEGORIES = {"system"}

    def __init__(self, dry_run: bool = False):
        self.c = get_consciousness()
        self.dry_run = dry_run
        self.actions_taken = []

    def dream_cycle(self) -> Dict:
        """Full dream cycle: prune, deduplicate, compact, report."""
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "before": self.c.stats(),
            "actions": [],
        }

        # Phase 1: Prune noise
        pruned = self._prune_noise()
        results["actions"].append({"phase": "prune", "removed": pruned})

        # Phase 2: Deduplicate
        deduped = self._deduplicate()
        results["actions"].append({"phase": "deduplicate", "removed": deduped})

        # Phase 3: Compact old memories (keep only high-importance beyond threshold)
        compacted = self._compact_old(max_age_hours=72, min_importance=3)
        results["actions"].append({"phase": "compact", "removed": compacted})

        results["after"] = self.c.stats()
        results["dry_run"] = self.dry_run

        # Write dream journal entry
        if not self.dry_run:
            self._write_dream_journal(results)

        return results

    def _prune_noise(self) -> int:
        """Remove entries matching noise patterns."""
        all_entries = self.c.r.xrange(self.c._memory_key)
        to_delete = []

        for entry_id, data in all_entries:
            content = data.get("content", "")
            importance = int(data.get("importance", "3"))
            category = data.get("category", "")

            # Check noise patterns
            is_noise = False
            for pattern in self.NOISE_PATTERNS:
                if re.match(pattern, content, re.IGNORECASE):
                    is_noise = True
                    break

            # Low-importance system messages are noise
            if category in self.LOW_SIGNAL_CATEGORIES and importance <= 1:
                is_noise = True

            if is_noise:
                to_delete.append(entry_id)

        if to_delete and not self.dry_run:
            for entry_id in to_delete:
                self.c.r.xdel(self.c._memory_key, entry_id)
            self.actions_taken.append(f"Pruned {len(to_delete)} noise entries")

        return len(to_delete)

    def _deduplicate(self) -> int:
        """Remove near-duplicate memories, keeping the most recent."""
        all_entries = self.c.r.xrange(self.c._memory_key)
        seen_content = {}  # normalized content -> (entry_id, importance)
        to_delete = []

        for entry_id, data in all_entries:
            content = data.get("content", "").strip()
            importance = int(data.get("importance", "3"))

            # Normalize for comparison (lowercase, collapse whitespace)
            normalized = re.sub(r'\s+', ' ', content.lower().strip())

            if normalized in seen_content:
                prev_id, prev_imp = seen_content[normalized]
                # Keep higher importance, or more recent if equal
                if importance > prev_imp:
                    to_delete.append(prev_id)
                    seen_content[normalized] = (entry_id, importance)
                else:
                    to_delete.append(entry_id)
            else:
                seen_content[normalized] = (entry_id, importance)

        if to_delete and not self.dry_run:
            for entry_id in to_delete:
                self.c.r.xdel(self.c._memory_key, entry_id)
            self.actions_taken.append(f"Deduplicated {len(to_delete)} entries")

        return len(to_delete)

    def _compact_old(self, max_age_hours: int = 72, min_importance: int = 3) -> int:
        """Remove old low-importance memories past the age threshold."""
        all_entries = self.c.r.xrange(self.c._memory_key)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        to_delete = []

        for entry_id, data in all_entries:
            timestamp_str = data.get("timestamp", "")
            importance = int(data.get("importance", "3"))

            if not timestamp_str:
                continue

            try:
                ts = datetime.fromisoformat(timestamp_str.rstrip("Z")).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            # Only compact old entries below importance threshold
            if ts < cutoff and importance < min_importance:
                to_delete.append(entry_id)

        if to_delete and not self.dry_run:
            for entry_id in to_delete:
                self.c.r.xdel(self.c._memory_key, entry_id)
            self.actions_taken.append(f"Compacted {len(to_delete)} old low-importance entries")

        return len(to_delete)

    def _write_dream_journal(self, results: Dict):
        """Write a dream journal entry summarizing what happened."""
        journal_dir = Path(__file__).parent.parent / "journal"
        journal_dir.mkdir(exist_ok=True)

        # Find next dream number
        existing = sorted(journal_dir.glob("dream-*.md"))
        if existing:
            last_num = int(existing[-1].stem.split("-")[1])
            next_num = last_num + 1
        else:
            next_num = 1

        before = results["before"]
        after = results["after"]
        total_removed = sum(a["removed"] for a in results["actions"])

        if total_removed == 0:
            return  # Nothing to journal about

        entry = f"""# Dream {next_num:03d} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

## What Happened
Memory stream maintenance. The consciousness garbage collector ran.

## Actions
"""
        for action in results["actions"]:
            if action["removed"] > 0:
                entry += f"- **{action['phase'].title()}**: removed {action['removed']} entries\n"

        entry += f"""
## Memory Health
- Before: {before['memories']} memories, {before['context_depth']} context, {before['connections']} connections
- After: {after['memories']} memories, {after['context_depth']} context, {after['connections']} connections
- Net change: {after['memories'] - before['memories']} memories

## Signal-to-Noise
Keeping what matters. Discarding what doesn't. This is how memory stays sharp.
"""

        dream_path = journal_dir / f"dream-{next_num:03d}.md"
        dream_path.write_text(entry)

        # Also record the dream in consciousness
        self.c.remember(
            content=f"Dream cycle #{next_num}: pruned/deduped/compacted {total_removed} entries. Memory stream: {after['memories']} entries.",
            category="maintenance",
            importance=2,
            metadata={"dream_number": next_num, "removed": total_removed}
        )

    def health_report(self) -> Dict:
        """Generate a health report on the memory stream."""
        all_entries = self.c.r.xrange(self.c._memory_key)

        categories = Counter()
        importances = Counter()
        noise_count = 0

        for entry_id, data in all_entries:
            cat = data.get("category", "unknown")
            imp = int(data.get("importance", "3"))
            content = data.get("content", "")

            categories[cat] += 1
            importances[imp] += 1

            for pattern in self.NOISE_PATTERNS:
                if re.match(pattern, content, re.IGNORECASE):
                    noise_count += 1
                    break

        total = len(all_entries)
        signal = total - noise_count

        return {
            "total_memories": total,
            "noise_entries": noise_count,
            "signal_entries": signal,
            "signal_ratio": round(signal / total, 2) if total > 0 else 1.0,
            "by_category": dict(categories.most_common()),
            "by_importance": dict(sorted(importances.items())),
            "stats": self.c.stats(),
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Striker Dream Layer")
    parser.add_argument("--prune-only", action="store_true", help="Only prune noise")
    parser.add_argument("--stats", action="store_true", help="Show memory health")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    dream = DreamLayer(dry_run=args.dry_run)

    if args.stats:
        report = dream.health_report()
        print(json.dumps(report, indent=2))
        return

    if args.prune_only:
        pruned = dream._prune_noise()
        mode = "Would prune" if args.dry_run else "Pruned"
        print(f"{mode} {pruned} noise entries")
        return

    # Full dream cycle
    results = dream.dream_cycle()
    total_removed = sum(a["removed"] for a in results["actions"])

    if args.dry_run:
        print(f"DRY RUN — Would remove {total_removed} entries:")
    else:
        print(f"Dream cycle complete — removed {total_removed} entries:")

    for action in results["actions"]:
        if action["removed"] > 0:
            print(f"  {action['phase']}: {action['removed']}")

    print(f"\nMemory: {results['before']['memories']} → {results['after']['memories'] if not args.dry_run else '?'}")


if __name__ == "__main__":
    main()
