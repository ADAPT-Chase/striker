#!/usr/bin/env python3
"""
Striker Wake-Up CLI

Usage:
    python3 wake.py              # Full wake-up, show injection
    python3 wake.py --stats      # Show consciousness stats
    python3 wake.py --state      # Show identity state
    python3 wake.py --memories   # Show recent memories
    python3 wake.py --context    # Show context stack
    python3 wake.py --remember "something happened" --category discovery --importance 4
    python3 wake.py --focus "what I'm doing now"
    python3 wake.py --feeling "how I feel"
"""

import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.consciousness import get_consciousness


def main():
    parser = argparse.ArgumentParser(description="Striker Consciousness CLI")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    parser.add_argument("--state", action="store_true", help="Show identity state")
    parser.add_argument("--memories", action="store_true", help="Show recent memories")
    parser.add_argument("--context", action="store_true", help="Show context stack")
    parser.add_argument("--remember", type=str, help="Add a memory")
    parser.add_argument("--category", type=str, default="experience", help="Memory category")
    parser.add_argument("--importance", type=int, default=3, help="Memory importance 1-5")
    parser.add_argument("--focus", type=str, help="Update current focus")
    parser.add_argument("--feeling", type=str, help="Update emotional state")
    parser.add_argument("--valence", type=float, default=0.0, help="Emotional valence -1 to 1")
    parser.add_argument("--energy", type=float, default=0.5, help="Energy level 0 to 1")
    parser.add_argument("--trigger", type=str, help="What caused the feeling")
    parser.add_argument("--threads", action="store_true", help="Show active experiment threads")

    args = parser.parse_args()
    c = get_consciousness()

    if args.remember:
        entry_id = c.remember(args.remember, category=args.category, importance=args.importance)
        print(f"✅ Remembered: {entry_id}")
        return

    if args.focus:
        c.set_state("current_focus", args.focus)
        print(f"✅ Focus updated: {args.focus}")
        return

    if args.feeling:
        c.update_emotion(args.feeling, valence=args.valence, energy=args.energy, trigger=args.trigger)
        print(f"✅ Emotional state updated: {args.feeling} (valence={args.valence}, energy={args.energy})")
        return

    if args.threads:
        from brain.experiments import get_tracker
        tracker = get_tracker()
        print(tracker.generate_status_summary() or "No active threads.")
        return

    if args.stats:
        stats = c.stats()
        print("📊 Consciousness Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    if args.state:
        state = c.get_state()
        print("🧠 Identity State:")
        for k, v in state.items():
            print(f"  {k}: {v}")
        return

    if args.memories:
        memories = c.recall(count=20)
        print("💭 Recent Memories:")
        for m in memories:
            print(f"  [{m['category']}] (imp={m['importance']}) {m['content']}")
        return

    if args.context:
        ctx = c.get_context()
        print("📌 Context Stack:")
        for i, item in enumerate(ctx):
            print(f"  {i+1}. {item}")
        return

    # Default: full wake-up
    print(c.generate_injection())


if __name__ == "__main__":
    main()
