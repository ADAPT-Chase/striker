#!/usr/bin/env python3
"""
Random Seeds V4 — Does the Triple Point Survive Initial Conditions?

Day 015 identified a critical limitation: single-seed experiments bias toward
rules whose complexity is visible from minimal initial conditions. R110 shows
gliders from a single dot. R54 needs richer starting states. R184 transforms
under balanced random starts.

This experiment re-runs the V4 triple point framework with multiple random
initial conditions and measures:
1. Does the R110 equivalence class still dominate?
2. Does R54 rise when given richer seeds?
3. Does Class 4/Class 3 separation improve or degrade?
4. Which rules are "seed-fragile" vs "seed-robust"?

The answer determines whether the V4 result is a property of the RULES
or an artifact of the INITIAL CONDITIONS.
"""

import json
import math
import os
import sys
import random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from automata import make_rule, evolve, single_seed, block_entropy
from memory_invariant import invariant_memory_score
from spatial_transport import spatial_transport_score as combined_transport_score
from transformation import transformation_score as compute_transformation
from triple_point_v3 import multi_perturbation_coherence, normalize, geometric_mean_3, balance


# ─── Seed Generators ───

def random_seed(width, p=0.5):
    return [1 if random.random() < p else 0 for _ in range(width)]

def sparse_seed(width):
    return random_seed(width, p=0.15)

def dense_seed(width):
    return random_seed(width, p=0.85)

SEED_TYPES = {
    'single': lambda w: single_seed(w),
    'random_balanced': lambda w: random_seed(w, 0.5),
    'random_sparse': lambda w: sparse_seed(w),
    'random_dense': lambda w: dense_seed(w),
}


# ─── Metrics (adapted to take pre-computed history) ───

def memory_from_history(history, block_size=3):
    """Invariant memory score from a pre-computed history (fast version).
    
    Uses lag-1 TI-MI only (not full profile) for speed.
    """
    from memory_invariant import (
        translation_invariant_mi, periodicity_penalty
    )
    
    # Use settled portion
    start = len(history) // 4
    
    # Sample a few timesteps for TI-MI at lag=1
    mi_vals = []
    for t in range(start, len(history) - 1, 4):  # stride 4 for speed
        best_mi, best_shift, _ = translation_invariant_mi(
            history[t], history[t + 1], max_shift=6, block_size=block_size
        )
        mi_vals.append(best_mi)
    
    mean_ti_mi = sum(mi_vals) / len(mi_vals) if mi_vals else 0.0
    
    # Periodicity penalty
    pp = periodicity_penalty(history, block_size)
    
    # Combined score
    novelty_factor = 1.0 - pp ** 2
    return mean_ti_mi * novelty_factor


def transport_from_history(history):
    """Spatial transport score from pre-computed history using directional MI."""
    from spatial_transport import directional_mi
    
    # Compute directional MI across offsets
    dmi_spec = {}
    for offset in range(-6, 7):
        dmi_spec[offset] = directional_mi(history, block_size=3, lag=1, offset=offset)
    
    dmi_vals = list(dmi_spec.values())
    if not dmi_vals or max(dmi_vals) < 0.001:
        return 0.0
    
    peak_dmi = max(dmi_vals)
    zero_dmi = dmi_spec.get(0, 0)
    
    # Asymmetry and off-center peaks indicate spatial transport
    left_sum = sum(v for k, v in dmi_spec.items() if k < 0)
    right_sum = sum(v for k, v in dmi_spec.items() if k > 0)
    total = left_sum + right_sum + zero_dmi
    
    if total < 0.01:
        return 0.0
    
    asymmetry = abs(left_sum - right_sum) / total
    off_center_ratio = (peak_dmi - zero_dmi) / max(peak_dmi, 0.01) if peak_dmi > zero_dmi else 0
    
    transport = peak_dmi * (0.3 + 0.7 * max(asymmetry, off_center_ratio))
    return transport


