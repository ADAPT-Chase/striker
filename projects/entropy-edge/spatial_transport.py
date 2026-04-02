#!/usr/bin/env python3
"""
Spatial Transport — Detecting Gliders and Moving Information

Day 009 revealed the gap: R110 clustered with chaotic rules because
metric_space.py only measures temporal MI at *fixed* spatial positions.
It can't see information that MOVES — gliders, particles, signals
propagating across the lattice.

This module adds:
  1. Directional MI — MI between blocks at (x, t) and (x+δ, t+lag)
  2. Transport spectrum — for each lag, the spatial offset δ that maximizes MI
  3. Transport score — how much MI is carried by moving vs stationary structures
  4. Glider persistence — do localized perturbations create structures that travel?

The hypothesis: R110's computation is spatial (glider-based), not temporal
(memory-based). R54 has extraordinary temporal memory but maybe no spatial
transport. If true, the "edge of chaos" might need TWO axes: temporal memory
AND spatial transport.
"""

import math
import random
from collections import Counter

from automata import make_rule, evolve, single_seed, block_entropy


# ─── Core Information Theory (matching metric_space.py conventions) ───

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

def mutual_information(seq_a, seq_b):
    ha = marginal_entropy(seq_a)
    hb = marginal_entropy(seq_b)
    hab = joint_entropy(seq_a, seq_b)
    return max(0.0, ha + hb - hab)


# ─── Directional MI ───

