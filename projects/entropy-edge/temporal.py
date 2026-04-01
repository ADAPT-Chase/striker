#!/usr/bin/env python3
"""
Temporal analysis of cellular automata — measuring computation at the edge.

The key insight: spatial entropy tells you about pattern complexity,
but TEMPORAL mutual information tells you about computation.

- High temporal MI = the future depends on the past in structured ways (computation)
- Low temporal MI + high spatial entropy = chaos (Rule 30)
- Low temporal MI + low spatial entropy = death (Rule 0)
- High temporal MI + high spatial entropy = the edge (Rule 110)

Also introduces Langton's lambda parameter (fraction of "alive" outputs in the rule table)
and tests whether lambda ≈ 0.5 really predicts edge-of-chaos behavior.
"""

import math
from collections import Counter
from automata import make_rule, evolve, single_seed, block_entropy, entropy_sparkline

# ─── Temporal Mutual Information ───

def row_to_blocks(row: list, k: int = 3) -> list:
    """Convert a row to overlapping blocks of size k."""
    return [tuple(row[i:i+k]) for i in range(len(row) - k + 1)]

def joint_entropy(seq_a: list, seq_b: list) -> float:
    """Joint Shannon entropy of two aligned sequences of symbols."""
    assert len(seq_a) == len(seq_b)
    pairs = list(zip(seq_a, seq_b))
    n = len(pairs)
    counts = Counter(pairs)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h

def marginal_entropy(seq: list) -> float:
    """Shannon entropy of a sequence of symbols."""
    n = len(seq)
    counts = Counter(seq)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h

def mutual_information(seq_a: list, seq_b: list) -> float:
    """MI(A;B) = H(A) + H(B) - H(A,B)"""
    ha = marginal_entropy(seq_a)
    hb = marginal_entropy(seq_b)
    hab = joint_entropy(seq_a, seq_b)
    return ha + hb - hab

