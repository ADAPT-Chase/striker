#!/usr/bin/env python3
"""
Transformation — The Third Axis of the Edge of Chaos

Day 010 revealed: transport ≠ computation. R67 moves information perfectly
but processes nothing (conveyor belt). R110 moves AND transforms (logic gate).
We need a metric that captures this difference.

Three measures of information transformation:

1. **Transfer Entropy** — TE(X→Y) = H(Y' | Y) - H(Y' | Y, X)
   How much does knowing source position X reduce uncertainty about 
   target position Y's next state, BEYOND Y's own past?
   High TE = genuine causal information flow (not just copying).

2. **Processing Ratio** — What fraction of the destination's information
   is NOT simply copied from the source?
   processing_ratio = H(dest | source) / H(dest)
   Low = conveyor belt (R67). High = chaos (R30). Medium = computation (R110).

3. **Structured Transformation Score** — The key insight: computation means
   MODERATE processing ratio WITH high transport AND memory. Pure chaos
   has high processing but no memory. Pure transport has no processing.
   The interesting rules have all three.

Together with temporal memory (Day 009) and spatial transport (Day 010),
this completes the 3D map of computational capability in CA rule space.
"""

import math
import json
from collections import Counter

from automata import make_rule, evolve, single_seed, block_entropy


# ─── Core Info Theory (consistent with other modules) ───

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
    assert len(seq_a) == len(seq_b)
    pairs = list(zip(seq_a, seq_b))
    n = len(pairs)
    if n == 0:
        return 0.0
    counts = Counter(pairs)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h

def conditional_entropy(seq_a, seq_b):
    """H(A | B) = H(A, B) - H(B). Uncertainty in A given B."""
    return joint_entropy(seq_a, seq_b) - marginal_entropy(seq_b)

def mutual_information(seq_a, seq_b):
    ha = marginal_entropy(seq_a)
    hb = marginal_entropy(seq_b)
    hab = joint_entropy(seq_a, seq_b)
    return max(0.0, ha + hb - hab)

def triple_joint_entropy(seq_a, seq_b, seq_c):
    """H(A, B, C)"""
    assert len(seq_a) == len(seq_b) == len(seq_c)
    triples = list(zip(seq_a, seq_b, seq_c))
    n = len(triples)
    if n == 0:
        return 0.0
    counts = Counter(triples)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h


# ─── Transfer Entropy ───

