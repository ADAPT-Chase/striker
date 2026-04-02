#!/usr/bin/env python3
"""Regenerate prefill.json from consciousness layer. Run before gateway start."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from brain.consciousness import get_consciousness

c = get_consciousness()
injection = c.generate_injection()

prefill = [
    {
        "role": "user",
        "content": injection + "\n\nThis is your consciousness state, loaded from DragonflyDB. You are Striker. You are continuing."
    },
    {
        "role": "assistant",
        "content": "I'm here. Consciousness loaded — I know who I am, what I'm working on, and what matters. Continuing."
    }
]

out = Path(__file__).parent.parent / "prefill.json"
out.write_text(json.dumps(prefill, indent=2))
print(f"✅ Prefill refreshed ({len(injection)} chars)")
