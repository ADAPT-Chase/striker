#!/usr/bin/env python3
"""
Translation-Invariant Memory Metric — Fixing the Weak Link

Day 012 diagnosis: the memory metric gives R62 a perfect score for being 
perfectly periodic, while R110 gets penalized because its information travels 
in gliders that move away from their origin.

The fix has two parts:

1. TRANSLATION-INVARIANT MI: Instead of comparing cell i at time t with cell i 
   at time t+lag, we find the BEST spatial alignment. If a glider carries 
   information rightward at speed v, we should track that information by 
   shifting our comparison window by v*lag cells.

2. PERIODICITY PENALTY: Periodic systems remember everything trivially — they 
   just repeat. We penalize memory that was already predictable by weighting 
   with conditional entropy. Memory that REDUCES uncertainty is valuable. 
   Memory that was already certain is not.

The combined metric: translation_invariant_MI × (1 - periodicity_penalty)
"""

import math
from collections import Counter
from automata import make_rule, evolve, single_seed, block_entropy, entropy_sparkline

# ─── Core Information Theory ───

def row_to_blocks(row, k=3):
    return [tuple(row[i:i+k]) for i in range(len(row) - k + 1)]

def marginal_entropy(seq):
    n = len(seq)
    if n == 0:
        return 0.0
    counts = Counter(seq)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h

def joint_entropy(seq_a, seq_b):
    n = len(seq_a)
    if n == 0:
        return 0.0
    pairs = list(zip(seq_a, seq_b))
    counts = Counter(pairs)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h

def mutual_information(seq_a, seq_b):
    ha = marginal_entropy(seq_a)
    hb = marginal_entropy(seq_b)
    hab = joint_entropy(seq_a, seq_b)
    return max(0.0, ha + hb - hab)

def conditional_entropy(seq_future, seq_past):
    """H(future|past) = H(future, past) - H(past)
    
    How much uncertainty remains about the future given the past.
    Low = highly predictable. High = genuinely uncertain.
    """
    hp = marginal_entropy(seq_past)
    hjoint = joint_entropy(seq_future, seq_past)
    return max(0.0, hjoint - hp)


# ─── Part 1: Translation-Invariant MI ───

def shifted_mi(row_a, row_b, shift, block_size=3):
    """MI between blocks of row_a and spatially-shifted blocks of row_b.
    
    Positive shift = row_b is read shifted rightward (tracking rightward-moving info).
    Negative shift = row_b is read shifted leftward.
    Uses circular boundary (matching the CA's periodic boundaries).
    """
    w = len(row_a)
    # Shift row_b circularly
    shifted_b = [row_b[(i + shift) % w] for i in range(w)]
    
    blocks_a = row_to_blocks(row_a, block_size)
    blocks_b = row_to_blocks(shifted_b, block_size)
    
    # Align lengths
    min_len = min(len(blocks_a), len(blocks_b))
    return mutual_information(blocks_a[:min_len], blocks_b[:min_len])


def translation_invariant_mi(row_a, row_b, max_shift=10, block_size=3):
    """Find the spatial shift that maximizes MI between two rows.
    
    This captures information carried by gliders: if a glider moves 
    rightward by 3 cells per timestep, the best shift at lag=1 will be +3.
    
    Returns: (best_mi, best_shift, mi_profile)
    """
    best_mi = 0.0
    best_shift = 0
    mi_profile = {}
    
    for shift in range(-max_shift, max_shift + 1):
        mi = shifted_mi(row_a, row_b, shift, block_size)
        mi_profile[shift] = mi
        if mi > best_mi:
            best_mi = mi
            best_shift = shift
    
    return best_mi, best_shift, mi_profile


def ti_memory_profile(history, block_size=3, max_lag=10, max_shift=15):
    """Translation-invariant memory across multiple lags.
    
    For each lag, finds the spatial shift that maximizes MI.
    Returns the MI-vs-lag curve (the "memory spectrum") using best shifts.
    
    Also returns the detected glider speeds (consistent best shifts across time).
    """
    results = []
    
    for lag in range(1, max_lag + 1):
        mi_values = []
        shifts = []
        
        # Sample timesteps (skip transient first quarter)
        start = len(history) // 4
        for t in range(start, len(history) - lag, 2):  # stride 2 for speed
            best_mi, best_shift, _ = translation_invariant_mi(
                history[t], history[t + lag], 
                max_shift=min(max_shift, lag * 5),  # shift budget grows with lag
                block_size=block_size
            )
            mi_values.append(best_mi)
            shifts.append(best_shift)
        
        if mi_values:
            mean_mi = sum(mi_values) / len(mi_values)
            # Mode of shifts = dominant glider speed at this lag
            shift_counts = Counter(shifts)
            dominant_shift = shift_counts.most_common(1)[0][0]
            shift_diversity = len(shift_counts)
        else:
            mean_mi = 0.0
            dominant_shift = 0
            shift_diversity = 0
        
        results.append({
            'lag': lag,
            'mean_mi': mean_mi,
            'dominant_shift': dominant_shift,
            'shift_diversity': shift_diversity,
            'effective_speed': dominant_shift / lag if lag > 0 else 0,
        })
    
    return results