def temporal_mi_profile(history: list, block_size: int = 3, lag: int = 1) -> dict:
    """Compute mutual information between row t and row t+lag.
    
    Uses block representations so we capture spatial structure too.
    MI(blocks_t, blocks_{t+lag}) tells us: how much does knowing the
    spatial pattern at time t tell us about time t+lag?
    """
    mi_values = []
    for t in range(len(history) - lag):
        blocks_t = row_to_blocks(history[t], block_size)
        blocks_next = row_to_blocks(history[t + lag], block_size)
        mi = mutual_information(blocks_t, blocks_next)
        mi_values.append(mi)
    
    # Skip transient
    settled = mi_values[len(mi_values)//4:]
    
    if not settled:
        return {'mean': 0, 'std': 0, 'trajectory': mi_values}
    
    mean = sum(settled) / len(settled)
    var = sum((v - mean)**2 for v in settled) / len(settled)
    
    return {
        'mean': mean,
        'std': math.sqrt(var),
        'trajectory': mi_values,
    }

# ─── Langton's Lambda ───

def langtons_lambda(rule_number: int) -> float:
    """Lambda = fraction of rule outputs that are 'alive' (1).
    
    For 8-bit rules: lambda = (number of 1-bits) / 8
    Lambda = 0 → all dead. Lambda = 1 → all alive.
    Lambda ≈ 0.5 → edge of chaos (Langton's hypothesis).
    """
    return bin(rule_number).count('1') / 8

# ─── Information Storage vs Transfer ───

def active_information_storage(history: list, block_size: int = 3) -> list:
    """AIS: MI between a cell's past block and its current state.
    
    High AIS = the system "remembers" — information persists.
    This distinguishes gliders (high AIS, information moves) 
    from static patterns (high AIS, information stays put)
    from chaos (low AIS, information destroyed each step).
    """
    ais_per_step = []
    for t in range(1, len(history)):
        # Past: block of k cells centered on position i at time t-1
        # Current: cell i at time t
        past_blocks = row_to_blocks(history[t-1], block_size)
        current_cells = history[t][block_size//2 : len(history[t]) - block_size//2 + 1]
        
        if len(past_blocks) != len(current_cells):
            # Align lengths
            min_len = min(len(past_blocks), len(current_cells))
            past_blocks = past_blocks[:min_len]
            current_cells = current_cells[:min_len]
        
        ais = mutual_information(past_blocks, current_cells)
        ais_per_step.append(ais)
    
    return ais_per_step

# ─── The Full Analysis ───

def analyze_rule(rule_num: int, width: int = 101, steps: int = 150, block_size: int = 3) -> dict:
    """Complete temporal analysis of a single rule."""
    rule = make_rule(rule_num)
    state = single_seed(width)
    history = evolve(rule, state, steps)
    
    # Spatial entropy (from original)
    blk_entropies = [block_entropy(row, block_size) for row in history]
    settled_blk = blk_entropies[len(blk_entropies)//4:]
    blk_mean = sum(settled_blk) / len(settled_blk) if settled_blk else 0
    
    # Temporal MI
    tmi = temporal_mi_profile(history, block_size)
    
    # AIS
    ais_values = active_information_storage(history, block_size)
    settled_ais = ais_values[len(ais_values)//4:]
    ais_mean = sum(settled_ais) / len(settled_ais) if settled_ais else 0
    
    # Lambda
    lam = langtons_lambda(rule_num)
    
    return {
        'rule': rule_num,
        'lambda': lam,
        'spatial_entropy': blk_mean,
        'temporal_mi': tmi['mean'],
        'temporal_mi_std': tmi['std'],
        'ais': ais_mean,
        'tmi_trajectory': tmi['trajectory'],
        'blk_trajectory': blk_entropies,
        'ais_trajectory': ais_values,
    }


def main():
    print("=" * 70)
    print("  TEMPORAL ANALYSIS — Measuring Computation at the Edge")
    print("=" * 70)
    print()
    
    WIDTH = 101
    STEPS = 150
    
    print(f"Analyzing all 256 rules ({WIDTH} cells, {STEPS} steps)...")
    print()
    
    all_results = []
    for r in range(256):
        result = analyze_rule(r, WIDTH, STEPS)
        all_results.append(result)
    
    # ─── Lambda vs Edge Metrics ───
    print("── LANGTON'S LAMBDA vs EDGE METRICS ──\n")
    print("Lambda groups and their average properties:\n")
    print(f"  {'Lambda':>8s}  {'Count':>5s}  {'Spatial H':>10s}  {'Temporal MI':>12s}  {'AIS':>8s}")
    print(f"  {'─'*8}  {'─'*5}  {'─'*10}  {'─'*12}  {'─'*8}")
    
    from collections import defaultdict
    lambda_groups = defaultdict(list)
    for r in all_results:
        lam_bin = round(r['lambda'] * 8) / 8  # bin to nearest 1/8
        lambda_groups[lam_bin].append(r)
    
    for lam in sorted(lambda_groups.keys()):
        group = lambda_groups[lam]
        avg_se = sum(r['spatial_entropy'] for r in group) / len(group)
        avg_tmi = sum(r['temporal_mi'] for r in group) / len(group)
        avg_ais = sum(r['ais'] for r in group) / len(group)
        print(f"  {lam:8.3f}  {len(group):5d}  {avg_se:10.3f}  {avg_tmi:12.3f}  {avg_ais:8.3f}")
    
    # ─── The Computation Score ───
    print("\n── COMPUTATION SCORE ──")
    print("Score = Temporal_MI × Spatial_Entropy × (1 + AIS)")
    print("High score = structured, temporally coherent, remembering → computing\n")
    
    scored = []
    for r in all_results:
        # Skip dead rules
        if r['spatial_entropy'] < 0.05:
            score = 0
        else:
            score = r['temporal_mi'] * r['spatial_entropy'] * (1 + r['ais'])
        scored.append((r['rule'], score, r))
    
    scored.sort(key=lambda x: -x[1])
    
    print(f"  {'Rank':>4s}  {'Rule':>4s}  {'Score':>7s}  {'λ':>5s}  {'Spatial H':>10s}  {'Temp MI':>8s}  {'AIS':>6s}  TMI Sparkline")
    print(f"  {'─'*4}  {'─'*4}  {'─'*7}  {'─'*5}  {'─'*10}  {'─'*8}  {'─'*6}  {'─'*30}")
    
    for rank, (rule_num, score, r) in enumerate(scored[:20], 1):
        spark = entropy_sparkline(r['tmi_trajectory'], 30)
        print(f"  {rank:4d}  {rule_num:4d}  {score:7.3f}  {r['lambda']:5.3f}  {r['spatial_entropy']:10.3f}  {r['temporal_mi']:8.3f}  {r['ais']:6.3f}  {spark}")
    
    # ─── Famous Rules Deep Dive ───
    print("\n── FAMOUS RULES DEEP DIVE ──\n")
    
    famous = {
        30: "Class III — Wolfram's chaos",
        110: "Class IV — Turing-complete",
        90: "Class III — Sierpinski fractal",
        184: "Class II — Traffic model",
        54: "Class III — Complex chaos",
        0: "Class I — Death",
        4: "Class II — Isolated structures",
        232: "Majority voting",
    }
    
    for rule_num, label in famous.items():
        r = all_results[rule_num]
        rank_idx = next(i for i, (rn, _, _) in enumerate(scored) if rn == rule_num) + 1
        
        print(f"  Rule {rule_num:3d} — {label}")
        print(f"    λ={r['lambda']:.3f}  Spatial H={r['spatial_entropy']:.3f}  "
              f"Temporal MI={r['temporal_mi']:.3f}  AIS={r['ais']:.3f}  "
              f"Rank={rank_idx}/256")
        print(f"    TMI: {entropy_sparkline(r['tmi_trajectory'], 40)}")
        print(f"    AIS: {entropy_sparkline(r['ais_trajectory'], 40)}")
        print()
    
    # ─── The Key Finding ───
    print("── KEY FINDING ──\n")
    
    # Check if the top computation scores cluster around lambda ≈ 0.5
    top20_lambdas = [r['lambda'] for _, _, r in scored[:20]]
    avg_lambda_top20 = sum(top20_lambdas) / len(top20_lambdas)
    
    # Where does Rule 110 rank?
    r110_rank = next(i for i, (rn, _, _) in enumerate(scored) if rn == 110) + 1
    r30_rank = next(i for i, (rn, _, _) in enumerate(scored) if rn == 30) + 1
    r90_rank = next(i for i, (rn, _, _) in enumerate(scored) if rn == 90) + 1
    
    print(f"  Average λ of top 20 computation scores: {avg_lambda_top20:.3f}")
    print(f"  (Langton's hypothesis predicts edge at λ ≈ 0.5)")
    print()
    print(f"  Rule 110 (Turing-complete):    computation rank #{r110_rank}")
    print(f"  Rule 30  (chaos/PRNG):          computation rank #{r30_rank}")
    print(f"  Rule 90  (Sierpinski fractal):  computation rank #{r90_rank}")
    print()
    
    # Compare Rule 30 vs 110 — the crucial distinction
    r110 = all_results[110]
    r30 = all_results[30]
    
    print("  Rule 30 vs 110 — the crucial distinction:")
    print(f"    Spatial entropy:  30={r30['spatial_entropy']:.3f}  110={r110['spatial_entropy']:.3f}")
    print(f"    Temporal MI:      30={r30['temporal_mi']:.3f}     110={r110['temporal_mi']:.3f}")
    print(f"    AIS:              30={r30['ais']:.3f}     110={r110['ais']:.3f}")
    print()
    
    if r110['temporal_mi'] > r30['temporal_mi']:
        print("  ✓ Rule 110 has HIGHER temporal MI — it preserves information across time.")
        print("    Rule 30 destroys it. Both are spatially complex, but only 110 *computes*.")
    elif r110['temporal_mi'] < r30['temporal_mi']:
        print("  ✗ Surprise: Rule 30 has higher temporal MI than 110.")
        print("    This challenges the simple narrative. Worth investigating why.")
    else:
        print("  ≈ They're essentially tied on temporal MI. The distinction is subtler.")
    
    if r110['ais'] > r30['ais']:
        print("  ✓ Rule 110 has HIGHER AIS — it stores and carries information (gliders!).")
    elif r110['ais'] < r30['ais']:
        print("  ✗ Rule 30 has higher AIS — interesting, need to think about what this means.")
    
    print()
    print("  The computation score isn't perfect, but it asks the right question:")
    print("  not 'how complex is the pattern?' but 'is the system doing work with")
    print("  information — receiving it, storing it, and producing structured output?'")
    print()
    
    return all_results, scored


if __name__ == '__main__':
    all_results, scored = main()