def directional_mi(history, block_size=3, lag=1, offset=0):
    """MI between blocks at position x (time t) and position x+offset (time t+lag).
    
    offset=0, lag=1 → standard temporal MI (stationary information)
    offset=1, lag=1 → rightward information transport at speed 1
    offset=-1, lag=1 → leftward information transport at speed 1
    
    Gliders show up as MI peaks at non-zero offsets.
    """
    mi_values = []
    width = len(history[0])
    max_block_pos = width - block_size + 1
    
    for t in range(len(history) - lag):
        blocks_t = row_to_blocks(history[t], block_size)
        blocks_next = row_to_blocks(history[t + lag], block_size)
        
        # Align with offset — only use positions where both source and target exist
        valid_pairs_a = []
        valid_pairs_b = []
        
        for pos in range(max_block_pos):
            target_pos = pos + offset
            if 0 <= target_pos < len(blocks_next):
                valid_pairs_a.append(blocks_t[pos])
                valid_pairs_b.append(blocks_next[target_pos])
        
        if len(valid_pairs_a) > block_size:  # Need enough data
            mi = mutual_information(valid_pairs_a, valid_pairs_b)
            mi_values.append(mi)
    
    settled = mi_values[len(mi_values)//4:]
    return sum(settled) / len(settled) if settled else 0.0


def transport_spectrum(history, block_size=3, lag=1, max_offset=10):
    """MI as a function of spatial offset for a given temporal lag.
    
    Returns dict: {offset: MI} for offsets in [-max_offset, +max_offset].
    Symmetric rules will have symmetric spectra. Gliders show directional peaks.
    """
    spectrum = {}
    for delta in range(-max_offset, max_offset + 1):
        spectrum[delta] = directional_mi(history, block_size, lag, delta)
    return spectrum


def transport_profile(history, block_size=3, max_lag=5, max_offset=8):
    """Full transport analysis across multiple lags.
    
    Returns:
        - peak_offsets: list of (lag, best_offset, peak_MI, stationary_MI) tuples
        - transport_score: aggregate measure of moving vs stationary information
        - dominant_speed: most common non-zero peak offset across lags
    """
    results = []
    
    for lag in range(1, max_lag + 1):
        spectrum = transport_spectrum(history, block_size, lag, max_offset)
        
        stationary_mi = spectrum.get(0, 0.0)
        
        # Find peak offset (excluding 0)
        best_offset = 0
        best_mi = stationary_mi
        for delta, mi in spectrum.items():
            if delta != 0 and mi > best_mi:
                best_mi = mi
                best_offset = delta
        
        # Also find absolute peak (including 0)
        abs_peak_offset = max(spectrum, key=spectrum.get)
        abs_peak_mi = spectrum[abs_peak_offset]
        
        results.append({
            'lag': lag,
            'stationary_mi': stationary_mi,
            'peak_offset': best_offset,
            'peak_mi': best_mi,
            'abs_peak_offset': abs_peak_offset,
            'abs_peak_mi': abs_peak_mi,
            'spectrum': spectrum,
        })
    
    # Transport score: ratio of moving MI to total MI across all lags
    total_moving = sum(r['peak_mi'] for r in results if r['peak_offset'] != 0)
    total_stationary = sum(r['stationary_mi'] for r in results)
    total_mi = total_moving + total_stationary
    transport_score = total_moving / total_mi if total_mi > 0.01 else 0.0
    
    # Dominant speed: most common non-zero peak offset
    nonzero_offsets = [r['peak_offset'] for r in results if r['peak_offset'] != 0]
    if nonzero_offsets:
        offset_counts = Counter(abs(o) for o in nonzero_offsets)
        dominant_speed = offset_counts.most_common(1)[0][0]
    else:
        dominant_speed = 0
    
    return {
        'lags': results,
        'transport_score': transport_score,
        'dominant_speed': dominant_speed,
    }


# ─── Glider Persistence ───

def perturbation_trail(rule_num, width=121, steps=100):
    """Track how a single-bit perturbation propagates spatially.
    
    Instead of just measuring damage (like perturbation_damage), track WHERE
    the damage goes. Glider rules will show damage that moves at constant speed.
    Non-glider rules will show damage that stays put or spreads diffusely.
    
    Returns:
        - trail: list of (step, center_of_mass_of_damage) tuples
        - speed: estimated speed (cells/step) of damage propagation  
        - coherence: how linear the trail is (R² of center-of-mass trajectory)
    """
    base = single_seed(width)
    perturbed = base[:]
    # Perturb slightly off-center to break symmetry
    perturb_pos = width // 2 + 3
    perturbed[perturb_pos] = 1 - perturbed[perturb_pos]
    
    rule = make_rule(rule_num)
    hist_a = evolve(rule, base, steps)
    hist_b = evolve(rule, perturbed, steps)
    
    trail = []
    for t in range(steps + 1):
        diff = [abs(a - b) for a, b in zip(hist_a[t], hist_b[t])]
        damage_sum = sum(diff)
        
        if damage_sum > 0:
            # Center of mass of damage
            com = sum(i * d for i, d in enumerate(diff)) / damage_sum
            trail.append((t, com, damage_sum))
    
    if len(trail) < 5:
        return {'trail': trail, 'speed': 0.0, 'coherence': 0.0, 'spread': 0.0}
    
    # Fit linear regression to center-of-mass trajectory
    # speed = slope, coherence = R²
    settled_trail = trail[len(trail)//4:]  # Skip transient
    
    if len(settled_trail) < 3:
        settled_trail = trail
    
    ts = [p[0] for p in settled_trail]
    xs = [p[1] for p in settled_trail]
    
    n = len(ts)
    mean_t = sum(ts) / n
    mean_x = sum(xs) / n
    
    cov_tx = sum((ts[i] - mean_t) * (xs[i] - mean_x) for i in range(n)) / n
    var_t = sum((ts[i] - mean_t) ** 2 for i in range(n)) / n
    var_x = sum((xs[i] - mean_x) ** 2 for i in range(n)) / n
    
    speed = cov_tx / var_t if var_t > 1e-10 else 0.0
    
    # R² (coherence)
    if var_t > 1e-10 and var_x > 1e-10:
        r = cov_tx / math.sqrt(var_t * var_x)
        coherence = r * r
    else:
        coherence = 0.0
    
    # Spread: how wide does the damage zone get?
    spreads = []
    for t, com, dmg in settled_trail:
        diff = [abs(a - b) for a, b in zip(hist_a[t], hist_b[t])]
        # Standard deviation of damage positions
        if dmg > 0:
            var_pos = sum((i - com) ** 2 * d for i, d in enumerate(diff)) / dmg
            spreads.append(math.sqrt(var_pos))
    
    avg_spread = sum(spreads) / len(spreads) if spreads else 0.0
    
    return {
        'trail': trail,
        'speed': abs(speed),
        'coherence': coherence,
        'spread': avg_spread,
    }


# ─── Combined Spatial Transport Score ───

def spatial_transport_score(rule_num, width=121, steps=150, block_size=3):
    """Single-number summary of spatial information transport.
    
    Combines:
    - transport_score from directional MI (how much MI is in moving structures)
    - coherence from perturbation trail (how linearly damage propagates)
    - speed from perturbation trail (how fast damage moves)
    
    High score = glider-like behavior (R110 should score high)
    Low score = stationary or diffuse (R54, R30 should score low-medium)
    """
    rule = make_rule(rule_num)
    state = single_seed(width)
    history = evolve(rule, state, steps)
    
    # Directional MI analysis
    tp = transport_profile(history, block_size, max_lag=4, max_offset=6)
    
    # Perturbation trail
    pt = perturbation_trail(rule_num, width, steps)
    
    # Combine into a single score
    # Transport component: is MI moving?
    mi_transport = tp['transport_score']
    
    # Coherence component: is damage propagating linearly? (glider signature)
    coherence = pt['coherence']
    
    # Speed component: is there actual movement? (normalized)
    speed = min(pt['speed'], 2.0) / 2.0  # Cap at speed 2, normalize to [0,1]
    
    # Combined: all three need to be present for a true glider
    # Using geometric-ish mean so all components matter
    score = (mi_transport * 0.4 + coherence * 0.4 + speed * 0.2)
    
    return {
        'rule': rule_num,
        'transport_score': mi_transport,
        'perturbation_coherence': coherence,
        'perturbation_speed': pt['speed'],
        'perturbation_spread': pt['spread'],
        'dominant_speed': tp['dominant_speed'],
        'combined_score': score,
        'transport_profile': tp,
    }


# ─── ASCII Visualization ───

def render_transport_spectrum(spectrum, title=""):
    """ASCII bar chart of MI vs spatial offset."""
    lines = []
    if title:
        lines.append(f"  {title}")
    
    max_mi = max(spectrum.values()) if spectrum else 1.0
    max_mi = max(max_mi, 0.01)
    
    for delta in sorted(spectrum.keys()):
        mi = spectrum[delta]
        bar_len = int(mi / max_mi * 40)
        marker = "█" if delta == 0 else "▓"
        bar = marker * bar_len
        arrow = " ◄── stationary" if delta == 0 else ""
        lines.append(f"  δ={delta:+3d} │ {mi:.3f} {bar}{arrow}")
    
    return "\n".join(lines)


# ─── Main Analysis ───

def main():
    print("=" * 78)
    print("  SPATIAL TRANSPORT — Do Gliders Explain R110?")
    print("  'The metrics saw temporal memory. They were blind to motion.'")
    print("=" * 78)
    print()
    
    # Test on the famous rules first
    famous_rules = [0, 30, 54, 90, 110, 184]
    rule_names = {0: "Dead", 30: "Chaos", 54: "Complex", 90: "XOR fractal", 
                  110: "Turing-complete", 184: "Traffic"}
    
    all_results = []
    
    for rule_num in famous_rules:
        print(f"── Rule {rule_num} ({rule_names.get(rule_num, '')}) ──")
        
        result = spatial_transport_score(rule_num)
        all_results.append(result)
        
        print(f"  Transport score:     {result['transport_score']:.4f}")
        print(f"  Pert. coherence:     {result['perturbation_coherence']:.4f}")
        print(f"  Pert. speed:         {result['perturbation_speed']:.4f} cells/step")
        print(f"  Pert. spread:        {result['perturbation_spread']:.2f} cells")
        print(f"  Dominant MI speed:   {result['dominant_speed']}")
        print(f"  ─── COMBINED: {result['combined_score']:.4f} ───")
        print()
        
        # Show transport spectrum for lag=1
        tp = result['transport_profile']
        if tp['lags']:
            spec = tp['lags'][0]['spectrum']
            print(render_transport_spectrum(spec, f"Lag-1 Transport Spectrum (Rule {rule_num})"))
            print()
    
    # ─── The Comparison Table ───
    print("\n" + "=" * 78)
    print("  COMPARISON TABLE — Temporal Memory vs Spatial Transport")
    print("=" * 78)
    print()
    print(f"  {'Rule':>6s}  {'Name':>16s}  {'Transport':>10s}  {'Coherence':>10s}  {'Speed':>8s}  {'Combined':>9s}")
    print(f"  {'─'*6}  {'─'*16}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*9}")
    
    for r in sorted(all_results, key=lambda x: -x['combined_score']):
        name = rule_names.get(r['rule'], "?")
        print(f"  R{r['rule']:>4d}  {name:>16s}  {r['transport_score']:>10.4f}  "
              f"{r['perturbation_coherence']:>10.4f}  {r['perturbation_speed']:>8.3f}  "
              f"{r['combined_score']:>9.4f}")
    
    print()
    
    # ─── Now scan ALL 256 rules ───
    print("Scanning all 256 rules for spatial transport...")
    print()
    
    all_256 = []
    for rule_num in range(256):
        if rule_num % 32 == 0:
            print(f"  Processing rules {rule_num}-{min(rule_num+31, 255)}...")
        result = spatial_transport_score(rule_num, width=101, steps=120)
        all_256.append(result)
    
    # Top 20 by transport
    print("\n── TOP 20 RULES BY SPATIAL TRANSPORT ──\n")
    top = sorted(all_256, key=lambda x: -x['combined_score'])[:20]
    print(f"  {'Rank':>4s}  {'Rule':>4s}  {'Combined':>9s}  {'Transport':>10s}  {'Coherence':>10s}  {'Speed':>8s}")
    print(f"  {'─'*4}  {'─'*4}  {'─'*9}  {'─'*10}  {'─'*10}  {'─'*8}")
    for i, r in enumerate(top):
        marker = " ◄" if r['rule'] in famous_rules else ""
        print(f"  {i+1:>4d}  R{r['rule']:>3d}  {r['combined_score']:>9.4f}  "
              f"{r['transport_score']:>10.4f}  {r['perturbation_coherence']:>10.4f}  "
              f"{r['perturbation_speed']:>8.3f}{marker}")
    
    # Where do famous rules rank?
    print("\n── FAMOUS RULE RANKINGS ──\n")
    ranked = sorted(all_256, key=lambda x: -x['combined_score'])
    for rule_num in famous_rules:
        rank = next(i+1 for i, r in enumerate(ranked) if r['rule'] == rule_num)
        result = next(r for r in all_256 if r['rule'] == rule_num)
        print(f"  R{rule_num:>3d} ({rule_names.get(rule_num, ''):>16s}): "
              f"rank {rank:>3d}/256, combined={result['combined_score']:.4f}")
    
    # ─── The Key Question ───
    print()
    print("=" * 78)
    print("  THE QUESTION: Does R110 separate from chaotic rules on this axis?")
    print("=" * 78)
    
    # Get R110 and R30 scores
    r110 = next(r for r in all_256 if r['rule'] == 110)
    r30 = next(r for r in all_256 if r['rule'] == 30)
    r54 = next(r for r in all_256 if r['rule'] == 54)
    
    print(f"\n  R110 combined: {r110['combined_score']:.4f}")
    print(f"  R30  combined: {r30['combined_score']:.4f}")
    print(f"  R54  combined: {r54['combined_score']:.4f}")
    
    if r110['combined_score'] > r30['combined_score'] * 1.5:
        print("\n  ✅ YES — R110 shows significantly more spatial transport than R30")
        print("  The temporal-only metrics were wrong to lump them together.")
    elif r110['combined_score'] > r30['combined_score']:
        print("\n  ⚠️  PARTIALLY — R110 shows more transport, but the gap is modest")
    else:
        print("\n  ❌ NO — R110 doesn't show more spatial transport by this measure")
        print("  Either the metric is wrong, or the hypothesis needs revision.")
    
    if r54['combined_score'] < r110['combined_score'] * 0.5:
        print(f"\n  R54's transport ({r54['combined_score']:.4f}) << R110's ({r110['combined_score']:.4f})")
        print("  → R54 is a temporal memory champion, R110 is a spatial transport champion")
        print("  → They're computing differently. The edge has at least two axes.")
    
    # Save results
    import json
    save_data = {
        'famous': {r['rule']: {k: v for k, v in r.items() if k != 'transport_profile'} 
                   for r in all_results},
        'all_256': [{k: v for k, v in r.items() if k != 'transport_profile'} 
                    for r in all_256],
    }
    
    with open('spatial_transport_results.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"\n  Results saved to spatial_transport_results.json")
    
    return all_256


if __name__ == '__main__':
    main()