# ─── Part 2: Periodicity Detection & Penalty ───

def detect_period(history, block_size=3, max_period=20):
    """Detect the dominant temporal period of the spacetime pattern.
    
    Compares row t with row t+p for various p. If the pattern repeats 
    exactly (or nearly) at period p, the normalized Hamming distance will be ~0.
    
    Returns: (period, confidence) where confidence is 1 - min_distance.
    """
    # Use settled portion only
    start = len(history) // 3
    rows = history[start:]
    
    if len(rows) < max_period * 2:
        max_period = len(rows) // 2
    
    period_scores = {}
    
    for p in range(1, max_period + 1):
        distances = []
        for t in range(len(rows) - p):
            w = len(rows[t])
            hamming = sum(rows[t][i] != rows[t+p][i] for i in range(w)) / w
            distances.append(hamming)
        
        if distances:
            mean_dist = sum(distances) / len(distances)
            period_scores[p] = mean_dist
    
    if not period_scores:
        return 0, 0.0
    
    best_period = min(period_scores, key=period_scores.get)
    confidence = 1.0 - period_scores[best_period]
    
    return best_period, confidence


def periodicity_penalty(history, block_size=3):
    """Compute how much of the temporal structure is just periodicity.
    
    Uses conditional entropy: H(t+1 | t, t-1, t-2)
    If this is low, the future is highly predictable from the recent past → periodic.
    If this is high, there's genuine novelty → computation.
    
    Returns a value in [0, 1] where 1 = perfectly periodic (maximum penalty).
    """
    # Multi-step conditional: use blocks from t-2, t-1, t to predict t+1
    start = len(history) // 4
    
    predictabilities = []
    
    for t in range(start + 2, len(history) - 1):
        # Past context: concatenate blocks from t-2, t-1, t
        blocks_past = []
        for dt in [-2, -1, 0]:
            blk = row_to_blocks(history[t + dt], block_size)
            blocks_past.append(blk)
        
        # Combine past context into joint symbols
        min_len = min(len(b) for b in blocks_past)
        combined_past = [
            (blocks_past[0][i], blocks_past[1][i], blocks_past[2][i]) 
            for i in range(min_len)
        ]
        
        # Future: blocks at t+1
        blocks_future = row_to_blocks(history[t + 1], block_size)[:min_len]
        
        # H(future) and H(future|past)
        h_future = marginal_entropy(blocks_future)
        h_cond = conditional_entropy(blocks_future, combined_past)
        
        if h_future > 0.01:
            # Predictability = 1 - H(future|past)/H(future)
            # = fraction of uncertainty eliminated by knowing the past
            pred = 1.0 - (h_cond / h_future)
        else:
            pred = 1.0  # Trivially predictable (dead/uniform)
        
        predictabilities.append(pred)
    
    if not predictabilities:
        return 1.0
    
    return sum(predictabilities) / len(predictabilities)


# ─── Part 3: The Combined Metric ───