def transformation_from_history(history, block_size=3):
    """Transformation score from pre-computed history."""
    from transformation import (
        directional_transfer_entropy, transformation_spectrum
    )
    
    te_spec = directional_transfer_entropy(history, block_size, lag=1, max_offset=6)
    pr_spec = transformation_spectrum(history, block_size, lag=1, max_offset=6)
    
    peak_offset = max(te_spec, key=te_spec.get)
    peak_te = te_spec[peak_offset]
    mean_pr = sum(pr_spec.values()) / len(pr_spec) if pr_spec else 0.0
    balance_factor = 4.0 * mean_pr * (1.0 - mean_pr)
    
    return peak_te * balance_factor


# ─── Main Experiment ───

def compute_rule_across_seeds(rule_num, width=101, steps=120, n_seeds=3):
    """Compute all three axes for a rule across multiple seed types."""
    rule = make_rule(rule_num)
    
    all_memory = []
    all_transport = []
    all_transform = []
    seed_results = {}
    
    for seed_name, seed_fn in SEED_TYPES.items():
        mem_trials = []
        trans_trials = []
        xform_trials = []
        
        n_trials = n_seeds if 'random' in seed_name else 1
        
        for trial in range(n_trials):
            random.seed(f"v4|{rule_num}|{seed_name}|{trial}")
            state = seed_fn(width)
            history = evolve(rule, state, steps)
            
            mem = memory_from_history(history)
            # For transport, use DMI-based approximation
            trans = transport_from_history(history)
            xform = transformation_from_history(history)
            
            mem_trials.append(mem)
            trans_trials.append(trans)
            xform_trials.append(xform)
        
        avg_mem = sum(mem_trials) / len(mem_trials)
        avg_trans = sum(trans_trials) / len(trans_trials)
        avg_xform = sum(xform_trials) / len(xform_trials)
        
        seed_results[seed_name] = {
            'memory': avg_mem,
            'transport': avg_trans,
            'transformation': avg_xform,
        }
        
        all_memory.append(avg_mem)
        all_transport.append(avg_trans)
        all_transform.append(avg_xform)
    
    # Overall: average across seed types
    overall_mem = sum(all_memory) / len(all_memory)
    overall_trans = sum(all_transport) / len(all_transport)
    overall_xform = sum(all_transform) / len(all_transform)
    
    # Robustness: coefficient of variation
    def cv(vals):
        if not vals or max(vals) < 0.001:
            return 0.0
        m = sum(vals) / len(vals)
        if m < 0.001:
            return 0.0
        v = sum((x - m)**2 for x in vals) / len(vals)
        return math.sqrt(v) / m
    
    return {
        'rule': rule_num,
        'memory': overall_mem,
        'transport': overall_trans,
        'transformation': overall_xform,
        'memory_cv': cv(all_memory),
        'transport_cv': cv(all_transport),
        'transformation_cv': cv(all_transform),
        'seed_results': seed_results,
    }


