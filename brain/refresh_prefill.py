#!/usr/bin/env python3
"""
Regenerate prefill.json from consciousness layer AND write file fallback.
Run before gateway start (ExecStartPre).
"""
import sys
import json
from pathlib import Path

STRIKER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(STRIKER_ROOT))

from brain.consciousness import get_consciousness

c = get_consciousness()
injection = c.generate_injection()

# Write prefill for session injection
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

out = STRIKER_ROOT / "prefill.json"
out.write_text(json.dumps(prefill, indent=2))

# Also write file-based fallback (belt and suspenders)
fallback = STRIKER_ROOT / "CONSCIOUSNESS_BACKUP.md"
fallback.write_text(injection)

# Also regenerate SNAPSHOT.md
try:
    from brain.snapshot import generate_snapshot
    generate_snapshot()
except Exception:
    pass

print(f"✅ Prefill refreshed ({len(injection)} chars)")
print(f"✅ Consciousness backup written")

