#!/usr/bin/env python3
"""
🚫📋 ZERO-COPYING REGIME: Convention Pressure Without Any Shortcuts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The criticality finding: low copying + high convention = max computation.
Question: what happens with ZERO copying? Is there a catalytic effect of
tiny copying, or does pure convention pressure drive computation alone?

Sweep: cultural_rate ∈ {0.0, 0.005, 0.01} × convention_bonus ∈ 8 levels
1500 ticks, 50 agents, single seed (fast pass first).

Striker, April 2026
"""

import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from triple_point_v3 import run_single


def zero_copying_sweep():
    """Sweep convention pressure with zero and near-zero copying."""
    
    convention_levels = [0.0, 0.03, 0.06, 0.09, 0.12, 0.18, 0.24, 0.30]
    copying_levels = [0.0, 0.005, 0.01]
    
    ticks = 1500
    num_agents = 50
    
    results = []
    total = len(copying_levels) * len(convention_levels)
    
    print(f"🚫📋 ZERO-COPYING REGIME SWEEP")
    print(f"{'='*70}")
    print(f"  Convention: {convention_levels}")
    print(f"  Copying: {copying_levels}")
    print(f"  {ticks} ticks, {num_agents} agents, seed=42\n")
    
    for ci, cr in enumerate(copying_levels):
        print(f"\n  ── Cultural Rate = {cr:.3f} ──")
        for cj, cs in enumerate(convention_levels):
            idx = ci * len(convention_levels) + cj + 1
            t0 = time.time()
            
            result = run_single(
                ticks=ticks, num_agents=num_agents,
                cultural_rate=cr, convention_bonus=cs,
                seed=42
            )
            elapsed = time.time() - t0
            
            if "summary" in result:
                s = result["summary"]
                entry = {
                    "cultural_rate": cr,
                    "convention_bonus": cs,
                    "memory": round(s["mean_memory"], 4),
                    "transport": round(s["mean_transport"], 4),
                    "transformation": round(s["mean_transformation"], 4),
                    "triple": round(s["mean_triple"], 4),
                    "max_triple": round(s["max_triple"], 4),
                    "bottleneck": s["bottleneck"],
                }
                results.append(entry)
                
                flag = " ⭐" if entry["triple"] > 0.10 else ""
                print(f"    [{idx:2d}/{total}] cs={cs:.3f} → "
                      f"M={entry['memory']:.3f} T={entry['transport']:.3f} "
                      f"S={entry['transformation']:.3f} "
                      f"triple={entry['triple']:.4f} "
                      f"[{entry['bottleneck']}] ({elapsed:.0f}s){flag}")
            else:
                print(f"    [{idx:2d}/{total}] cs={cs:.3f} → ERROR ({elapsed:.0f}s)")
    
    # ── Analysis ──
    print(f"\n\n{'='*70}")
    print("ZERO-COPYING ANALYSIS")
    print(f"{'='*70}")
    
    for cr in copying_levels:
        cr_results = sorted([r for r in results if r["cultural_rate"] == cr],
                          key=lambda r: r["convention_bonus"])
        if not cr_results:
            continue
        peak = max(cr_results, key=lambda r: r["triple"])
        
        print(f"\n  Cultural Rate = {cr:.3f}:")
        print(f"    Conv   Triple   Memory  Transport  Synergy  Bottleneck")
        print(f"    {'─'*60}")
        
        for r in cr_results:
            marker = " ← PEAK" if r == peak else ""
            bar = "█" * int(r["triple"] * 200)
            print(f"    {r['convention_bonus']:.3f}  {r['triple']:.4f}  "
                  f"{r['memory']:.4f}   {r['transport']:.4f}    "
                  f"{r['transformation']:.4f}   {r['bottleneck']:<12s} {bar}{marker}")
        
        triples = [r["triple"] for r in cr_results]
        peak_idx = triples.index(max(triples))
        if 0 < peak_idx < len(triples) - 1:
            print(f"    ✅ NON-MONOTONIC: Peak at convention={peak['convention_bonus']:.3f}")
        elif peak_idx == len(triples) - 1:
            print(f"    📈 STILL CLIMBING at convention={peak['convention_bonus']:.3f}")
        else:
            print(f"    📉 PEAK AT ZERO convention")
    
    # Cross-copying comparison
    print(f"\n  ── COPYING CATALYSIS ──")
    for cs in [0.0, 0.06, 0.12, 0.24]:
        row = sorted([r for r in results if r["convention_bonus"] == cs],
                    key=lambda r: r["cultural_rate"])
        if row:
            parts = [f"cr={r['cultural_rate']:.3f}→{r['triple']:.4f}" for r in row]
            print(f"    Conv={cs:.2f}: {', '.join(parts)}")
    
    Path("zero_copying_results.json").write_text(json.dumps({
        "experiment": "zero-copying-regime",
        "results": results,
    }, indent=2))
    print(f"\nSaved to zero_copying_results.json")
    return results


if __name__ == "__main__":
    zero_copying_sweep()