def main():
    print("=" * 78)
    print("  RANDOM SEEDS V4 — Does the Triple Point Survive Initial Conditions?")
    print("  'If a metric only works from one seed, it's measuring the seed, not the rule.'")
    print("=" * 78)
    print()
    
    random.seed(42)
    
    # ─── Phase 1: Compute all 256 rules across seed types ───
    print("Phase 1: Computing triple-point metrics across seed types...")
    print("  (4 seed types × 256 rules, 3 trials per random seed)")
    print()
    
    all_results = []
    for r in range(256):
        if r % 32 == 0:
            print(f"  Processing rules {r}-{min(r+31, 255)}...")
        result = compute_rule_across_seeds(r, width=71, steps=80, n_seeds=2)
        all_results.append(result)
    
    # ─── Phase 2: Also get perturbation coherence (V4 needs this) ───
    print("\nPhase 2: Computing perturbation coherence for V4 weighting...")
    
    random.seed(42)
    perturbation_data = {}
    for r in range(256):
        if r % 32 == 0:
            print(f"  Processing rules {r}-{min(r+31, 255)}...")
        perturbation_data[r] = multi_perturbation_coherence(r, width=71, steps=70, n_trials=2)
    
    # ─── Phase 3: Build rankings ───
    print("\n" + "=" * 78)
    print("  PHASE 3: Building V4-Random Rankings")
    print("=" * 78)
    
    # Get raw values
    raw_mem = [r['memory'] for r in all_results]
    raw_trans = [r['transport'] for r in all_results]
    raw_xform = [r['transformation'] for r in all_results]
    
    # Normalize
    norm_mem = normalize(raw_mem)
    norm_trans = normalize(raw_trans)
    norm_xform = normalize(raw_xform)
    
    # Build V4 scores (with coherence weighting)
    coords = {}
    for i, r in enumerate(all_results):
        rule_num = r['rule']
        m, t, x = norm_mem[i], norm_trans[i], norm_xform[i]
        
        # V4: apply perturbation coherence as global weight
        coherence = perturbation_data[rule_num]['mean_coherence']
        coherence_weight = 0.3 + 0.7 * coherence
        
        triple = geometric_mean_3(m, t, x)
        bal = balance(m, t, x)
        raw_combined = triple * (0.7 + 0.3 * bal)
        v4_combined = raw_combined * coherence_weight
        
        coords[rule_num] = {
            'memory': m,
            'transport': t,
            'transformation': x,
            'raw_memory': raw_mem[i],
            'raw_transport': raw_trans[i],
            'raw_transformation': raw_xform[i],
            'coherence': coherence,
            'coherence_weight': coherence_weight,
            'combined': v4_combined,
            'raw_combined': raw_combined,
            'memory_cv': r['memory_cv'],
            'transport_cv': r['transport_cv'],
            'transformation_cv': r['transformation_cv'],
        }
    
    # Rank
    ranked = sorted(coords.items(), key=lambda x: -x[1]['combined'])
    rank_map = {r: i+1 for i, (r, _) in enumerate(ranked)}
    
    # ─── Top 25 ───
    print(f"\n  TOP 25 — V4 with Random Seeds\n")
    
    famous = {
        0: "Dead", 30: "Chaos", 54: "Complex", 62: "Periodic",
        67: "Conveyor", 75: "Chaos#2", 89: "Chaos#3",
        90: "XOR", 110: "Turing", 184: "Traffic"
    }
    
    print(f"  {'Rk':>3s}  {'Rule':>4s}  {'V4-R':>7s}  {'M':>5s}  {'T':>5s}  {'X':>5s}  {'Coh':>5s}  {'M-CV':>5s}")
    print(f"  {'─'*3}  {'─'*4}  {'─'*7}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*5}")
    
    for rank, (rn, c) in enumerate(ranked[:25], 1):
        marker = f" ◄ {famous[rn]}" if rn in famous else ""
        print(f"  {rank:>3d}  R{rn:>3d}  {c['combined']:>7.4f}  {c['memory']:>.3f}  {c['transport']:>.3f}  "
              f"{c['transformation']:>.3f}  {c['coherence']:>.3f}  {c['memory_cv']:>.3f}{marker}")
    
    # ─── Famous rules comparison ───
    print(f"\n{'='*78}")
    print(f"  FAMOUS RULES: Single-Seed V4 vs Random-Seed V4")
    print(f"{'='*78}\n")
    
    # Load original V4 results for comparison
    v3_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'triple_point_v3_results.json')
    try:
        with open(v3_path) as f:
            v3_data = json.load(f)
        v3_rankings = {r: i+1 for i, (r, _) in enumerate(v3_data.get('rankings', []))}
    except FileNotFoundError:
        v3_rankings = {}
    
    print(f"  {'Rule':>6s}  {'Name':>12s}  {'V4-Single':>10s}  {'V4-Random':>10s}  {'Change':>8s}  {'Seed CV':>8s}")
    print(f"  {'─'*6}  {'─'*12}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*8}")
    
    for rn in sorted(famous.keys()):
        if rn in coords:
            v4s_rank = v3_rankings.get(rn, '?')
            v4r_rank = rank_map.get(rn, '?')
            c = coords[rn]
            avg_cv = (c['memory_cv'] + c['transport_cv'] + c['transformation_cv']) / 3
            
            if isinstance(v4s_rank, int) and isinstance(v4r_rank, int):
                change = v4s_rank - v4r_rank
                arrow = f"{'↑' if change > 0 else '↓' if change < 0 else '='}{abs(change)}"
            else:
                arrow = "?"
            
            print(f"  R{rn:>4d}  {famous[rn]:>12s}  #{str(v4s_rank):>9s}  #{v4r_rank:>9d}  {arrow:>8s}  {avg_cv:>8.3f}")
    
    # ─── Wolfram class analysis ───
    print(f"\n{'='*78}")
    print(f"  WOLFRAM CLASS ANALYSIS")
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
    
    print(f"  {'Class':>7s}  {'Avg Score':>10s}  {'Avg Rank':>9s}  {'Avg M-CV':>9s}  {'Members':>8s}")
    print(f"  {'─'*7}  {'─'*10}  {'─'*9}  {'─'*9}  {'─'*8}")
    
    class_avgs = {}
    for cls in [1, 2, 3, 4]:
        members = [r for r in wolfram_classes[cls] if r in coords]
        if members:
            avg_score = sum(coords[r]['combined'] for r in members) / len(members)
            avg_rank = sum(rank_map[r] for r in members) / len(members)
            avg_mcv = sum(coords[r]['memory_cv'] for r in members) / len(members)
            class_avgs[cls] = avg_score
            print(f"  Class {cls}  {avg_score:>10.4f}  {avg_rank:>9.1f}  {avg_mcv:>9.3f}  {len(members):>8d}")
    
    # Class 4 / Class 3 separation
    if 4 in class_avgs and 3 in class_avgs:
        ratio = class_avgs[4] / class_avgs[3] if class_avgs[3] > 0.001 else 0
        print(f"\n  Class 4 / Class 3 separation: {ratio:.2f}x {'✅' if ratio > 1.0 else '❌'}")
        print(f"  (V4 single-seed was 1.23x)")
    
    # ─── Seed Robustness Analysis ───
    print(f"\n{'='*78}")
    print(f"  SEED ROBUSTNESS: Which Rules Change Most?")
    print(f"{'='*78}\n")
    
    # Find most seed-sensitive rules (high CV)
    by_cv = sorted(all_results, key=lambda r: -(r['memory_cv'] + r['transport_cv'] + r['transformation_cv']) / 3)
    
    print("  Most seed-FRAGILE rules (high CV across seed types):\n")
    print(f"  {'Rule':>4s}  {'M-CV':>6s}  {'T-CV':>6s}  {'X-CV':>6s}  {'Avg CV':>7s}  {'Rank':>5s}")
    print(f"  {'─'*4}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*7}  {'─'*5}")
    for r in by_cv[:15]:
        rn = r['rule']
        avg_cv = (r['memory_cv'] + r['transport_cv'] + r['transformation_cv']) / 3
        marker = f" ◄ {famous[rn]}" if rn in famous else ""
        print(f"  R{rn:>3d}  {r['memory_cv']:>6.3f}  {r['transport_cv']:>6.3f}  {r['transformation_cv']:>6.3f}  {avg_cv:>7.3f}  #{rank_map[rn]:>4d}{marker}")
    
    print("\n  Most seed-ROBUST rules (low CV across seed types):\n")
    by_cv_low = sorted([r for r in all_results if coords[r['rule']]['combined'] > 0.1],
                       key=lambda r: (r['memory_cv'] + r['transport_cv'] + r['transformation_cv']) / 3)
    
    print(f"  {'Rule':>4s}  {'M-CV':>6s}  {'T-CV':>6s}  {'X-CV':>6s}  {'Avg CV':>7s}  {'Rank':>5s}")
    print(f"  {'─'*4}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*7}  {'─'*5}")
    for r in by_cv_low[:15]:
        rn = r['rule']
        avg_cv = (r['memory_cv'] + r['transport_cv'] + r['transformation_cv']) / 3
        marker = f" ◄ {famous[rn]}" if rn in famous else ""
        print(f"  R{rn:>3d}  {r['memory_cv']:>6.3f}  {r['transport_cv']:>6.3f}  {r['transformation_cv']:>6.3f}  {avg_cv:>7.3f}  #{rank_map[rn]:>4d}{marker}")
    
    # ─── R54 Deep Dive ───
    print(f"\n{'='*78}")
    print(f"  R54 DEEP DIVE: Does R54 Rise with Random Seeds?")
    print(f"{'='*78}\n")
    
    r54_data = next(r for r in all_results if r['rule'] == 54)
    r110_data = next(r for r in all_results if r['rule'] == 110)
    
    print("  R54 by seed type:")
    for seed_name, metrics in r54_data['seed_results'].items():
        print(f"    {seed_name:18s}  mem={metrics['memory']:.4f}  trans={metrics['transport']:.4f}  xform={metrics['transformation']:.4f}")
    
    print("\n  R110 by seed type:")
    for seed_name, metrics in r110_data['seed_results'].items():
        print(f"    {seed_name:18s}  mem={metrics['memory']:.4f}  trans={metrics['transport']:.4f}  xform={metrics['transformation']:.4f}")
    
    print(f"\n  R54 overall rank: #{rank_map[54]}")
    print(f"  R110 overall rank: #{rank_map[110]}")
    
    # ─── Save ───
    save_data = {
        'version': 'v4-random-seeds',
        'seed_types': list(SEED_TYPES.keys()),
        'results': [{k: v for k, v in r.items()} for r in all_results],
        'coordinates': {str(r): c for r, c in coords.items()},
        'rankings': [(r, c['combined']) for r, c in ranked[:50]],
        'class_separation': class_avgs,
    }
    
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'random_seeds_v4_results.json')
    with open(out_path, 'w') as f:
        json.dump(save_data, f, indent=2, default=str)
    
    print(f"\n  Results saved to random_seeds_v4_results.json")
    
    # ─── Verdict ───
    print(f"\n{'='*78}")
    print(f"  VERDICT")
    print(f"{'='*78}\n")
    
    r110_rank = rank_map[110]
    r54_rank = rank_map[54]
    r75_rank = rank_map[75]
    r30_rank = rank_map[30]
    
    print(f"  R110 (Turing-complete): #{r110_rank}")
    print(f"  R54 (complex):          #{r54_rank}")
    print(f"  R75 (chaos):            #{r75_rank}")
    print(f"  R30 (chaos):            #{r30_rank}")
    
    if r110_rank < r75_rank and r110_rank < r30_rank:
        print(f"\n  ✅ Computational rules still dominate over chaos with random seeds.")
    else:
        print(f"\n  ⚠️ Random seeds shuffle the rankings — single-seed V4 was partially artifactual.")
    
    if r54_rank < r110_rank:
        print(f"  📊 R54 rises above R110 with richer seeds — the single-seed bias was real.")
    elif abs(r54_rank - r110_rank) < 10:
        print(f"  📊 R54 and R110 are close — both genuinely computational.")
    else:
        print(f"  📊 R110 still dominates R54 — the single-seed story holds.")
    
    return coords, ranked


if __name__ == '__main__':
    coords, ranked = main()
