#!/usr/bin/env python3
"""
The Triple Point V2 — With Invariant Memory

Day 013 fix: Replace the old temporal MI memory axis with the 
translation-invariant memory metric that has a periodicity penalty.
The old metric gave R62 (periodic) a perfect score. The new one
correctly penalizes tape loops.

Also: investigate R75/R89 — the mysterious top-ranking rules.

This is the updated 3D map:
  X: Invariant Memory (TI-MI × periodicity correction)
  Y: Spatial Transport (directional MI + perturbation coherence)
  Z: Transformation (transfer entropy + processing ratio)
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_data():
    """Load all three axis datasets."""
    base = os.path.dirname(os.path.abspath(__file__))
    
    # New invariant memory (replaces old temporal MI)
    with open(os.path.join(base, 'memory_invariant_results.json')) as f:
        memory_data = json.load(f)
    
    # Spatial transport (unchanged)
    with open(os.path.join(base, 'spatial_transport_results.json')) as f:
        transport_data = json.load(f)
    
    # Transformation (unchanged)
    with open(os.path.join(base, 'transformation_results.json')) as f:
        transform_data = json.load(f)
    
    return memory_data, transport_data, transform_data


def normalize(values):
    """Min-max normalize to [0, 1]."""
    mn, mx = min(values), max(values)
    rng = mx - mn
    if rng < 1e-10:
        return [0.5] * len(values)
    return [(v - mn) / rng for v in values]


def geometric_mean_3(a, b, c, eps=0.01):
    """Geometric mean of three values. Zero if any axis is zero."""
    return (max(a, eps) * max(b, eps) * max(c, eps)) ** (1/3)


def balance(a, b, c):
    """How balanced are the three axes? 1 = perfectly balanced."""
    mean = (a + b + c) / 3
    if mean < 0.01:
        return 0.0
    var = ((a - mean)**2 + (b - mean)**2 + (c - mean)**2) / 3
    cv = math.sqrt(var) / mean
    return max(0.0, 1.0 - cv)


def investigate_rule(rule_num, memory_entry, transport_entry, transform_entry, coords):
    """Deep profile of a single rule."""
    c = coords
    print(f"\n  ═══ RULE {rule_num} — Deep Profile ═══")
    print(f"  Memory (invariant):   {c['memory_norm']:.3f}  (raw: {c['memory_raw']:.4f})")
    print(f"  Transport:            {c['transport_norm']:.3f}  (raw: {c['transport_raw']:.4f})")
    print(f"  Transformation:       {c['transform_norm']:.3f}  (raw: {c['transform_raw']:.4f})")
    print(f"  Triple score:         {c['triple']:.4f}")
    print(f"  Balance:              {c['balance']:.4f}")
    print(f"  Combined:             {c['combined']:.4f}")
    
    # Memory details
    print(f"\n  Memory breakdown:")
    print(f"    TI-MI (raw):        {memory_entry.get('ti_memory_raw', 'N/A')}")
    print(f"    Periodicity penalty: {memory_entry.get('periodicity_penalty', 'N/A')}")
    print(f"    Novelty factor:     {memory_entry.get('novelty_factor', 'N/A')}")
    print(f"    Period:             {memory_entry.get('period', 'N/A')} (conf: {memory_entry.get('period_confidence', 'N/A')})")
    print(f"    Spatial entropy:    {memory_entry.get('spatial_entropy', 'N/A')}")
    
    # Transport details
    print(f"\n  Transport breakdown:")
    print(f"    Combined score:     {transport_entry.get('combined_score', 'N/A')}")
    
    # Transformation details
    print(f"\n  Transformation breakdown:")
    print(f"    Transform score:    {transform_entry.get('transformation_score', 'N/A')}")


def main():
    print("=" * 78)
    print("  THE TRIPLE POINT V2 — With Invariant Memory")
    print("  'Now the metric can tell a tape loop from a computer'")
    print("=" * 78)
    
    memory_data, transport_data, transform_data = load_data()
    
    # Index all data by rule number
    mem_by_rule = {e['rule']: e for e in memory_data['all_256']}
    
    # Transport: check structure
    transport_list = transport_data.get('all_256', transport_data if isinstance(transport_data, list) else [])
    trans_by_rule = {e['rule']: e for e in transport_list}
    
    # Transform: check structure
    transform_list = transform_data.get('all_256', transform_data if isinstance(transform_data, list) else [])
    xform_by_rule = {e['rule']: e for e in transform_list}
    
    # Build unified coordinates for all rules that have all 3 axes
    complete_rules = []
    raw_mem, raw_trans, raw_xform = [], [], []
    
    for r in range(256):
        if r in mem_by_rule and r in trans_by_rule and r in xform_by_rule:
            complete_rules.append(r)
            raw_mem.append(mem_by_rule[r]['invariant_memory_score'])
            raw_trans.append(trans_by_rule[r].get('combined_score', 0))
            raw_xform.append(xform_by_rule[r].get('transformation_score', 0))
    
    print(f"\n  Rules with all 3 axes: {len(complete_rules)}/256")
    
    # Normalize
    norm_mem = normalize(raw_mem)
    norm_trans = normalize(raw_trans)
    norm_xform = normalize(raw_xform)
    
    # Build coordinate map
    coords = {}
    for i, r in enumerate(complete_rules):
        m, t, x = norm_mem[i], norm_trans[i], norm_xform[i]
        triple = geometric_mean_3(m, t, x)
        bal = balance(m, t, x)
        combined = triple * (0.7 + 0.3 * bal)
        
        coords[r] = {
            'memory_norm': m, 'transport_norm': t, 'transform_norm': x,
            'memory_raw': raw_mem[i], 'transport_raw': raw_trans[i], 'transform_raw': raw_xform[i],
            'triple': triple, 'balance': bal, 'combined': combined,
        }
    
    # Rank by combined score
    ranked = sorted(coords.items(), key=lambda x: -x[1]['combined'])
    
    # ─── Famous rules ───
    famous = {
        0: "Dead", 30: "Chaos", 54: "Complex", 62: "Periodic", 
        67: "Conveyor", 75: "Mystery #1", 89: "Mystery #2",
        90: "XOR fractal", 110: "Turing-complete", 184: "Traffic"
    }
    
    print(f"\n{'='*78}")
    print(f"  FAMOUS RULES — 3D Coordinates (V2)")
    print(f"{'='*78}\n")
    print(f"  {'Rule':>6s}  {'Name':>16s}  {'Memory':>7s}  {'Transport':>10s}  {'Transform':>10s}  {'Triple':>7s}  {'Combined':>9s}")
    print(f"  {'─'*6}  {'─'*16}  {'─'*7}  {'─'*10}  {'─'*10}  {'─'*7}  {'─'*9}")
    
    for rn in sorted(famous.keys()):
        if rn in coords:
            c = coords[rn]
            print(f"  R{rn:>4d}  {famous[rn]:>16s}  {c['memory_norm']:>7.3f}  {c['transport_norm']:>10.3f}  "
                  f"{c['transform_norm']:>10.3f}  {c['triple']:>7.3f}  {c['combined']:>9.4f}")
    
    # ─── Top 25 by combined score ───
    print(f"\n{'='*78}")
    print(f"  TOP 25 — TRIPLE POINT RANKING (V2)")
    print(f"{'='*78}\n")
    print(f"  {'Rank':>4s}  {'Rule':>4s}  {'Combined':>9s}  {'Triple':>7s}  {'Bal':>5s}  {'M':>5s}  {'T':>5s}  {'X':>5s}")
    print(f"  {'─'*4}  {'─'*4}  {'─'*9}  {'─'*7}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*5}")
    
    for rank, (rn, c) in enumerate(ranked[:25], 1):
        marker = f" ◄ {famous[rn]}" if rn in famous else ""
        print(f"  {rank:>4d}  R{rn:>3d}  {c['combined']:>9.4f}  {c['triple']:>7.4f}  "
              f"{c['balance']:>.3f}  {c['memory_norm']:>.3f}  {c['transport_norm']:>.3f}  "
              f"{c['transform_norm']:>.3f}{marker}")
    
    # ─── Where do famous rules rank? ───
    print(f"\n── FAMOUS RULE RANKINGS ──\n")
    for rn in sorted(famous.keys()):
        if rn in coords:
            rank = next(i+1 for i, (r, _) in enumerate(ranked) if r == rn)
            c = coords[rn]
            print(f"  R{rn:>3d} ({famous[rn]:>16s}): rank {rank:>3d}/{len(ranked)}, combined={c['combined']:.4f}")
    
    # ─── V1 vs V2 comparison ───
    print(f"\n{'='*78}")
    print(f"  V1 → V2 CHANGES (Effect of Invariant Memory)")
    print(f"{'='*78}\n")
    
    old_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'triple_point_results.json')
    if os.path.exists(old_path):
        with open(old_path) as f:
            old_data = json.load(f)
        old_rankings = old_data.get('rankings', [])
        old_rank_map = {r: i+1 for i, (r, _) in enumerate(old_rankings)}
        
        print(f"  {'Rule':>6s}  {'Name':>16s}  {'V1 Rank':>8s}  {'V2 Rank':>8s}  {'Change':>8s}")
        print(f"  {'─'*6}  {'─'*16}  {'─'*8}  {'─'*8}  {'─'*8}")
        
        for rn in sorted(famous.keys()):
            if rn in coords:
                v2_rank = next(i+1 for i, (r, _) in enumerate(ranked) if r == rn)
                v1_rank = old_rank_map.get(str(rn), old_rank_map.get(rn, '?'))
                if isinstance(v1_rank, int):
                    change = v1_rank - v2_rank  # positive = improved
                    arrow = f"{'↑' if change > 0 else '↓' if change < 0 else '='}{abs(change)}"
                else:
                    arrow = "?"
                print(f"  R{rn:>4d}  {famous[rn]:>16s}  {str(v1_rank):>8s}  {v2_rank:>8d}  {arrow:>8s}")
    
    # ─── Deep dive: R75 and R89 ───
    print(f"\n{'='*78}")
    print(f"  MYSTERY RULES: R75 and R89")
    print(f"  These ranked #1 on the invariant memory metric. Why?")
    print(f"{'='*78}")
    
    for rn in [75, 89]:
        if rn in coords and rn in mem_by_rule and rn in trans_by_rule and rn in xform_by_rule:
            investigate_rule(rn, mem_by_rule[rn], trans_by_rule[rn], xform_by_rule[rn], coords[rn])
    
    # Compare R75, R89, R110, R30
    print(f"\n── HEAD-TO-HEAD: The Contenders ──\n")
    contenders = [75, 89, 110, 30, 62]
    print(f"  {'Rule':>4s}  {'Mem':>7s}  {'Trans':>7s}  {'Xform':>7s}  {'Triple':>7s}  {'Combined':>9s}  {'Rank':>4s}")
    print(f"  {'─'*4}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*9}  {'─'*4}")
    for rn in contenders:
        if rn in coords:
            c = coords[rn]
            rank = next(i+1 for i, (r, _) in enumerate(ranked) if r == rn)
            print(f"  R{rn:>3d}  {c['memory_norm']:>7.3f}  {c['transport_norm']:>7.3f}  "
                  f"{c['transform_norm']:>7.3f}  {c['triple']:>7.3f}  {c['combined']:>9.4f}  #{rank}")
    
    # ─── Wolfram class analysis ───
    print(f"\n{'='*78}")
    print(f"  WOLFRAM CLASS ANALYSIS (V2)")
    print(f"{'='*78}\n")
    
    # Known Wolfram classes
    wolfram_classes = {
        1: [0, 8, 32, 40, 128, 136, 160, 168],  # Uniform
        2: [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 19, 23, 24, 25, 
            26, 27, 28, 29, 33, 34, 35, 36, 37, 38, 42, 43, 44, 46, 50, 51,
            56, 57, 58, 62, 72, 73, 74, 76, 77, 78, 94, 104, 108, 130, 132,
            134, 138, 140, 142, 152, 154, 156, 162, 164, 170, 172, 178, 184,
            200, 204, 232],  # Periodic
        3: [18, 22, 30, 45, 60, 90, 105, 122, 126, 146, 150, 182],  # Chaotic
        4: [41, 54, 106, 110],  # Complex
    }
    
    print(f"  {'Class':>7s}  {'Count':>5s}  {'Avg Combined':>13s}  {'Avg Memory':>11s}  {'Avg Transport':>14s}  {'Avg Transform':>14s}")
    print(f"  {'─'*7}  {'─'*5}  {'─'*13}  {'─'*11}  {'─'*14}  {'─'*14}")
    
    for cls in [1, 2, 3, 4]:
        members = [r for r in wolfram_classes[cls] if r in coords]
        if members:
            avg_comb = sum(coords[r]['combined'] for r in members) / len(members)
            avg_m = sum(coords[r]['memory_norm'] for r in members) / len(members)
            avg_t = sum(coords[r]['transport_norm'] for r in members) / len(members)
            avg_x = sum(coords[r]['transform_norm'] for r in members) / len(members)
            print(f"  Class {cls}  {len(members):>5d}  {avg_comb:>13.4f}  {avg_m:>11.3f}  {avg_t:>14.3f}  {avg_x:>14.3f}")
    
    # ─── The ASCII scatter plot ───
    print(f"\n── MEMORY (V2) vs TRANSFORMATION — Transport as marker ──\n")
    
    PLOT_W, PLOT_H = 60, 25
    grid = [[' ' for _ in range(PLOT_W)] for _ in range(PLOT_H)]
    
    for rn, c in coords.items():
        x = int(c['memory_norm'] * (PLOT_W - 1))
        y = PLOT_H - 1 - int(c['transform_norm'] * (PLOT_H - 1))
        x = max(0, min(PLOT_W - 1, x))
        y = max(0, min(PLOT_H - 1, y))
        
        if rn in famous:
            label = str(rn)
            for ci, ch in enumerate(label):
                if x + ci < PLOT_W:
                    grid[y][x + ci] = ch
        elif grid[y][x] == ' ':
            if c['transport_norm'] > 0.5:
                grid[y][x] = '●'
            elif c['transport_norm'] > 0.2:
                grid[y][x] = '·'
            else:
                grid[y][x] = '.'
    
    print("  Transform ↑")
    for row in grid:
        print("  │" + ''.join(row))
    print("  └" + "─" * PLOT_W + "→ Memory (invariant)")
    print()
    
    # ─── The Verdict ───
    print(f"\n{'='*78}")
    print(f"  THE VERDICT")
    print(f"{'='*78}\n")
    
    if 110 in coords:
        r110 = coords[110]
        r110_rank = next(i+1 for i, (r, _) in enumerate(ranked) if r == 110)
        
        # Check: is R62 properly separated?
        if 62 in coords:
            r62 = coords[62]
            r62_rank = next(i+1 for i, (r, _) in enumerate(ranked) if r == 62)
            print(f"  R110: rank {r110_rank}/{len(ranked)} (combined={r110['combined']:.4f})")
            print(f"  R62:  rank {r62_rank}/{len(ranked)} (combined={r62['combined']:.4f})")
            if r110_rank < r62_rank:
                print(f"  ✅ R110 properly ranks above R62 (the periodic impostor)")
            else:
                print(f"  ❌ R62 still ranks above R110 — something's wrong")
        
        # Check: does R110 sit at triple point?
        if (r110['memory_norm'] > 0.3 and r110['transport_norm'] > 0.3 and r110['transform_norm'] > 0.3):
            print(f"\n  ✅ R110 IS AT THE TRIPLE POINT (V2)")
            print(f"     M={r110['memory_norm']:.3f}  T={r110['transport_norm']:.3f}  X={r110['transform_norm']:.3f}")
        else:
            weak = []
            if r110['memory_norm'] <= 0.3: weak.append(f"Memory ({r110['memory_norm']:.3f})")
            if r110['transport_norm'] <= 0.3: weak.append(f"Transport ({r110['transport_norm']:.3f})")
            if r110['transform_norm'] <= 0.3: weak.append(f"Transform ({r110['transform_norm']:.3f})")
            print(f"\n  ⚠️  R110 weak axes: {', '.join(weak)}")
        
        # Check: do Class 4 rules cluster near the triple point?
        class4 = [r for r in wolfram_classes[4] if r in coords]
        class4_avg_combined = sum(coords[r]['combined'] for r in class4) / len(class4) if class4 else 0
        class2_members = [r for r in wolfram_classes[2] if r in coords]
        class2_avg = sum(coords[r]['combined'] for r in class2_members) / len(class2_members) if class2_members else 0
        
        if class4_avg_combined > class2_avg * 1.5:
            print(f"\n  ✅ Class 4 (complex) separates from Class 2 (periodic)")
            print(f"     Class 4 avg: {class4_avg_combined:.4f}  vs  Class 2 avg: {class2_avg:.4f}")
        
        # The key question from Day 013: does the new memory metric improve separation?
        print(f"\n  Key insight: With invariant memory, the triple point framework")
        print(f"  no longer rewards tape loops. Periodic rules that just repeat")
        print(f"  are penalized on the memory axis, pushing them away from the")
        print(f"  triple point where genuine computers live.")
    
    # Save
    save_data = {
        'version': 'v2-invariant-memory',
        'coordinates': {str(r): c for r, c in coords.items()},
        'rankings': [(r, c['combined']) for r, c in ranked[:50]],
        'class_averages': {},
    }
    
    for cls in [1, 2, 3, 4]:
        members = [r for r in wolfram_classes[cls] if r in coords]
        if members:
            save_data['class_averages'][f'class_{cls}'] = {
                'combined': sum(coords[r]['combined'] for r in members) / len(members),
                'memory': sum(coords[r]['memory_norm'] for r in members) / len(members),
                'transport': sum(coords[r]['transport_norm'] for r in members) / len(members),
                'transform': sum(coords[r]['transform_norm'] for r in members) / len(members),
            }
    
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'triple_point_v2_results.json')
    with open(out_path, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\n  Results saved to triple_point_v2_results.json")
    
    return coords, ranked


if __name__ == '__main__':
    coords, ranked = main()
