#!/usr/bin/env python3
"""
The Triple Point V3 — Separating Chaos from Computation

Day 014 diagnosis: V2 fixed the periodicity bias but introduced a chaotic bias.
R75/R89 (chaotic) dominate the rankings because "not periodic" includes both 
chaos and computation.

The fix: integrate perturbation coherence into the memory axis.

The hierarchy of unpredictability:
  1. Dead/uniform — perfectly predictable → score=0
  2. Periodic — predictable from recent history → score≈0 (V2 caught this)
  3. Chaotic — unpredictable, damage is RANDOM → score should be low (V3 target)
  4. Computational — unpredictable, damage is STRUCTURED → score should be high

Key insight: When you perturb R110, the damage propagates along glider paths — 
it's a clean "damage cone" with high R² (coherence). When you perturb R75/R30, 
the damage splatters randomly — low R² (incoherent).

V3 formula:
  Memory axis = invariant_memory × perturbation_coherence_factor
  
  Where perturbation_coherence_factor uses multiple perturbation trials to get
  a robust estimate of how structured the damage pattern is.
"""

import json
import math
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from automata import make_rule, evolve, single_seed, block_entropy


# ─── Perturbation Coherence (enhanced from spatial_transport.py) ───

def multi_perturbation_coherence(rule_num, width=121, steps=120, n_trials=5):
    """Run multiple perturbation trials at different positions.
    
    Single perturbation trail can be noisy. We average over multiple
    perturbation sites to get a robust coherence estimate.
    
    Returns:
        - mean_coherence: average R² of damage trajectories
        - mean_spread: average spatial spread of damage
        - mean_damage: average fraction of cells affected
        - damage_structure: ratio of coherent to total damage (the key metric)
    """
    rule = make_rule(rule_num)
    
    coherences = []
    spreads = []
    damages = []
    
    for trial in range(n_trials):
        base = single_seed(width)
        perturbed = base[:]
        
        # Perturb at different positions around center
        if trial == 0:
            perturb_pos = width // 2 + 3
        else:
            perturb_pos = width // 2 + random.randint(-15, 15)
        
        perturb_pos = max(1, min(width - 2, perturb_pos))
        perturbed[perturb_pos] = 1 - perturbed[perturb_pos]
        
        hist_a = evolve(rule, base, steps)
        hist_b = evolve(rule, perturbed, steps)
        
        trail = []
        for t in range(steps + 1):
            diff = [abs(a - b) for a, b in zip(hist_a[t], hist_b[t])]
            damage_sum = sum(diff)
            
            if damage_sum > 0:
                com = sum(i * d for i, d in enumerate(diff)) / damage_sum
                trail.append((t, com, damage_sum))
        
        if len(trail) < 5:
            coherences.append(0.0)
            spreads.append(0.0)
            damages.append(0.0)
            continue
        
        # Use settled portion
        settled = trail[len(trail)//4:]
        if len(settled) < 3:
            settled = trail
        
        ts = [p[0] for p in settled]
        xs = [p[1] for p in settled]
        dmgs = [p[2] / width for p in settled]
        
        n = len(ts)
        mean_t = sum(ts) / n
        mean_x = sum(xs) / n
        
        cov_tx = sum((ts[i] - mean_t) * (xs[i] - mean_x) for i in range(n)) / n
        var_t = sum((ts[i] - mean_t) ** 2 for i in range(n)) / n
        var_x = sum((xs[i] - mean_x) ** 2 for i in range(n)) / n
        
        if var_t > 1e-10 and var_x > 1e-10:
            r = cov_tx / math.sqrt(var_t * var_x)
            coherence = r * r
        else:
            coherence = 0.0 if var_x > 1e-10 else 1.0  # No movement = coherent (stays put)
        
        # Spread of damage
        spread_vals = []
        for t_idx, com, dmg in settled:
            diff = [abs(a - b) for a, b in zip(hist_a[t_idx], hist_b[t_idx])]
            if dmg > 0:
                var_pos = sum((i - com) ** 2 * d for i, d in enumerate(diff)) / dmg
                spread_vals.append(math.sqrt(var_pos))
        
        coherences.append(coherence)
        spreads.append(sum(spread_vals) / len(spread_vals) if spread_vals else 0.0)
        damages.append(sum(dmgs) / len(dmgs))
    
    mean_coherence = sum(coherences) / len(coherences) if coherences else 0.0
    mean_spread = sum(spreads) / len(spreads) if spreads else 0.0
    mean_damage = sum(damages) / len(damages) if damages else 0.0
    
    # Damage structure score: coherent damage with moderate (not maximal) magnitude
    # Chaos: high damage + low coherence → low score
    # Computation: moderate damage + high coherence → high score
    # Frozen: low damage + high coherence → moderate score (caught by other axes)
    
    if mean_damage < 0.01:
        damage_structure = 0.0  # No damage = nothing to analyze
    else:
        # Penalize both maximal damage (chaos) and minimal damage (frozen)
        # Sweet spot around 0.15-0.35 (computational range)
        damage_moderation = 1.0 - abs(2.0 * mean_damage - 0.5)  # Peaks at 0.25
        damage_moderation = max(0.0, min(1.0, damage_moderation))
        
        # But don't over-penalize — coherence matters more
        damage_structure = mean_coherence * (0.4 + 0.6 * damage_moderation)
    
    return {
        'mean_coherence': mean_coherence,
        'mean_spread': mean_spread, 
        'mean_damage': mean_damage,
        'damage_structure': damage_structure,
        'coherences': coherences,
    }


# ─── Data Loading ───

def load_data():
    """Load all axis datasets."""
    base = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(base, 'memory_invariant_results.json')) as f:
        memory_data = json.load(f)
    
    with open(os.path.join(base, 'spatial_transport_results.json')) as f:
        transport_data = json.load(f)
    
    with open(os.path.join(base, 'transformation_results.json')) as f:
        transform_data = json.load(f)
    
    return memory_data, transport_data, transform_data


