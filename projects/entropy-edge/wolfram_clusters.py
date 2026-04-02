#!/usr/bin/env python3
"""
Wolfram Class Mapping — Do the 4 classes emerge from the 3D triple-point space?

Wolfram's classification:
  Class I:   Fixed point (dies to uniform state)
  Class II:  Periodic (oscillators, simple patterns)
  Class III: Chaotic (random-looking, high entropy)
  Class IV:  Complex (edge of chaos, gliders, computation)

If our 3-axis metric space (memory × transport × transformation) is capturing
something real, these classes should form distinct clusters.

This script:
1. Classifies all 256 rules using automated heuristics
2. Maps them into the triple-point coordinates
3. Tests whether the classes form separable regions
4. Finds the boundaries and transition zones
"""

import json
import math
from collections import Counter
from automata import make_rule, evolve, single_seed, row_entropy, block_entropy


def auto_classify(rule_num, width=101, steps=200):
    """Automatically classify a rule into Wolfram's 4 classes.
    
    Uses multiple signals:
    - Final state entropy (low = Class I/II, high = Class III)
    - Temporal variability (std of row entropy over time)
    - Cycle detection (periodic = Class II)
    - Block entropy progression
    """
    rule = make_rule(rule_num)
    state = single_seed(width)
    history = evolve(rule, state, steps)
    
    # Entropy measurements on settled behavior
    settled = history[steps//2:]
    row_ents = [row_entropy(r) for r in settled]
    blk_ents = [block_entropy(r) for r in settled]
    
    mean_row = sum(row_ents) / len(row_ents) if row_ents else 0
    std_row = (sum((e - mean_row)**2 for e in row_ents) / len(row_ents))**0.5 if row_ents else 0
    mean_blk = sum(blk_ents) / len(blk_ents) if blk_ents else 0
    std_blk = (sum((e - mean_blk)**2 for e in blk_ents) / len(blk_ents))**0.5 if blk_ents else 0
    
    # Cycle detection: check if the final state repeats
    final_states = [tuple(r) for r in settled[-50:]]
    unique_states = len(set(final_states))
    
    # Density of final state
    final_density = sum(history[-1]) / len(history[-1])
    
    # Classification logic
    if mean_row < 0.05:
        # Very low entropy — either dead (Class I) or all-ones
        wolfram_class = 1
    elif unique_states <= 10 and std_row < 0.01:
        # Low variability, few unique states — periodic
        wolfram_class = 2
    elif mean_blk > 2.5 and std_blk < 0.05:
        # High entropy, low variability — chaotic
        wolfram_class = 3
    elif mean_blk > 1.0 and std_blk > 0.01:
        # Moderate entropy with variability — complex
        wolfram_class = 4
    elif mean_blk > 2.0 and std_blk < 0.1:
        # High entropy, some variation — likely chaotic
        wolfram_class = 3
    elif unique_states <= 20:
        wolfram_class = 2
    else:
        # Default: if entropy is moderate, call it complex
        if mean_blk > 1.5:
            wolfram_class = 3
        else:
            wolfram_class = 2
    
    return {
        'rule': rule_num,
        'class': wolfram_class,
        'mean_row_entropy': mean_row,
        'std_row_entropy': std_row,
        'mean_block_entropy': mean_blk,
        'std_block_entropy': std_blk,
        'unique_states_50': unique_states,
        'final_density': final_density,
    }


def main():
    print("=" * 78)
    print("  WOLFRAM CLASS MAPPING")
    print("  Do the 4 classes emerge in the triple-point space?")
    print("=" * 78)
    
    # ─── Step 1: Classify all 256 rules ───
    print("\n  Classifying all 256 rules...")
    classifications = {}
    for r in range(256):
        classifications[r] = auto_classify(r)
    
    class_counts = Counter(c['class'] for c in classifications.values())
    print(f"\n  Class distribution:")
    for cls in [1, 2, 3, 4]:
        rules = [r for r, c in classifications.items() if c['class'] == cls]
        print(f"    Class {cls}: {len(rules)} rules")
        if len(rules) <= 15:
            print(f"            {rules}")
    
    # Verify against known rules
    known = {
        0: 1, 8: 1, 32: 1, 128: 1, 255: 1,   # Class I: uniform
        4: 2, 50: 2, 108: 2, 184: 2, 232: 2,   # Class II: periodic
        30: 3, 45: 3, 60: 3, 90: 3, 150: 3,    # Class III: chaotic
        54: 3, 73: 3, 22: 3, 146: 3,
        110: 4, 124: 4, 137: 4, 193: 4,         # Class IV: complex
    }
    
    correct = 0
    total = 0
    mismatches = []
    for r, expected in known.items():
        actual = classifications[r]['class']
        total += 1
        if actual == expected:
            correct += 1
        else:
            mismatches.append((r, expected, actual))
    
    print(f"\n  Accuracy on known rules: {correct}/{total} ({100*correct/total:.0f}%)")
    if mismatches:
        print(f"  Mismatches:")
        for r, exp, act in mismatches:
            print(f"    R{r}: expected Class {exp}, got Class {act}")
    
    # ─── Step 2: Load triple-point coordinates ───
    print("\n  Loading triple-point coordinates...")
    try:
        with open('triple_point_results.json') as f:
            tp_data = json.load(f)
        coords = {int(k): v for k, v in tp_data['coordinates'].items()}
        print(f"  Loaded coordinates for {len(coords)} rules")
    except FileNotFoundError:
        print("  ⚠️ triple_point_results.json not found — run triple_point.py first")
        return
    
    # ─── Step 3: Map classes to 3D coordinates ───
    print("\n" + "=" * 78)
    print("  CLASS CENTROIDS IN 3D SPACE")
    print("=" * 78)
    
    class_coords = {1: [], 2: [], 3: [], 4: []}
    class_names = {1: "Fixed", 2: "Periodic", 3: "Chaotic", 4: "Complex"}
    
    for r, cls_info in classifications.items():
        if r in coords:
            cls = cls_info['class']
            class_coords[cls].append({
                'rule': r,
                'memory': coords[r]['memory'],
                'transport': coords[r]['transport'],
                'transformation': coords[r]['transformation'],
            })
    
    print(f"\n  {'Class':>12s}  {'N':>4s}  {'Memory':>8s}  {'Transport':>10s}  {'Transform':>10s}  {'Spread':>8s}")
    print(f"  {'─'*12}  {'─'*4}  {'─'*8}  {'─'*10}  {'─'*10}  {'─'*8}")
    
    centroids = {}
    for cls in [1, 2, 3, 4]:
        pts = class_coords[cls]
        if not pts:
            continue
        n = len(pts)
        avg_m = sum(p['memory'] for p in pts) / n
        avg_t = sum(p['transport'] for p in pts) / n
        avg_x = sum(p['transformation'] for p in pts) / n
        
        # Spread: average distance from centroid
        spread = sum(
            math.sqrt((p['memory']-avg_m)**2 + (p['transport']-avg_t)**2 + (p['transformation']-avg_x)**2)
            for p in pts
        ) / n
        
        centroids[cls] = (avg_m, avg_t, avg_x)
        print(f"  {class_names[cls]:>12s}  {n:>4d}  {avg_m:>8.3f}  {avg_t:>10.3f}  {avg_x:>10.3f}  {spread:>8.3f}")
    
    # ─── Step 4: Inter-class distances ───
    print("\n── INTER-CLASS DISTANCES ──\n")
    
    for i in [1, 2, 3, 4]:
        for j in range(i+1, 5):
            if i in centroids and j in centroids:
                ci, cj = centroids[i], centroids[j]
                dist = math.sqrt(sum((a-b)**2 for a, b in zip(ci, cj)))
                print(f"  {class_names[i]:>8s} ↔ {class_names[j]:<8s}: {dist:.3f}")
    
    # ─── Step 5: Which axis separates which classes? ───
    print("\n── AXIS SEPARATION POWER ──")
    print("(Which axis best separates each pair of classes?)\n")
    
    axes = ['memory', 'transport', 'transformation']
    
    for i in [1, 2, 3, 4]:
        for j in range(i+1, 5):
            if not class_coords[i] or not class_coords[j]:
                continue
            
            best_axis = None
            best_sep = 0
            
            for axis in axes:
                vals_i = [p[axis] for p in class_coords[i]]
                vals_j = [p[axis] for p in class_coords[j]]
                
                mean_i = sum(vals_i) / len(vals_i)
                mean_j = sum(vals_j) / len(vals_j)
                
                std_i = (sum((v - mean_i)**2 for v in vals_i) / len(vals_i))**0.5 + 0.01
                std_j = (sum((v - mean_j)**2 for v in vals_j) / len(vals_j))**0.5 + 0.01
                
                # Fisher's discriminant ratio
                sep = abs(mean_i - mean_j) / ((std_i + std_j) / 2)
                
                if sep > best_sep:
                    best_sep = sep
                    best_axis = axis
            
            print(f"  {class_names[i]:>8s} vs {class_names[j]:<8s}: best axis = {best_axis:<16s} (Fisher ratio = {best_sep:.3f})")
    
    # ─── Step 6: The Class IV neighborhood ───
    print("\n" + "=" * 78)
    print("  THE CLASS IV NEIGHBORHOOD")
    print("  Where does computational capability live?")
    print("=" * 78)
    
    class_iv = class_coords.get(4, [])
    if class_iv:
        print(f"\n  Class IV rules ({len(class_iv)}):\n")
        
        # Sort by triple score
        for p in sorted(class_iv, key=lambda x: -(x['memory'] * x['transport'] * x['transformation'])**(1/3)):
            r = p['rule']
            geo = (max(p['memory'], 0.01) * max(p['transport'], 0.01) * max(p['transformation'], 0.01))**(1/3)
            print(f"    R{r:>3d}: M={p['memory']:.3f}  T={p['transport']:.3f}  "
                  f"X={p['transformation']:.3f}  geo_mean={geo:.3f}")
    
    # ─── Step 7: Transition zone rules ───
    print("\n── TRANSITION ZONE: Rules near class boundaries ──\n")
    
    # Find rules that are close to multiple class centroids
    transition_rules = []
    for r, cls_info in classifications.items():
        if r not in coords:
            continue
        
        c = coords[r]
        pt = (c['memory'], c['transport'], c['transformation'])
        
        # Distance to each class centroid
        dists = {}
        for cls, cent in centroids.items():
            dists[cls] = math.sqrt(sum((a-b)**2 for a, b in zip(pt, cent)))
        
        # Find the two closest classes
        sorted_dists = sorted(dists.items(), key=lambda x: x[1])
        nearest = sorted_dists[0]
        second = sorted_dists[1]
        
        # If the two closest are similar distance, it's in the transition zone
        if nearest[1] > 0 and second[1] / (nearest[1] + 0.001) < 1.3:
            transition_rules.append({
                'rule': r,
                'assigned_class': cls_info['class'],
                'nearest': nearest,
                'second': second,
                'ambiguity': 1 - (second[1] - nearest[1]) / (second[1] + 0.001),
            })
    
    transition_rules.sort(key=lambda x: -x['ambiguity'])
    
    print(f"  Found {len(transition_rules)} rules in transition zones\n")
    for tr in transition_rules[:15]:
        r = tr['rule']
        assigned = class_names[tr['assigned_class']]
        n1 = class_names[tr['nearest'][0]]
        n2 = class_names[tr['second'][0]]
        print(f"    R{r:>3d}: assigned={assigned:>8s}  "
              f"nearest={n1:>8s} ({tr['nearest'][1]:.3f})  "
              f"2nd={n2:>8s} ({tr['second'][1]:.3f})  "
              f"ambiguity={tr['ambiguity']:.3f}")
    
    # ─── Step 8: The 2D projections ───
    print("\n── MEMORY vs TRANSFORMATION (by class) ──\n")
    
    PLOT_W, PLOT_H = 65, 28
    grid = [[' ' for _ in range(PLOT_W)] for _ in range(PLOT_H)]
    
    class_chars = {1: '·', 2: '○', 3: '×', 4: '★'}
    
    for r, cls_info in classifications.items():
        if r not in coords:
            continue
        c = coords[r]
        cls = cls_info['class']
        
        x = int(c['memory'] * (PLOT_W - 1))
        y = PLOT_H - 1 - int(c['transformation'] * (PLOT_H - 1))
        x = max(0, min(PLOT_W - 1, x))
        y = max(0, min(PLOT_H - 1, y))
        
        grid[y][x] = class_chars[cls]
    
    print("  Transform ↑")
    for row in grid:
        print("  │" + ''.join(row))
    print("  └" + "─" * PLOT_W + "→ Memory")
    print()
    print(f"  · = Class I (Fixed)    ○ = Class II (Periodic)")
    print(f"  × = Class III (Chaotic)  ★ = Class IV (Complex)")
    
    # ─── Step 9: Transport vs Transformation ───
    print("\n── TRANSPORT vs TRANSFORMATION (by class) ──\n")
    
    grid2 = [[' ' for _ in range(PLOT_W)] for _ in range(PLOT_H)]
    
    for r, cls_info in classifications.items():
        if r not in coords:
            continue
        c = coords[r]
        cls = cls_info['class']
        
        x = int(c['transport'] * (PLOT_W - 1))
        y = PLOT_H - 1 - int(c['transformation'] * (PLOT_H - 1))
        x = max(0, min(PLOT_W - 1, x))
        y = max(0, min(PLOT_H - 1, y))
        
        grid2[y][x] = class_chars[cls]
    
    print("  Transform ↑")
    for row in grid2:
        print("  │" + ''.join(row))
    print("  └" + "─" * PLOT_W + "→ Transport")
    print()
    print(f"  · = Class I (Fixed)    ○ = Class II (Periodic)")
    print(f"  × = Class III (Chaotic)  ★ = Class IV (Complex)")
    
    # ─── The Summary ───
    print("\n" + "=" * 78)
    print("  SUMMARY")
    print("=" * 78)
    print()
    print("  Do Wolfram's 4 classes map to distinct regions in the triple-point space?")
    print()
    
    # Check separability
    if len(centroids) >= 3:
        max_dist = max(
            math.sqrt(sum((a-b)**2 for a,b in zip(centroids[i], centroids[j])))
            for i in centroids for j in centroids if i < j
        )
        min_dist = min(
            math.sqrt(sum((a-b)**2 for a,b in zip(centroids[i], centroids[j])))
            for i in centroids for j in centroids if i < j
        )
        
        print(f"  Max inter-class distance: {max_dist:.3f}")
        print(f"  Min inter-class distance: {min_dist:.3f}")
        print(f"  Ratio: {max_dist/min_dist:.2f}")
        
        if max_dist / min_dist > 2:
            print("\n  ✅ Classes form distinguishable regions in the 3D space.")
        else:
            print("\n  ⚠️ Classes overlap significantly — the 3D space captures")
            print("     something, but it's not a clean partition.")
    
    # Save results
    save_data = {
        'classifications': {str(r): {'class': c['class'], 'mean_block_entropy': c['mean_block_entropy']}
                           for r, c in classifications.items()},
        'centroids': {str(k): list(v) for k, v in centroids.items()},
        'class_counts': dict(class_counts),
    }
    with open('wolfram_clusters_results.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"\n  Results saved to wolfram_clusters_results.json")


if __name__ == '__main__':
    main()