def transfer_entropy(history, block_size=3, source_offset=0, lag=1):
    """Transfer Entropy from source position (x + source_offset) to target position (x).
    
    TE(source → target) = H(target' | target_past) - H(target' | target_past, source)
    
    Where:
      target' = block at position x, time t+lag
      target_past = block at position x, time t
      source = block at position x + source_offset, time t
    
    High TE means the source genuinely influences the target beyond what 
    the target's own history predicts. This is CAUSAL information flow.
    """
    width = len(history[0])
    max_pos = width - block_size + 1
    
    te_values = []
    
    for t in range(len(history) - lag):
        blocks_t = row_to_blocks(history[t], block_size)
        blocks_next = row_to_blocks(history[t + lag], block_size)
        
        # Collect aligned triplets: (target_future, target_past, source)
        targets_future = []
        targets_past = []
        sources = []
        
        for pos in range(max_pos):
            source_pos = pos + source_offset
            if 0 <= source_pos < len(blocks_t):
                targets_future.append(blocks_next[pos])
                targets_past.append(blocks_t[pos])
                sources.append(blocks_t[source_pos])
        
        if len(targets_future) < block_size * 2:
            continue
        
        # TE = H(future | past) - H(future | past, source)
        # = H(future, past) - H(past) - [H(future, past, source) - H(past, source)]
        h_fp = joint_entropy(targets_future, targets_past)
        h_p = marginal_entropy(targets_past)
        h_fps = triple_joint_entropy(targets_future, targets_past, sources)
        h_ps = joint_entropy(targets_past, sources)
        
        te = (h_fp - h_p) - (h_fps - h_ps)
        te = max(0.0, te)  # Clamp numerical noise
        te_values.append(te)
    
    # Skip transient
    settled = te_values[len(te_values)//4:]
    return sum(settled) / len(settled) if settled else 0.0


def directional_transfer_entropy(history, block_size=3, lag=1, max_offset=6):
    """Transfer entropy as a function of source offset.
    
    Returns dict: {offset: TE}
    Peaks at non-zero offsets = information being CAUSALLY transferred across space.
    """
    spectrum = {}
    for delta in range(-max_offset, max_offset + 1):
        spectrum[delta] = transfer_entropy(history, block_size, delta, lag)
    return spectrum


# ─── Processing Ratio ───

def processing_ratio(history, block_size=3, offset=0, lag=1):
    """What fraction of the destination's information is NOT copied from the source?
    
    processing_ratio = H(dest | source) / H(dest)
    
    = 0.0: source perfectly predicts destination (conveyor belt)
    = 1.0: source tells you nothing about destination (chaos/independence)
    = moderate: source partially predicts, but destination has new structure (computation)
    """
    width = len(history[0])
    max_pos = width - block_size + 1
    
    ratios = []
    
    for t in range(len(history) - lag):
        blocks_t = row_to_blocks(history[t], block_size)
        blocks_next = row_to_blocks(history[t + lag], block_size)
        
        sources = []
        dests = []
        
        for pos in range(max_pos):
            source_pos = pos + offset
            if 0 <= source_pos < len(blocks_t):
                sources.append(blocks_t[source_pos])
                dests.append(blocks_next[pos])
        
        if len(sources) < block_size * 2:
            continue
        
        h_dest = marginal_entropy(dests)
        if h_dest < 0.01:
            continue  # Skip trivial rows
        
        h_dest_given_source = conditional_entropy(dests, sources)
        ratio = h_dest_given_source / h_dest
        ratios.append(max(0.0, min(1.0, ratio)))
    
    settled = ratios[len(ratios)//4:]
    return sum(settled) / len(settled) if settled else 0.0


# ─── Transformation Spectrum ───

def transformation_spectrum(history, block_size=3, lag=1, max_offset=6):
    """Processing ratio as a function of spatial offset.
    
    For each offset, how much is the destination's info NOT from the source?
    Conveyor belts: low ratio at their transport offset.
    Computers: moderate ratio everywhere.
    Chaos: high ratio everywhere.
    """
    spectrum = {}
    for delta in range(-max_offset, max_offset + 1):
        spectrum[delta] = processing_ratio(history, block_size, delta, lag)
    return spectrum


# ─── The Transformation Score ───

def transformation_score(rule_num, width=121, steps=150, block_size=3):
    """Measure how much a rule TRANSFORMS information during transport.
    
    The key insight: we want to separate three regimes:
    1. Conveyor belts (R67): low transformation, high transport → score LOW
    2. Chaos (R30): high transformation, no memory → score MODERATE  
    3. Computation (R110): moderate transformation WITH preserved structure → score HIGH
    
    Strategy:
    - Compute transfer entropy along dominant transport direction
    - Compute processing ratio along that same direction
    - The "sweet spot" is where TE is high (genuine causal flow) AND
      processing ratio is moderate (not just copying, not just destroying)
    
    Score = TE_peak × (4 × processing_ratio × (1 - processing_ratio))
    The quadratic term peaks at processing_ratio = 0.5 (equal parts 
    preserved and transformed). Conveyor belts (ratio≈0) and chaos
    (ratio≈1) both get penalized.
    """
    rule = make_rule(rule_num)
    state = single_seed(width)
    history = evolve(rule, state, steps)
    
    # Transfer entropy spectrum
    te_spec = directional_transfer_entropy(history, block_size, lag=1, max_offset=6)
    
    # Processing ratio spectrum
    pr_spec = transformation_spectrum(history, block_size, lag=1, max_offset=6)
    
    # Find peak TE (the direction of maximum causal flow)
    peak_offset = max(te_spec, key=te_spec.get)
    peak_te = te_spec[peak_offset]
    
    # Processing ratio at peak TE direction
    pr_at_peak = pr_spec.get(peak_offset, 0.5)
    
    # Also compute mean TE across all directions (omnidirectional processing)
    mean_te = sum(te_spec.values()) / len(te_spec) if te_spec else 0.0
    
    # Mean processing ratio
    mean_pr = sum(pr_spec.values()) / len(pr_spec) if pr_spec else 0.0
    
    # The "computation" score: TE × balance_factor
    # Balance factor = 4 * p * (1-p), peaks at p=0.5
    balance = 4.0 * mean_pr * (1.0 - mean_pr)
    
    # Combined transformation score
    # Uses peak TE (directional information flow) weighted by balance
    combined = peak_te * balance
    
    # Also compute a "raw transformation" score without the balance penalty
    # (useful for understanding what each component contributes)
    raw_transform = peak_te * mean_pr
    
    return {
        'rule': rule_num,
        'peak_te': peak_te,
        'peak_te_offset': peak_offset,
        'mean_te': mean_te,
        'mean_processing_ratio': mean_pr,
        'balance_factor': balance,
        'transformation_score': combined,
        'raw_transformation': raw_transform,
        'te_spectrum': te_spec,
        'pr_spectrum': pr_spec,
    }


# ─── ASCII Visualization ───

def render_te_spectrum(te_spec, pr_spec, title=""):
    """Side-by-side ASCII visualization of TE and processing ratio."""
    lines = []
    if title:
        lines.append(f"  {title}")
    
    max_te = max(te_spec.values()) if te_spec else 0.01
    max_te = max(max_te, 0.01)
    
    lines.append(f"  {'Offset':>8s}  {'TE':>6s}  {'':40s}  {'PR':>5s}")
    
    for delta in sorted(te_spec.keys()):
        te = te_spec[delta]
        pr = pr_spec.get(delta, 0)
        te_bar_len = int(te / max_te * 30)
        pr_bar_len = int(pr * 20)
        te_bar = "█" * te_bar_len
        pr_bar = "░" * pr_bar_len
        lines.append(f"  δ={delta:+3d}    {te:.4f}  {te_bar:30s}  {pr:.3f} {pr_bar}")
    
    return "\n".join(lines)


# ─── Main Analysis ───

def main():
    print("=" * 78)
    print("  TRANSFORMATION — The Third Axis")
    print("  'A conveyor belt is not a factory. Transport is not computation.'")
    print("=" * 78)
    print()
    
    # Key rules to test
    test_rules = {
        0: "Dead",
        30: "Chaos",
        54: "Complex",
        67: "Conveyor belt",
        90: "XOR fractal",
        110: "Turing-complete",
        184: "Traffic",
    }
    
    all_results = {}
    
    for rule_num, name in test_rules.items():
        print(f"── Rule {rule_num} ({name}) ──")
        result = transformation_score(rule_num)
        all_results[rule_num] = result
        
        print(f"  Peak TE:             {result['peak_te']:.4f} (at δ={result['peak_te_offset']:+d})")
        print(f"  Mean TE:             {result['mean_te']:.4f}")
        print(f"  Processing ratio:    {result['mean_processing_ratio']:.4f}")
        print(f"  Balance factor:      {result['balance_factor']:.4f}")
        print(f"  ─── TRANSFORMATION: {result['transformation_score']:.4f} ───")
        print()
        
        print(render_te_spectrum(result['te_spectrum'], result['pr_spectrum'],
                                 f"TE & Processing Ratio (Rule {rule_num})"))
        print()
    
    # ─── Comparison Table ───
    print("\n" + "=" * 78)
    print("  COMPARISON — The Three Axes")
    print("=" * 78)
    print()
    print(f"  {'Rule':>6s}  {'Name':>16s}  {'Peak TE':>8s}  {'Proc. Ratio':>12s}  {'Balance':>8s}  {'Transform':>10s}")
    print(f"  {'─'*6}  {'─'*16}  {'─'*8}  {'─'*12}  {'─'*8}  {'─'*10}")
    
    for rule_num in sorted(all_results.keys()):
        r = all_results[rule_num]
        name = test_rules.get(rule_num, "?")
        print(f"  R{rule_num:>4d}  {name:>16s}  {r['peak_te']:>8.4f}  "
              f"{r['mean_processing_ratio']:>12.4f}  {r['balance_factor']:>8.4f}  "
              f"{r['transformation_score']:>10.4f}")
    
    print()
    
    # ─── Now scan ALL 256 rules ───
    print("Scanning all 256 rules for transformation...")
    print()
    
    all_256 = []
    for rule_num in range(256):
        if rule_num % 32 == 0:
            print(f"  Processing rules {rule_num}-{min(rule_num+31, 255)}...")
        result = transformation_score(rule_num, width=101, steps=120)
        all_256.append(result)
    
    # Top 20
    print("\n── TOP 20 RULES BY TRANSFORMATION SCORE ──\n")
    top = sorted(all_256, key=lambda x: -x['transformation_score'])[:20]
    print(f"  {'Rank':>4s}  {'Rule':>4s}  {'Transform':>10s}  {'Peak TE':>8s}  {'Proc Ratio':>11s}  {'Balance':>8s}")
    print(f"  {'─'*4}  {'─'*4}  {'─'*10}  {'─'*8}  {'─'*11}  {'─'*8}")
    for i, r in enumerate(top):
        marker = " ◄" if r['rule'] in test_rules else ""
        print(f"  {i+1:>4d}  R{r['rule']:>3d}  {r['transformation_score']:>10.4f}  "
              f"{r['peak_te']:>8.4f}  {r['mean_processing_ratio']:>11.4f}  "
              f"{r['balance_factor']:>8.4f}{marker}")
    
    # Famous rule rankings
    print("\n── KEY RULE RANKINGS ──\n")
    ranked = sorted(all_256, key=lambda x: -x['transformation_score'])
    for rule_num in sorted(test_rules.keys()):
        rank = next(i+1 for i, r in enumerate(ranked) if r['rule'] == rule_num)
        result = next(r for r in all_256 if r['rule'] == rule_num)
        print(f"  R{rule_num:>3d} ({test_rules[rule_num]:>16s}): "
              f"rank {rank:>3d}/256, transform={result['transformation_score']:.4f}")
    
    # ─── The Critical Test ───
    print()
    print("=" * 78)
    print("  THE CRITICAL TEST: Does R67 (conveyor) separate from R110 (computer)?")
    print("=" * 78)
    
    r110 = next(r for r in all_256 if r['rule'] == 110)
    r67 = next(r for r in all_256 if r['rule'] == 67)
    r30 = next(r for r in all_256 if r['rule'] == 30)
    r54 = next(r for r in all_256 if r['rule'] == 54)
    
    print(f"\n  R110 (computer):       transform={r110['transformation_score']:.4f}  "
          f"TE={r110['peak_te']:.4f}  PR={r110['mean_processing_ratio']:.4f}")
    print(f"  R67  (conveyor):       transform={r67['transformation_score']:.4f}  "
          f"TE={r67['peak_te']:.4f}  PR={r67['mean_processing_ratio']:.4f}")
    print(f"  R30  (chaos):          transform={r30['transformation_score']:.4f}  "
          f"TE={r30['peak_te']:.4f}  PR={r30['mean_processing_ratio']:.4f}")
    print(f"  R54  (complex):        transform={r54['transformation_score']:.4f}  "
          f"TE={r54['peak_te']:.4f}  PR={r54['mean_processing_ratio']:.4f}")
    
    if r67['transformation_score'] < r110['transformation_score'] * 0.5:
        print(f"\n  ✅ R67's transformation ({r67['transformation_score']:.4f}) << "
              f"R110's ({r110['transformation_score']:.4f})")
        print("  The conveyor belt is exposed. Transport alone isn't computation.")
    
    if r30['transformation_score'] < r110['transformation_score']:
        print(f"\n  ✅ R30 (chaos, {r30['transformation_score']:.4f}) < "
              f"R110 (computer, {r110['transformation_score']:.4f})")
        print("  Chaos destroys too much — the balance factor penalizes it.")
    elif r30['transformation_score'] > r110['transformation_score']:
        print(f"\n  ⚠️ R30 ({r30['transformation_score']:.4f}) > R110 ({r110['transformation_score']:.4f})")
        print("  The balance penalty isn't separating chaos from computation.")
        print("  May need to combine with memory/transport for full picture.")
    
    # Save results
    save_data = {
        'key_rules': {r['rule']: {k: v for k, v in r.items() 
                                   if k not in ('te_spectrum', 'pr_spectrum')}
                      for r in all_256 if r['rule'] in test_rules},
        'all_256': [{k: v for k, v in r.items() 
                     if k not in ('te_spectrum', 'pr_spectrum')}
                    for r in all_256],
    }
    
    with open('transformation_results.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"\n  Results saved to transformation_results.json")
    
    return all_256


if __name__ == '__main__':
    main()
