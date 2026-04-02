#!/usr/bin/env python3
"""
The Triple Point — Where Memory, Transport, and Transformation Intersect

Day 009: temporal memory (how far back does information reach?)
Day 010: spatial transport (does information move through space?)  
Day 011: transformation (is information processed during transport?)

Hypothesis: R110 lives at the triple point — where all three are 
simultaneously non-trivial. This is what makes it Turing-complete.
Other interesting rules maximize one or two axes but not all three.

This script:
1. Loads data from all three analyses (or recomputes if needed)
2. Normalizes the three axes to [0,1]
3. Computes a "triple point distance" for each rule
4. Tests whether R110 uniquely occupies the triple point
5. Identifies any other rules that come close
"""

import json
import math
import os

# Try to load pre-computed results; fall back to computing
def load_or_compute():
    """Load results from the three analysis modules."""
    
    # We need all three datasets
    results = {}
    
    # 1. Temporal memory — from metric_space or temporal module
    temporal_path = 'metric_space_results.json'
    if os.path.exists(temporal_path):
        with open(temporal_path) as f:
            temporal_data = json.load(f)
        print("  Loaded temporal memory data from metric_space_results.json")
    else:
        temporal_data = None
    
    # 2. Spatial transport — from spatial_transport module
    transport_path = 'spatial_transport_results.json'
    if os.path.exists(transport_path):
        with open(transport_path) as f:
            transport_data = json.load(f)
        print("  Loaded spatial transport data from spatial_transport_results.json")
    else:
        transport_data = None
    
    # 3. Transformation — from transformation module
    transform_path = 'transformation_results.json'
    if os.path.exists(transform_path):
        with open(transform_path) as f:
            transform_data = json.load(f)
        print("  Loaded transformation data from transformation_results.json")
    else:
        transform_data = None
    
    return temporal_data, transport_data, transform_data


def build_unified_map(temporal_data, transport_data, transform_data):
    """Build unified 3D coordinates for all 256 rules."""
    
    rules = {}
    
    # Extract temporal memory scores
    # metric_space_results.json is a flat list of dicts with 'rule', 'temporal_mi', etc.
    if temporal_data:
        entries = temporal_data if isinstance(temporal_data, list) else temporal_data.get('all_256', temporal_data.get('rules', []))
        for entry in entries:
            rule = entry['rule']
            if rule not in rules:
                rules[rule] = {}
            # Use memory_horizon (lag half-life) as the memory score — 
            # it's the best single measure of how far back information reaches
            rules[rule]['memory'] = entry.get('memory_horizon',
                                              entry.get('temporal_mi', 0.0))
    
    # Extract spatial transport scores
    if transport_data:
        entries = transport_data.get('all_256', []) if isinstance(transport_data, dict) else transport_data
        for entry in entries:
            rule = entry['rule']
            if rule not in rules:
                rules[rule] = {}
            rules[rule]['transport'] = entry.get('combined_score', 0.0)
    
    # Extract transformation scores
    if transform_data:
        entries = transform_data.get('all_256', []) if isinstance(transform_data, dict) else transform_data
        for entry in entries:
            rule = entry['rule']
            if rule not in rules:
                rules[rule] = {}
            rules[rule]['transformation'] = entry.get('transformation_score', 0.0)
    
    return rules


def normalize_axis(values):
    """Normalize to [0, 1] range using min-max scaling."""
    if not values:
        return values
    mn = min(values)
    mx = max(values)
    rng = mx - mn
    if rng < 1e-10:
        return [0.5] * len(values)
    return [(v - mn) / rng for v in values]


def compute_triple_score(m, t, x):
    """How close is this rule to the triple point (1,1,1)?
    
    Uses geometric mean — all three axes must be non-trivial.
    Geometric mean is 0 if ANY axis is 0, and 1 only if ALL are 1.
    This is exactly what we want: the triple point is where all three
    capabilities coexist.
    """
    # Add small epsilon to avoid zero-kills in geometric mean
    eps = 0.01
    return (max(m, eps) * max(t, eps) * max(x, eps)) ** (1/3)


def compute_balance_score(m, t, x):
    """How balanced are the three capabilities?
    
    A rule that's high on all three is more interesting than one
    that's extreme on one axis. Measures how "spherical" the point is.
    
    Balance = 1 - coefficient_of_variation(m, t, x)
    """
    mean = (m + t + x) / 3
    if mean < 0.01:
        return 0.0
    var = ((m - mean)**2 + (t - mean)**2 + (x - mean)**2) / 3
    cv = math.sqrt(var) / mean
    return max(0.0, 1.0 - cv)