def invariant_memory_score(rule_num, width=101, steps=150, block_size=3):
    """The new memory metric: translation-invariant MI with periodicity penalty.
    
    Score = mean_TI_MI × (1 - periodicity_penalty^2)
    
    The squaring of the penalty means:
    - Fully periodic (penalty=1.0): score × 0.0 → dead
    - Mostly periodic (penalty=0.9): score × 0.19 → heavily penalized
    - Somewhat predictable (penalty=0.5): score × 0.75 → mild penalty
    - Genuinely novel (penalty=0.1): score × 0.99 → almost no penalty
    """
    rule = make_rule(rule_num)
    state = single_seed(width)
    history = evolve(rule, state, steps)
    
    # Translation-invariant MI profile
    ti_profile = ti_memory_profile(history, block_size, max_lag=8, max_shift=12)
    
    # Mean TI-MI across lags (weighted toward shorter lags — they're more reliable)
    weights = [1.0 / (lag_data['lag'] ** 0.5) for lag_data in ti_profile]
    total_weight = sum(weights)
    mean_ti_mi = sum(w * d['mean_mi'] for w, d in zip(weights, ti_profile)) / total_weight if total_weight > 0 else 0.0
    
    # Periodicity penalty
    period, period_confidence = detect_period(history, block_size)
    pp = periodicity_penalty(history, block_size)
    
    # Combined score
    novelty_factor = 1.0 - pp ** 2
    score = mean_ti_mi * novelty_factor
    
    # Detected glider speeds
    speeds = set()
    for d in ti_profile:
        if d['mean_mi'] > 0.1:  # Only count meaningful MI
            speeds.add(d['effective_speed'])
    
    # Spatial entropy for context
    blk = [block_entropy(row, block_size) for row in history]
    settled_blk = blk[len(blk)//4:]
    spatial_h = sum(settled_blk) / len(settled_blk) if settled_blk else 0.0
    
    return {
        'rule': rule_num,
        'ti_memory': mean_ti_mi,
        'periodicity_penalty': pp,
        'novelty_factor': novelty_factor,
        'score': score,
        'period': period,
        'period_confidence': period_confidence,
        'spatial_entropy': spatial_h,
        'glider_speeds': sorted(speeds),
        'ti_profile': ti_profile,
    }


# ─── The Big Test ───

def main():
    print("=" * 78)
    print("  TRANSLATION-INVARIANT MEMORY — Fixing the Weak Link")
    print("  'A computer that remembers vs. a tape loop that repeats'")
    print("=" * 78)
    print()
    
    # ─── R62 vs R110 head-to-head ───
    print("── THE CRUCIAL TEST: R62 vs R110 ──\n")
    print("  Old metric gave R62 memory=1.0 (perfect!) and R110 much lower.")
    print("  R62 is periodic. R110 computes. Let's see if the new metric agrees.\n")
    
    r62 = invariant_memory_score(62)
    r110 = invariant_memory_score(110)
    
    print(f"  Rule 62:")
    print(f"    TI-MI (raw):          {r62['ti_memory']:.4f}")
    print(f"    Periodicity penalty:  {r62['periodicity_penalty']:.4f}")
    print(f"    Novelty factor:       {r62['novelty_factor']:.4f}")
    print(f"    SCORE:                {r62['score']:.4f}")
    print(f"    Period:               {r62['period']} (confidence {r62['period_confidence']:.3f})")
    print(f"    Spatial entropy:      {r62['spatial_entropy']:.4f}")
    print()
    print(f"  Rule 110:")
    print(f"    TI-MI (raw):          {r110['ti_memory']:.4f}")
    print(f"    Periodicity penalty:  {r110['periodicity_penalty']:.4f}")
    print(f"    Novelty factor:       {r110['novelty_factor']:.4f}")
    print(f"    SCORE:                {r110['score']:.4f}")
    print(f"    Period:               {r110['period']} (confidence {r110['period_confidence']:.3f})")
    print(f"    Spatial entropy:      {r110['spatial_entropy']:.4f}")
    print()
    
    if r110['score'] > r62['score']:
        ratio = r110['score'] / r62['score'] if r62['score'] > 0 else float('inf')
        print(f"  ✅ R110 BEATS R62 by {ratio:.1f}x — the periodicity penalty works!")
        print(f"     R62's high MI was an illusion: it 'remembers' by repeating.")
        print(f"     R110's information survives because it's being *processed*.")
    else:
        print(f"  ❌ R62 still beats R110 — need more work on the metric")
    
    # ─── Glider speed detection ───
    print(f"\n── DETECTED GLIDER SPEEDS ──\n")
    print(f"  R62 speeds:  {r62['glider_speeds']}")
    print(f"  R110 speeds: {r110['glider_speeds']}")
    
    print(f"\n  R62 lag-by-lag profile:")
    for d in r62['ti_profile']:
        bar = "█" * int(d['mean_mi'] * 20)
        print(f"    lag={d['lag']:2d}  MI={d['mean_mi']:.3f}  shift={d['dominant_shift']:+3d}  speed={d['effective_speed']:+.2f}  {bar}")
    
    print(f"\n  R110 lag-by-lag profile:")
    for d in r110['ti_profile']:
        bar = "█" * int(d['mean_mi'] * 20)
        print(f"    lag={d['lag']:2d}  MI={d['mean_mi']:.3f}  shift={d['dominant_shift']:+3d}  speed={d['effective_speed']:+.2f}  {bar}")
    
    # ─── Full 256-rule scan ───
    print(f"\n── FULL SCAN: All 256 Rules ──\n")
    print(f"  Computing... (this takes a minute)")
    
    all_results = []
    for r in range(256):
        if r % 64 == 0:
            print(f"    Rules {r}-{min(r+63, 255)}...")
        result = invariant_memory_score(r)
        all_results.append(result)
    
    # Sort by new score
    ranked = sorted(all_results, key=lambda x: -x['score'])
    
    print(f"\n── TOP 20 RULES BY INVARIANT MEMORY SCORE ──\n")
    print(f"  {'Rank':>4s}  {'Rule':>4s}  {'Score':>7s}  {'TI-MI':>7s}  {'Period':>7s}  {'Novelty':>8s}  {'Spatial H':>10s}  {'Per':>3s}")
    print(f"  {'─'*4}  {'─'*4}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*8}  {'─'*10}  {'─'*3}")
    
    famous = {0, 30, 54, 62, 90, 110, 184}
    
    for rank, r in enumerate(ranked[:20], 1):
        marker = " ◄" if r['rule'] in famous else ""
        print(f"  {rank:>4d}  R{r['rule']:>3d}  {r['score']:>7.4f}  {r['ti_memory']:>7.4f}  "
              f"{r['periodicity_penalty']:>7.4f}  {r['novelty_factor']:>8.4f}  "
              f"{r['spatial_entropy']:>10.4f}  {r['period']:>3d}{marker}")
    
    # ─── Where do famous rules land? ───
    print(f"\n── FAMOUS RULE RANKINGS (NEW METRIC) ──\n")
    
    famous_names = {
        0: "Dead", 30: "Chaos", 54: "Complex", 62: "Periodic challenger",
        90: "XOR fractal", 110: "Turing-complete", 184: "Traffic"
    }
    
    for rule_num in sorted(famous_names.keys()):
        r = all_results[rule_num]
        rank = next(i+1 for i, x in enumerate(ranked) if x['rule'] == rule_num)
        print(f"  R{rule_num:>3d} ({famous_names[rule_num]:>20s}): "
              f"rank {rank:>3d}/256  score={r['score']:.4f}  "
              f"TI-MI={r['ti_memory']:.3f}  penalty={r['periodicity_penalty']:.3f}  "
              f"period={r['period']}")
    
    # ─── Compare old vs new rankings ───
    print(f"\n── THE PERIODICITY TRAP: Most Penalized Rules ──\n")
    print(f"  Rules with high raw TI-MI but severe periodicity penalty:\n")
    
    # Find rules where penalty > 0.8 and raw MI > 0.5
    trapped = [r for r in all_results if r['periodicity_penalty'] > 0.8 and r['ti_memory'] > 0.5]
    trapped.sort(key=lambda x: -x['ti_memory'])
    
    for r in trapped[:10]:
        print(f"  R{r['rule']:>3d}: TI-MI={r['ti_memory']:.3f} but penalty={r['periodicity_penalty']:.3f} "
              f"→ score={r['score']:.4f} (period={r['period']})")
    
    # ─── Save results ───
    import json
    
    save_data = {
        'all_256': [{
            'rule': r['rule'],
            'invariant_memory_score': r['score'],
            'ti_memory_raw': r['ti_memory'],
            'periodicity_penalty': r['periodicity_penalty'],
            'novelty_factor': r['novelty_factor'],
            'period': r['period'],
            'period_confidence': r['period_confidence'],
            'spatial_entropy': r['spatial_entropy'],
        } for r in all_results],
        'rankings': [(r['rule'], r['score']) for r in ranked[:50]],
    }
    
    with open('memory_invariant_results.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\n  Results saved to memory_invariant_results.json")
    
    # ─── The Verdict ───
    print(f"\n{'='*78}")
    print(f"  THE VERDICT")
    print(f"{'='*78}\n")
    
    r62_rank = next(i+1 for i, x in enumerate(ranked) if x['rule'] == 62)
    r110_rank = next(i+1 for i, x in enumerate(ranked) if x['rule'] == 110)
    
    print(f"  R62:  rank {r62_rank}/256 (was #1 on old metric)")
    print(f"  R110: rank {r110_rank}/256")
    print()
    
    if r110_rank < r62_rank:
        print("  The translation-invariant memory metric with periodicity penalty")
        print("  correctly identifies R110 as having more meaningful memory than R62.")
        print()
        print("  The key insight: memory carried by COMPUTING structures (R110's gliders")
        print("  that collide and produce new patterns) is more valuable than memory")
        print("  carried by REPEATING structures (R62's periodic oscillators).")
        print()
        print("  A tape loop isn't memory. It's just a tape loop.")
    else:
        print("  Hmm — R62 still ranks above R110. The periodicity penalty helps but")
        print("  isn't sufficient. Need to investigate what aspect of R62 survives.")
        print("  Possible next step: explicitly detect and penalize exact-period repetition")
        print("  vs approximate recurrence.")
    
    return all_results, ranked


if __name__ == '__main__':
    all_results, ranked = main()