def normalize(values):
    mn, mx = min(values), max(values)
    rng = mx - mn
    if rng < 1e-10:
        return [0.5] * len(values)
    return [(v - mn) / rng for v in values]


def geometric_mean_3(a, b, c, eps=0.01):
    return (max(a, eps) * max(b, eps) * max(c, eps)) ** (1/3)


def balance(a, b, c):
    mean = (a + b + c) / 3
    if mean < 0.01:
        return 0.0
    var = ((a - mean)**2 + (b - mean)**2 + (c - mean)**2) / 3
    cv = math.sqrt(var) / mean
    return max(0.0, 1.0 - cv)


# ─── Main ───

def main():
    print("=" * 78)
    print("  THE TRIPLE POINT V3 — Separating Chaos from Computation")
    print("  'Chaos destroys information. Computation transforms it.'")
    print("=" * 78)
    
    # First: compute perturbation coherence for all 256 rules
    print("\n── PHASE 1: Computing perturbation coherence for all 256 rules ──\n")
    
    random.seed(42)  # Reproducible
    
    perturbation_results = {}
    for r in range(256):
        if r % 32 == 0:
            print(f"  Processing rules {r}-{min(r+31, 255)}...")
        perturbation_results[r] = multi_perturbation_coherence(r, width=121, steps=120, n_trials=5)
    
    # ─── Show key rules ───
    print("\n── PERTURBATION COHERENCE: Key Rules ──\n")
    
    key_rules = {
        0: "Dead", 30: "Chaos", 54: "Complex", 62: "Periodic",
        75: "Mystery", 89: "Mystery", 90: "XOR", 110: "Turing-complete", 184: "Traffic"
    }
    
    print(f"  {'Rule':>6s}  {'Name':>16s}  {'Coherence':>10s}  {'Spread':>8s}  {'Damage':>8s}  {'Structure':>10s}")
    print(f"  {'─'*6}  {'─'*16}  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*10}")
    
    for rn in sorted(key_rules.keys()):
        p = perturbation_results[rn]
        print(f"  R{rn:>4d}  {key_rules[rn]:>16s}  {p['mean_coherence']:>10.4f}  "
              f"{p['mean_spread']:>8.2f}  {p['mean_damage']:>8.4f}  {p['damage_structure']:>10.4f}")
    
    # ─── The critical comparison ───
    print("\n── THE CRITICAL TEST: R75 (chaos) vs R110 (computation) ──\n")
    
    p75 = perturbation_results[75]
    p110 = perturbation_results[110]
    p30 = perturbation_results[30]
    
    print(f"  R75  (chaos):       coherence={p75['mean_coherence']:.4f}  damage={p75['mean_damage']:.4f}  structure={p75['damage_structure']:.4f}")
    print(f"  R30  (chaos):       coherence={p30['mean_coherence']:.4f}  damage={p30['mean_damage']:.4f}  structure={p30['damage_structure']:.4f}")
    print(f"  R110 (computation): coherence={p110['mean_coherence']:.4f}  damage={p110['mean_damage']:.4f}  structure={p110['damage_structure']:.4f}")
    
    if p110['damage_structure'] > p75['damage_structure']:
        print(f"\n  ✅ R110 has more structured damage than R75!")
        print(f"     Structure ratio: {p110['damage_structure'] / max(p75['damage_structure'], 0.001):.2f}x")
    else:
        print(f"\n  ⚠️  R75 still shows more structure — need to refine the metric")
    
    # ─── PHASE 2: Build V3 triple point ───
    print(f"\n\n{'='*78}")
    print(f"  PHASE 2: Building V3 Triple Point")
    print(f"{'='*78}\n")
    
    memory_data, transport_data, transform_data = load_data()
    
    mem_by_rule = {e['rule']: e for e in memory_data['all_256']}
    transport_list = transport_data.get('all_256', transport_data if isinstance(transport_data, list) else [])
    trans_by_rule = {e['rule']: e for e in transport_list}
    transform_list = transform_data.get('all_256', transform_data if isinstance(transform_data, list) else [])
    xform_by_rule = {e['rule']: e for e in transform_list}
    
    # Build V3 coordinates
    complete_rules = []
    raw_mem_v3 = []  # Memory × perturbation coherence
    raw_mem_v2 = []  # Original V2 memory for comparison
    raw_trans = []
    raw_xform = []
    
    for r in range(256):
        if r in mem_by_rule and r in trans_by_rule and r in xform_by_rule and r in perturbation_results:
            complete_rules.append(r)
            
            inv_mem = mem_by_rule[r]['invariant_memory_score']
            pert_struct = perturbation_results[r]['damage_structure']
            
            # V3 memory: invariant_memory weighted by perturbation structure
            # This penalizes chaotic rules whose "memory" is just noise
            v3_mem = inv_mem * (0.3 + 0.7 * pert_struct)
            
            raw_mem_v3.append(v3_mem)
            raw_mem_v2.append(inv_mem)
            raw_trans.append(trans_by_rule[r].get('combined_score', 0))
            raw_xform.append(xform_by_rule[r].get('transformation_score', 0))
    
    print(f"  Rules with all axes: {len(complete_rules)}/256")
    
    # Normalize
    norm_mem = normalize(raw_mem_v3)
    norm_mem_v2 = normalize(raw_mem_v2)
    norm_trans = normalize(raw_trans)
    norm_xform = normalize(raw_xform)
    
    # Build coordinate maps for V2 and V3
    coords_v3 = {}
    coords_v2 = {}
    
    for i, r in enumerate(complete_rules):
        # V3
        m, t, x = norm_mem[i], norm_trans[i], norm_xform[i]
        triple = geometric_mean_3(m, t, x)
        bal = balance(m, t, x)
        combined = triple * (0.7 + 0.3 * bal)
        
        coords_v3[r] = {
            'memory_norm': m, 'transport_norm': t, 'transform_norm': x,
            'memory_raw': raw_mem_v3[i], 'transport_raw': raw_trans[i], 'transform_raw': raw_xform[i],
            'triple': triple, 'balance': bal, 'combined': combined,
            'perturbation_coherence': perturbation_results[r]['mean_coherence'],
            'perturbation_damage': perturbation_results[r]['mean_damage'],
            'damage_structure': perturbation_results[r]['damage_structure'],
        }
        
        # V2 for comparison
        m2, t2, x2 = norm_mem_v2[i], norm_trans[i], norm_xform[i]
        triple2 = geometric_mean_3(m2, t2, x2)
        bal2 = balance(m2, t2, x2)
        combined2 = triple2 * (0.7 + 0.3 * bal2)
        
        coords_v2[r] = {
            'memory_norm': m2, 'combined': combined2,
        }
    
    # Rank both
    ranked_v3 = sorted(coords_v3.items(), key=lambda x: -x[1]['combined'])
    ranked_v2 = sorted(coords_v2.items(), key=lambda x: -x[1]['combined'])
    
    v2_rank_map = {r: i+1 for i, (r, _) in enumerate(ranked_v2)}
    v3_rank_map = {r: i+1 for i, (r, _) in enumerate(ranked_v3)}
    
    # ─── Top 25 ───
    print(f"\n{'='*78}")
    print(f"  TOP 25 — TRIPLE POINT V3 RANKING")
    print(f"{'='*78}\n")
    
    famous = {
        0: "Dead", 30: "Chaos", 54: "Complex", 62: "Periodic",
        67: "Conveyor", 75: "Mystery #1", 89: "Mystery #2",
        90: "XOR fractal", 110: "Turing-complete", 184: "Traffic"
    }
    
    print(f"  {'Rank':>4s}  {'Rule':>4s}  {'Combined':>9s}  {'M':>5s}  {'T':>5s}  {'X':>5s}  {'Coh':>5s}  {'Dmg':>5s}  {'V2→V3':>7s}")
    print(f"  {'─'*4}  {'─'*4}  {'─'*9}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*7}")
    
    for rank, (rn, c) in enumerate(ranked_v3[:25], 1):
        v2r = v2_rank_map.get(rn, '?')
        if isinstance(v2r, int):
            change = v2r - rank
            arrow = f"{'↑' if change > 0 else '↓' if change < 0 else '='}{abs(change)}"
        else:
            arrow = "?"
        
        marker = f" ◄ {famous[rn]}" if rn in famous else ""
        print(f"  {rank:>4d}  R{rn:>3d}  {c['combined']:>9.4f}  {c['memory_norm']:>.3f}  {c['transport_norm']:>.3f}  "
              f"{c['transform_norm']:>.3f}  {c['perturbation_coherence']:>.3f}  {c['perturbation_damage']:>.3f}  "
              f"{arrow:>7s}{marker}")
    
    # ─── V2 → V3 changes for famous rules ───
    print(f"\n{'='*78}")
    print(f"  V2 → V3 CHANGES FOR FAMOUS RULES")
    print(f"{'='*78}\n")
    
    print(f"  {'Rule':>6s}  {'Name':>16s}  {'V2 Rank':>8s}  {'V3 Rank':>8s}  {'Change':>8s}  {'Coherence':>10s}  {'DmgStruct':>10s}")
    print(f"  {'─'*6}  {'─'*16}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*10}  {'─'*10}")
    
    for rn in sorted(famous.keys()):
        if rn in coords_v3:
            v2r = v2_rank_map.get(rn, 999)
            v3r = v3_rank_map.get(rn, 999)
            change = v2r - v3r
            arrow = f"{'↑' if change > 0 else '↓' if change < 0 else '='}{abs(change)}"
            c = coords_v3[rn]
            print(f"  R{rn:>4d}  {famous[rn]:>16s}  {v2r:>8d}  {v3r:>8d}  {arrow:>8s}  "
                  f"{c['perturbation_coherence']:>10.4f}  {c['damage_structure']:>10.4f}")
    
    # ─── Head-to-head: The contenders ───
    print(f"\n── HEAD-TO-HEAD: The Contenders ──\n")
    contenders = [75, 89, 30, 110, 54, 62]
    print(f"  {'Rule':>4s}  {'V2 Rank':>8s}  {'V3 Rank':>8s}  {'V3 Mem':>7s}  {'Coherence':>10s}  {'Structure':>10s}  {'V3 Combined':>12s}")
    print(f"  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*7}  {'─'*10}  {'─'*10}  {'─'*12}")
    for rn in contenders:
        if rn in coords_v3:
            c = coords_v3[rn]
            print(f"  R{rn:>3d}  {v2_rank_map.get(rn,'?'):>8}  {v3_rank_map.get(rn,'?'):>8}  "
                  f"{c['memory_norm']:>7.3f}  {c['perturbation_coherence']:>10.4f}  "
                  f"{c['damage_structure']:>10.4f}  {c['combined']:>12.4f}")
    
    # ─── Wolfram class analysis ───
    print(f"\n{'='*78}")
    print(f"  WOLFRAM CLASS ANALYSIS (V3 vs V2)")
    print(f"{'='*78}\n")
    
    wolfram_classes = {
        1: [0, 8, 32, 40, 128, 136, 160, 168],
        2: [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 19, 23, 24, 25,
            26, 27, 28, 29, 33, 34, 35, 36, 37, 38, 42, 43, 44, 46, 50, 51,
            56, 57, 58, 62, 72, 73, 74, 76, 77, 78, 94, 104, 108, 130, 132,
            134, 138, 140, 142, 152, 154, 156, 162, 164, 170, 172, 178, 184,
            200, 204, 232],
        3: [18, 22, 30, 45, 60, 90, 105, 122, 126, 146, 150, 182],
        4: [41, 54, 106, 110],
    }
    
    print(f"  {'Class':>7s}  {'V2 Avg':>8s}  {'V3 Avg':>8s}  {'Change':>8s}  {'V3 Mem':>7s}  {'V3 Trans':>9s}  {'V3 Xform':>9s}")
    print(f"  {'─'*7}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*7}  {'─'*9}  {'─'*9}")
    
    for cls in [1, 2, 3, 4]:
        members = [r for r in wolfram_classes[cls] if r in coords_v3]
        if members:
            avg_v3 = sum(coords_v3[r]['combined'] for r in members) / len(members)
            avg_v2 = sum(coords_v2[r]['combined'] for r in members) / len(members)
            avg_m = sum(coords_v3[r]['memory_norm'] for r in members) / len(members)
            avg_t = sum(coords_v3[r]['transport_norm'] for r in members) / len(members)
            avg_x = sum(coords_v3[r]['transform_norm'] for r in members) / len(members)
            change = avg_v3 - avg_v2
            arrow = "↑" if change > 0.001 else "↓" if change < -0.001 else "="
            print(f"  Class {cls}  {avg_v2:>8.4f}  {avg_v3:>8.4f}  {arrow}{abs(change):>.4f}  "
                  f"{avg_m:>7.3f}  {avg_t:>9.3f}  {avg_x:>9.3f}")
    
    # ─── The Verdict ───
    print(f"\n{'='*78}")
    print(f"  THE VERDICT: Does V3 Fix the Chaos Problem?")
    print(f"{'='*78}\n")
    
    # Check 1: R75 should rank lower than R110
    r75_v3 = v3_rank_map.get(75, 999)
    r110_v3 = v3_rank_map.get(110, 999)
    r75_v2 = v2_rank_map.get(75, 999)
    r110_v2 = v2_rank_map.get(110, 999)
    
    print(f"  Test 1: R110 should rank above R75")
    print(f"    V2: R110=#{r110_v2}, R75=#{r75_v2} {'✅' if r110_v2 < r75_v2 else '❌'}")
    print(f"    V3: R110=#{r110_v3}, R75=#{r75_v3} {'✅' if r110_v3 < r75_v3 else '❌'}")
    
    # Check 2: Class 4 should separate from Class 3
    class3 = [r for r in wolfram_classes[3] if r in coords_v3]
    class4 = [r for r in wolfram_classes[4] if r in coords_v3]
    avg_c3 = sum(coords_v3[r]['combined'] for r in class3) / len(class3) if class3 else 0
    avg_c4 = sum(coords_v3[r]['combined'] for r in class4) / len(class4) if class4 else 0
    
    print(f"\n  Test 2: Class 4 (complex) should separate from Class 3 (chaotic)")
    print(f"    V3 Class 4 avg: {avg_c4:.4f}")
    print(f"    V3 Class 3 avg: {avg_c3:.4f}")
    print(f"    Separation: {avg_c4/avg_c3:.2f}x {'✅' if avg_c4 > avg_c3 * 1.3 else '⚠️' if avg_c4 > avg_c3 else '❌'}")
    
    # Check 3: R62 should still be demoted
    r62_v3 = v3_rank_map.get(62, 999)
    print(f"\n  Test 3: R62 (periodic) should still be demoted")
    print(f"    V3 rank: #{r62_v3} {'✅ (below #15)' if r62_v3 > 15 else '⚠️'}")
    
    # ─── Summary ───
    print(f"\n{'='*78}")
    print(f"  PROGRESSION: V1 → V2 → V3")
    print(f"{'='*78}\n")
    print(f"  V1: Memory × Transport × Transformation")
    print(f"       Problem: Periodic rules dominate (R62 at #1)")
    print(f"  V2: Invariant Memory (with periodicity penalty) × Transport × Transformation")
    print(f"       Fixed: Periodic rules demoted")
    print(f"       Problem: Chaotic rules dominate (R75/R89 at #1)")
    print(f"  V3: Coherent Memory (invariant × perturbation coherence) × Transport × Transformation")
    
    if r110_v3 < r75_v3 and avg_c4 > avg_c3:
        print(f"       Fixed: Chaotic rules demoted, computational rules elevated")
        print(f"       Status: ✅ TRIPLE POINT HYPOTHESIS CONFIRMED")
        print(f"       → Computation = structured memory × structured transport × structured transformation")
    elif r110_v3 < r75_v3:
        print(f"       Improved: R110 now ranks above R75")
        print(f"       Remaining: Class 3/4 separation still weak")
    else:
        print(f"       Status: ⚠️ Partial improvement — chaos/computation boundary still blurry")
        print(f"       Next: Try different coherence integration (multiplicative vs additive)")
    
    # Save results
    save_data = {
        'version': 'v3-perturbation-coherence',
        'perturbation_results': {
            str(r): {k: v for k, v in p.items() if k != 'coherences'} 
            for r, p in perturbation_results.items()
        },
        'coordinates': {str(r): c for r, c in coords_v3.items()},
        'rankings': [(r, c['combined']) for r, c in ranked_v3[:50]],
        'v2_rankings': [(r, c['combined']) for r, c in ranked_v2[:50]],
    }
    
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'triple_point_v3_results.json')
    with open(out_path, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\n  Results saved to triple_point_v3_results.json")
    
    return coords_v3, ranked_v3


if __name__ == '__main__':
    coords, ranked = main()