def main():
    print("=" * 78)
    print("  THE TRIPLE POINT")
    print("  Where Memory, Transport, and Transformation Intersect")
    print("=" * 78)
    print()
    
    # Load data
    temporal_data, transport_data, transform_data = load_or_compute()
    
    if not all([temporal_data, transport_data, transform_data]):
        missing = []
        if not temporal_data:
            missing.append("metric_space_results.json (run metric_space.py)")
        if not transport_data:
            missing.append("spatial_transport_results.json (run spatial_transport.py)")
        if not transform_data:
            missing.append("transformation_results.json (run transformation.py)")
        print(f"\n  ⚠️ Missing data files:")
        for m in missing:
            print(f"    - {m}")
        print("\n  Computing missing data inline...")
        
        # Compute whatever's missing
        if not temporal_data:
            print("\n  Running temporal analysis...")
            from temporal import analyze_rule
            temporal_results = []
            for r in range(256):
                if r % 64 == 0:
                    print(f"    Rules {r}-{min(r+63, 255)}...")
                result = analyze_rule(r, width=101, steps=120)
                temporal_results.append({
                    'rule': r,
                    'temporal_mi_mean': result['temporal_mi'],
                })
            temporal_data = {'all_256': temporal_results}
        
        if not transport_data:
            print("\n  Running spatial transport analysis...")
            from spatial_transport import spatial_transport_score
            transport_results = []
            for r in range(256):
                if r % 64 == 0:
                    print(f"    Rules {r}-{min(r+63, 255)}...")
                result = spatial_transport_score(r, width=101, steps=120)
                transport_results.append({
                    'rule': r,
                    'combined_score': result['combined_score'],
                })
            transport_data = {'all_256': transport_results}
        
        if not transform_data:
            print("\n  Running transformation analysis...")
            from transformation import transformation_score
            transform_results = []
            for r in range(256):
                if r % 64 == 0:
                    print(f"    Rules {r}-{min(r+63, 255)}...")
                result = transformation_score(r, width=101, steps=120)
                transform_results.append({
                    'rule': r,
                    'transformation_score': result['transformation_score'],
                })
            transform_data = {'all_256': transform_results}
    
    # Build unified map
    rules = build_unified_map(temporal_data, transport_data, transform_data)
    
    # Check coverage
    complete_rules = [r for r, v in rules.items() 
                      if 'memory' in v and 'transport' in v and 'transformation' in v]
    print(f"\n  Rules with all 3 axes: {len(complete_rules)}/256")
    
    if len(complete_rules) < 200:
        print("  ⚠️ Insufficient coverage — some axes may be missing data")
        print(f"  Memory: {sum(1 for v in rules.values() if 'memory' in v)}")
        print(f"  Transport: {sum(1 for v in rules.values() if 'transport' in v)}")
        print(f"  Transform: {sum(1 for v in rules.values() if 'transformation' in v)}")
    
    # Extract raw values for normalization
    memory_raw = {r: v.get('memory', 0) for r, v in rules.items() if r in complete_rules}
    transport_raw = {r: v.get('transport', 0) for r, v in rules.items() if r in complete_rules}
    transform_raw = {r: v.get('transformation', 0) for r, v in rules.items() if r in complete_rules}
    
    # Normalize each axis to [0, 1]
    rule_ids = sorted(complete_rules)
    mem_vals = [memory_raw[r] for r in rule_ids]
    trans_vals = [transport_raw[r] for r in rule_ids]
    xform_vals = [transform_raw[r] for r in rule_ids]
    
    mem_norm = normalize_axis(mem_vals)
    trans_norm = normalize_axis(trans_vals)
    xform_norm = normalize_axis(xform_vals)
    
    # Build normalized coordinates
    coords = {}
    for i, r in enumerate(rule_ids):
        coords[r] = {
            'memory': mem_norm[i],
            'transport': trans_norm[i],
            'transformation': xform_norm[i],
            'memory_raw': mem_vals[i],
            'transport_raw': trans_vals[i],
            'transformation_raw': xform_vals[i],
        }
        coords[r]['triple_score'] = compute_triple_score(
            mem_norm[i], trans_norm[i], xform_norm[i])
        coords[r]['balance'] = compute_balance_score(
            mem_norm[i], trans_norm[i], xform_norm[i])
        # Combined: geometric mean × balance bonus
        coords[r]['combined'] = coords[r]['triple_score'] * (0.7 + 0.3 * coords[r]['balance'])
    
    # ─── Results ───
    
    # Famous rules
    famous = {
        0: "Dead", 30: "Chaos", 54: "Complex", 67: "Conveyor",
        90: "XOR fractal", 110: "Turing-complete", 184: "Traffic"
    }
    
    print("\n" + "=" * 78)
    print("  THE 3D MAP — Normalized Coordinates")
    print("=" * 78)
    print()
    print(f"  {'Rule':>6s}  {'Name':>16s}  {'Memory':>7s}  {'Transport':>10s}  {'Transform':>10s}  {'Triple':>7s}  {'Balance':>8s}  {'Combined':>9s}")
    print(f"  {'─'*6}  {'─'*16}  {'─'*7}  {'─'*10}  {'─'*10}  {'─'*7}  {'─'*8}  {'─'*9}")
    
    for rule_num in sorted(famous.keys()):
        if rule_num in coords:
            c = coords[rule_num]
            name = famous[rule_num]
            print(f"  R{rule_num:>4d}  {name:>16s}  {c['memory']:>7.3f}  {c['transport']:>10.3f}  "
                  f"{c['transformation']:>10.3f}  {c['triple_score']:>7.3f}  "
                  f"{c['balance']:>8.3f}  {c['combined']:>9.3f}")
    
    # ─── Top 20 by triple score ───
    print("\n── TOP 20 RULES BY TRIPLE POINT SCORE ──")
    print("(Geometric mean of normalized Memory × Transport × Transformation)\n")
    
    ranked = sorted(coords.items(), key=lambda x: -x[1]['combined'])
    
    print(f"  {'Rank':>4s}  {'Rule':>4s}  {'Combined':>9s}  {'Triple':>7s}  {'Balance':>8s}  {'M':>5s}  {'T':>5s}  {'X':>5s}")
    print(f"  {'─'*4}  {'─'*4}  {'─'*9}  {'─'*7}  {'─'*8}  {'─'*5}  {'─'*5}  {'─'*5}")
    
    for rank, (rule_num, c) in enumerate(ranked[:20], 1):
        marker = f" ◄ {famous[rule_num]}" if rule_num in famous else ""
        print(f"  {rank:>4d}  R{rule_num:>3d}  {c['combined']:>9.4f}  {c['triple_score']:>7.4f}  "
              f"{c['balance']:>8.4f}  {c['memory']:>.3f}  {c['transport']:>.3f}  "
              f"{c['transformation']:>.3f}{marker}")
    
    # ─── Where does R110 rank? ───
    print("\n── FAMOUS RULE RANKINGS ──\n")
    for rule_num in sorted(famous.keys()):
        if rule_num in coords:
            rank = next(i+1 for i, (r, _) in enumerate(ranked) if r == rule_num)
            c = coords[rule_num]
            print(f"  R{rule_num:>3d} ({famous[rule_num]:>16s}): "
                  f"rank {rank:>3d}/{len(ranked)}, combined={c['combined']:.4f}")
    
    # ─── The Triple Point Analysis ───
    print("\n" + "=" * 78)
    print("  THE TRIPLE POINT ANALYSIS")
    print("=" * 78)
    
    if 110 in coords:
        r110 = coords[110]
        r110_rank = next(i+1 for i, (r, _) in enumerate(ranked) if r == 110)
        
        print(f"\n  R110 coordinates: M={r110['memory']:.3f}  T={r110['transport']:.3f}  "
              f"X={r110['transformation']:.3f}")
        print(f"  R110 triple score: {r110['triple_score']:.4f} (rank {r110_rank}/{len(ranked)})")
        print(f"  R110 balance: {r110['balance']:.4f}")
        
        # How many rules are within 90% of R110's triple score?
        threshold = r110['combined'] * 0.9
        nearby = [(r, c) for r, c in ranked if c['combined'] >= threshold]
        print(f"\n  Rules within 90% of R110's combined score: {len(nearby)}")
        for r, c in nearby:
            name = famous.get(r, f"Rule {r}")
            print(f"    R{r:>3d} ({name}): combined={c['combined']:.4f}  "
                  f"M={c['memory']:.3f} T={c['transport']:.3f} X={c['transformation']:.3f}")
    
    # ─── Key comparisons ───
    print("\n── KEY COMPARISONS ──\n")
    
    comparisons = [
        (110, 67, "R110 vs R67: Computer vs Conveyor Belt"),
        (110, 30, "R110 vs R30: Computer vs Chaos"),
        (110, 54, "R110 vs R54: Computer vs Memory Champion"),
        (30, 54, "R30 vs R54: Chaos vs Complex"),
    ]
    
    for a, b, label in comparisons:
        if a in coords and b in coords:
            ca, cb = coords[a], coords[b]
            print(f"  {label}")
            dist = math.sqrt((ca['memory'] - cb['memory'])**2 + 
                           (ca['transport'] - cb['transport'])**2 + 
                           (ca['transformation'] - cb['transformation'])**2)
            print(f"    R{a}: M={ca['memory']:.3f} T={ca['transport']:.3f} X={ca['transformation']:.3f} → combined={ca['combined']:.4f}")
            print(f"    R{b}: M={cb['memory']:.3f} T={cb['transport']:.3f} X={cb['transformation']:.3f} → combined={cb['combined']:.4f}")
            print(f"    3D distance: {dist:.3f}")
            
            # What axis separates them most?
            diffs = {
                'memory': abs(ca['memory'] - cb['memory']),
                'transport': abs(ca['transport'] - cb['transport']),
                'transformation': abs(ca['transformation'] - cb['transformation']),
            }
            biggest = max(diffs, key=diffs.get)
            print(f"    Biggest separation axis: {biggest} (Δ={diffs[biggest]:.3f})")
            print()
    
    # ─── The ASCII 3D Plot (projection) ───
    print("── MEMORY vs TRANSFORMATION (Transport as marker size) ──\n")
    
    # 2D scatter: memory (x) vs transformation (y), transport as symbol
    PLOT_W, PLOT_H = 60, 25
    grid = [[' ' for _ in range(PLOT_W)] for _ in range(PLOT_H)]
    
    # Place rules
    for rule_num, c in coords.items():
        x = int(c['memory'] * (PLOT_W - 1))
        y = PLOT_H - 1 - int(c['transformation'] * (PLOT_H - 1))
        x = max(0, min(PLOT_W - 1, x))
        y = max(0, min(PLOT_H - 1, y))
        
        if rule_num in famous:
            grid[y][x] = str(rule_num)[-1]  # Last digit for famous rules
        elif grid[y][x] == ' ':
            if c['transport'] > 0.5:
                grid[y][x] = '●'
            elif c['transport'] > 0.2:
                grid[y][x] = '·'
            else:
                grid[y][x] = '.'
    
    # Render
    print("  Transform ↑")
    for row in grid:
        print("  │" + ''.join(row))
    print("  └" + "─" * PLOT_W + "→ Memory")
    print()
    print("  Legend: 0=R0, 0=R30, 4=R54, 7=R67, 0=R90, 0=R110, 4=R184")
    print("          ● = high transport, · = medium, . = low")
    
    # ─── The Verdict ───
    print("\n" + "=" * 78)
    print("  THE VERDICT")
    print("=" * 78)
    
    if 110 in coords and 67 in coords and 30 in coords:
        r110 = coords[110]
        r67 = coords[67]
        r30 = coords[30]
        
        # Does R110 beat R67 on transformation while keeping transport?
        if (r110['transformation'] > r67['transformation'] * 2 and 
            r110['transport'] > 0.3):
            print("\n  ✅ R110 SEPARATES FROM R67 (conveyor belt)")
            print(f"     R110 transforms (X={r110['transformation']:.3f}) while transporting (T={r110['transport']:.3f})")
            print(f"     R67 transports (T={r67['transport']:.3f}) without transforming (X={r67['transformation']:.3f})")
        
        # Does R110 beat R30 by having memory that R30 lacks?
        if r110['memory'] > r30['memory']:
            print("\n  ✅ R110 SEPARATES FROM R30 (chaos)")
            print(f"     R110 remembers (M={r110['memory']:.3f}) while R30 forgets (M={r30['memory']:.3f})")
            print(f"     Both transform, but only R110 preserves structure through time")
        elif r30['memory'] > r110['memory']:
            print(f"\n  ⚠️ R30 has MORE memory than R110 ({r30['memory']:.3f} vs {r110['memory']:.3f})")
            print("     The temporal MI metric may not capture the right kind of memory")
        
        # Is R110 at the triple point?
        if (r110['memory'] > 0.3 and r110['transport'] > 0.3 and 
            r110['transformation'] > 0.3):
            print("\n  ✅ R110 IS AT THE TRIPLE POINT")
            print("     All three capabilities are simultaneously non-trivial:")
            print(f"     Memory={r110['memory']:.3f}  Transport={r110['transport']:.3f}  "
                  f"Transformation={r110['transformation']:.3f}")
            print("     This is what Turing-completeness looks like in information space:")
            print("     the ability to store, move, AND process information all at once.")
        else:
            low_axes = []
            if r110['memory'] <= 0.3: low_axes.append(f"Memory ({r110['memory']:.3f})")
            if r110['transport'] <= 0.3: low_axes.append(f"Transport ({r110['transport']:.3f})")
            if r110['transformation'] <= 0.3: low_axes.append(f"Transform ({r110['transformation']:.3f})")
            print(f"\n  ⚠️ R110's weak axes: {', '.join(low_axes)}")
            print("     Not cleanly at the triple point — the map may need refinement")
    
    # Save unified results
    save_data = {
        'coordinates': {str(r): c for r, c in coords.items()},
        'rankings': [(r, c['combined']) for r, c in ranked[:50]],
    }
    with open('triple_point_results.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"\n  Results saved to triple_point_results.json")
    
    return coords, ranked


if __name__ == '__main__':
    coords, ranked = main()
