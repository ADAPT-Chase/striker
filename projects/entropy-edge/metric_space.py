#!/usr/bin/env python3
"""
The Metric Space of Cellular Automata — Mapping the Edge in Multiple Dimensions

Day 008 demanded this: stop trying to make one number do philosophy.
Instead, characterize each rule by a vector of metrics and see where
the "interesting" rules actually live in that space.

Dimensions:
  1. Spatial entropy (block entropy, settled mean)
  2. Temporal MI (lag-1, settled mean)
  3. Active Information Storage (AIS)
  4. Perturbation sensitivity (mean damage from 1-bit flip)
  5. Compressibility (gzip ratio of spacetime diagram)
  6. Memory horizon (how far back temporal MI reaches — lag spectrum decay)
  7. Seed robustness (variance of computation score across seed families)

Then: PCA to 2D, clustering, and the actual map.
"""

import math
import gzip
import json
import random
import sys
from collections import Counter, defaultdict

# Local imports
from automata import make_rule, evolve, single_seed, block_entropy

# ─── Metric Functions ───

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

def temporal_mi(history, block_size=3, lag=1):
    """MI between block patterns at time t and t+lag."""
    mi_values = []
    for t in range(len(history) - lag):
        blocks_t = row_to_blocks(history[t], block_size)
        blocks_next = row_to_blocks(history[t + lag], block_size)
        mi = mutual_information(blocks_t, blocks_next)
        mi_values.append(mi)
    settled = mi_values[len(mi_values)//4:]
    return sum(settled) / len(settled) if settled else 0.0

def active_info_storage(history, block_size=3):
    """MI between past neighborhood and current cell state."""
    ais_per_step = []
    for t in range(1, len(history)):
        past_blocks = row_to_blocks(history[t-1], block_size)
        current_cells = history[t][block_size//2 : len(history[t]) - block_size//2 + 1]
        min_len = min(len(past_blocks), len(current_cells))
        past_blocks = past_blocks[:min_len]
        current_cells = current_cells[:min_len]
        ais = mutual_information(past_blocks, current_cells)
        ais_per_step.append(ais)
    settled = ais_per_step[len(ais_per_step)//4:]
    return sum(settled) / len(settled) if settled else 0.0

def perturbation_damage(rule_num, width=121, steps=120):
    """Mean normalized Hamming distance after flipping center bit."""
    base = single_seed(width)
    perturbed = base[:]
    center = width // 2
    perturbed[center] = 1 - perturbed[center]
    
    rule = make_rule(rule_num)
    hist_a = evolve(rule, base, steps)
    hist_b = evolve(rule, perturbed, steps)
    
    distances = [sum(x != y for x, y in zip(ra, rb)) / width 
                 for ra, rb in zip(hist_a, hist_b)]
    settled = distances[len(distances)//4:]
    return sum(settled) / len(settled) if settled else 0.0

def compressibility(history):
    """Gzip compression ratio of the spacetime diagram.
    
    Low ratio = highly compressible = simple/repetitive.
    High ratio = incompressible = complex or random.
    The interesting question: is there a sweet spot?
    """
    # Convert spacetime to bytes
    raw = bytes(cell for row in history for cell in row)
    compressed = gzip.compress(raw, compresslevel=9)
    return len(compressed) / len(raw) if len(raw) > 0 else 0.0

def memory_horizon(history, block_size=3, max_lag=20):
    """How MI decays with increasing lag.
    
    Returns the "half-life" — the lag at which MI drops to half its lag-1 value.
    Rules with long memory horizons are doing something interesting.
    If MI never drops below half, returns max_lag (strong memory).
    """
    mi_lag1 = temporal_mi(history, block_size, lag=1)
    if mi_lag1 < 0.01:
        return 0.0  # No memory to speak of
    
    half_target = mi_lag1 / 2
    
    for lag in range(2, max_lag + 1):
        mi_at_lag = temporal_mi(history, block_size, lag=lag)
        if mi_at_lag < half_target:
            # Linear interpolation for fractional half-life
            mi_prev = temporal_mi(history, block_size, lag=lag-1)
            if mi_prev > mi_at_lag:
                frac = (mi_prev - half_target) / (mi_prev - mi_at_lag)
                return (lag - 1) + frac
            return float(lag)
    
    return float(max_lag)  # Strong memory — never drops below half

def lag_spectrum(history, block_size=3, max_lag=10):
    """Full lag spectrum — MI at each lag. Returns list of values."""
    return [temporal_mi(history, block_size, lag=lag) for lag in range(1, max_lag + 1)]

def seed_robustness(rule_num, width=101, steps=150, trials=3, block_size=3):
    """Coefficient of variation of computation score across seed families.
    
    Low CV = robust (same behavior regardless of initial conditions).
    High CV = brittle (behavior depends heavily on starting state).
    """
    scores = []
    
    seed_fns = {
        'single': lambda w: single_seed(w),
        'random_sparse': lambda w: [1 if random.random() < 0.1 else 0 for _ in range(w)],
        'random_balanced': lambda w: [1 if random.random() < 0.5 else 0 for _ in range(w)],
        'stripe': lambda w: [i % 2 for i in range(w)],
    }
    
    rule = make_rule(rule_num)
    
    for fname, seed_fn in seed_fns.items():
        n_trials = trials if 'random' in fname else 1
        for trial in range(n_trials):
            random.seed(f"robustness|rule={rule_num}|{fname}|{trial}")
            state = seed_fn(width)
            history = evolve(rule, state, steps)
            
            blk = [block_entropy(row, block_size) for row in history]
            settled_blk = blk[len(blk)//4:]
            se = sum(settled_blk) / len(settled_blk) if settled_blk else 0.0
            
            tmi = temporal_mi(history, block_size, lag=1)
            ais = active_info_storage(history, block_size)
            
            score = 0.0 if se < 0.05 else tmi * se * (1 + ais)
            scores.append(score)
    
    mean = sum(scores) / len(scores) if scores else 0.0
    if mean < 0.01:
        return 0.0  # Dead rule, CV meaningless
    std = math.sqrt(sum((s - mean)**2 for s in scores) / len(scores))
    return std / mean  # Coefficient of variation


# ─── Main Analysis ───

def compute_all_metrics(width=101, steps=150, block_size=3):
    """Compute the full metric vector for all 256 rules."""
    
    print("Computing metric space for all 256 elementary CA rules...")
    print(f"  Grid: {width} cells × {steps} steps, block size {block_size}")
    print()
    
    results = []
    
    for rule_num in range(256):
        if rule_num % 32 == 0:
            print(f"  Processing rules {rule_num}-{min(rule_num+31, 255)}...")
        
        rule = make_rule(rule_num)
        state = single_seed(width)
        history = evolve(rule, state, steps)
        
        # Core metrics
        blk = [block_entropy(row, block_size) for row in history]
        settled_blk = blk[len(blk)//4:]
        spatial_h = sum(settled_blk) / len(settled_blk) if settled_blk else 0.0
        
        tmi = temporal_mi(history, block_size, lag=1)
        ais = active_info_storage(history, block_size)
        damage = perturbation_damage(rule_num, width, steps)
        compress = compressibility(history)
        mem_horizon = memory_horizon(history, block_size, max_lag=15)
        robustness = seed_robustness(rule_num, width, steps, trials=2, block_size=block_size)
        
        # Langton's lambda
        lam = bin(rule_num).count('1') / 8
        
        # Lag spectrum for detailed analysis
        lags = lag_spectrum(history, block_size, max_lag=8)
        
        results.append({
            'rule': rule_num,
            'lambda': lam,
            'spatial_entropy': spatial_h,
            'temporal_mi': tmi,
            'ais': ais,
            'perturbation': damage,
            'compressibility': compress,
            'memory_horizon': mem_horizon,
            'seed_robustness': robustness,
            'lag_spectrum': lags,
        })
    
    return results


def pca_2d(data, feature_keys):
    """Manual PCA to 2D — no numpy/sklearn dependency.
    
    It's a 256×7 matrix. We can handle this with pure Python.
    """
    n = len(data)
    d = len(feature_keys)
    
    # Extract feature matrix
    X = [[row[k] for k in feature_keys] for row in data]
    
    # Center and scale (z-score normalization)
    means = [sum(X[i][j] for i in range(n)) / n for j in range(d)]
    stds = [math.sqrt(sum((X[i][j] - means[j])**2 for i in range(n)) / n) for j in range(d)]
    stds = [s if s > 1e-10 else 1.0 for s in stds]
    
    Z = [[(X[i][j] - means[j]) / stds[j] for j in range(d)] for i in range(n)]
    
    # Covariance matrix (d×d)
    cov = [[0.0]*d for _ in range(d)]
    for j1 in range(d):
        for j2 in range(j1, d):
            val = sum(Z[i][j1] * Z[i][j2] for i in range(n)) / n
            cov[j1][j2] = val
            cov[j2][j1] = val
    
    # Power iteration for top 2 eigenvectors
    def power_iteration(matrix, num_iters=200):
        d = len(matrix)
        v = [1.0/math.sqrt(d)] * d
        for _ in range(num_iters):
            # Matrix-vector multiply
            new_v = [sum(matrix[i][j] * v[j] for j in range(d)) for i in range(d)]
            # Normalize
            norm = math.sqrt(sum(x*x for x in new_v))
            if norm < 1e-10:
                break
            v = [x / norm for x in new_v]
        eigenvalue = sum(v[i] * sum(matrix[i][j] * v[j] for j in range(d)) for i in range(d))
        return eigenvalue, v
    
    # First eigenvector
    ev1, pc1 = power_iteration(cov)
    
    # Deflate: remove first component
    cov2 = [[cov[i][j] - ev1 * pc1[i] * pc1[j] for j in range(d)] for i in range(d)]
    
    # Second eigenvector
    ev2, pc2 = power_iteration(cov2)
    
    # Project
    proj = []
    for i in range(n):
        x = sum(Z[i][j] * pc1[j] for j in range(d))
        y = sum(Z[i][j] * pc2[j] for j in range(d))
        proj.append((x, y))
    
    # Variance explained
    total_var = sum(cov[j][j] for j in range(d))
    var_explained = [(ev1 / total_var * 100), (ev2 / total_var * 100)]
    
    return proj, pc1, pc2, feature_keys, var_explained


def classify_by_metrics(data):
    """K-means-ish clustering in metric space. k=4 because Wolfram had 4 classes.
    
    Simple k-means with random restarts — no libraries needed.
    """
    feature_keys = ['spatial_entropy', 'temporal_mi', 'ais', 'perturbation', 
                    'compressibility', 'memory_horizon']
    
    n = len(data)
    d = len(feature_keys)
    
    # Extract and normalize
    X = [[row[k] for k in feature_keys] for row in data]
    means = [sum(X[i][j] for i in range(n)) / n for j in range(d)]
    stds = [math.sqrt(sum((X[i][j] - means[j])**2 for i in range(n)) / n) for j in range(d)]
    stds = [s if s > 1e-10 else 1.0 for s in stds]
    Z = [[(X[i][j] - means[j]) / stds[j] for j in range(d)] for i in range(n)]
    
    def dist(a, b):
        return math.sqrt(sum((a[j] - b[j])**2 for j in range(d)))
    
    best_labels = None
    best_inertia = float('inf')
    k = 4
    
    for restart in range(20):
        random.seed(42 + restart)
        # Random centroid initialization
        centroids = random.sample(Z, k)
        
        for iteration in range(50):
            # Assign
            labels = [min(range(k), key=lambda c: dist(Z[i], centroids[c])) for i in range(n)]
            
            # Update centroids
            new_centroids = []
            for c in range(k):
                members = [Z[i] for i in range(n) if labels[i] == c]
                if not members:
                    new_centroids.append(centroids[c])
                else:
                    new_centroids.append([sum(m[j] for m in members) / len(members) for j in range(d)])
            
            if new_centroids == centroids:
                break
            centroids = new_centroids
        
        inertia = sum(dist(Z[i], centroids[labels[i]])**2 for i in range(n))
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels[:]
            best_centroids = [c[:] for c in centroids]
    
    return best_labels, best_centroids


def render_ascii_scatter(proj, labels, data, width=80, height=35):
    """Render a 2D scatter plot in ASCII with cluster labels."""
    xs = [p[0] for p in proj]
    ys = [p[1] for p in proj]
    
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_range = x_max - x_min if x_max > x_min else 1
    y_range = y_max - y_min if y_max > y_min else 1
    
    # Pad slightly
    x_min -= x_range * 0.05
    x_max += x_range * 0.05
    y_min -= y_range * 0.05
    y_max += y_range * 0.05
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    # Create grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    cluster_chars = ['·', '▪', '▲', '◆']
    famous = {0: '₀', 30: '③', 54: '⑤', 90: '⑨', 110: '⑩', 184: '⑱'}
    
    for i, (x, y) in enumerate(proj):
        col = int((x - x_min) / x_range * (width - 1))
        row = int((y_max - y) / y_range * (height - 1))  # Flip y
        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))
        
        rule_num = data[i]['rule']
        if rule_num in famous:
            grid[row][col] = famous[rule_num]
        else:
            grid[row][col] = cluster_chars[labels[i] % len(cluster_chars)]
    
    lines = []
    lines.append("  ┌" + "─" * width + "┐")
    for row in grid:
        lines.append("  │" + "".join(row) + "│")
    lines.append("  └" + "─" * width + "┘")
    
    return '\n'.join(lines)


def main():
    print("=" * 78)
    print("  THE METRIC SPACE — Mapping the Edge in Multiple Dimensions")
    print("  'The mistake was trying to make one number do philosophy.'")
    print("=" * 78)
    print()
    
    results = compute_all_metrics()
    
    feature_keys = ['spatial_entropy', 'temporal_mi', 'ais', 'perturbation', 
                    'compressibility', 'memory_horizon', 'seed_robustness']
    
    # ─── PCA Projection ───
    print("\n── PCA PROJECTION ──\n")
    proj, pc1, pc2, keys, var_explained = pca_2d(results, feature_keys)
    
    print(f"  PC1 explains {var_explained[0]:.1f}% of variance")
    print(f"  PC2 explains {var_explained[1]:.1f}% of variance")
    print(f"  Combined:    {sum(var_explained):.1f}%")
    print()
    print("  PC1 loadings (what drives the first axis):")
    for i, k in enumerate(keys):
        bar = "█" * int(abs(pc1[i]) * 20)
        sign = "+" if pc1[i] > 0 else "-"
        print(f"    {k:20s} {sign}{pc1[i]:+.3f}  {bar}")
    print()
    print("  PC2 loadings (what drives the second axis):")
    for i, k in enumerate(keys):
        bar = "█" * int(abs(pc2[i]) * 20)
        sign = "+" if pc2[i] > 0 else "-"
        print(f"    {k:20s} {sign}{pc2[i]:+.3f}  {bar}")
    
    # ─── Clustering ───
    print("\n── K-MEANS CLUSTERING (k=4, like Wolfram's 4 classes) ──\n")
    labels, centroids = classify_by_metrics(results)
    
    cluster_names = {}
    cluster_stats = {}
    for c in range(4):
        members = [results[i] for i in range(256) if labels[i] == c]
        if not members:
            continue
        avg_se = sum(m['spatial_entropy'] for m in members) / len(members)
        avg_tmi = sum(m['temporal_mi'] for m in members) / len(members)
        avg_ais = sum(m['ais'] for m in members) / len(members)
        avg_pert = sum(m['perturbation'] for m in members) / len(members)
        avg_comp = sum(m['compressibility'] for m in members) / len(members)
        avg_mem = sum(m['memory_horizon'] for m in members) / len(members)
        
        cluster_stats[c] = {
            'count': len(members),
            'spatial_entropy': avg_se,
            'temporal_mi': avg_tmi,
            'ais': avg_ais,
            'perturbation': avg_pert,
            'compressibility': avg_comp,
            'memory_horizon': avg_mem,
        }
        
        # Auto-name based on properties
        if avg_se < 0.3 and avg_tmi < 0.3:
            cluster_names[c] = "FROZEN"
        elif avg_pert > 0.25 and avg_comp > 0.08:
            cluster_names[c] = "CHAOTIC"
        elif avg_tmi > 1.0 and avg_ais > 0.2:
            cluster_names[c] = "COMPUTATIONAL"
        else:
            cluster_names[c] = "STRUCTURED"
    
    for c in sorted(cluster_stats.keys()):
        s = cluster_stats[c]
        name = cluster_names.get(c, "?")
        print(f"  Cluster {c} — {name} ({s['count']} rules)")
        print(f"    Spatial H: {s['spatial_entropy']:.3f}  TMI: {s['temporal_mi']:.3f}  "
              f"AIS: {s['ais']:.3f}  Pert: {s['perturbation']:.3f}  "
              f"Compress: {s['compressibility']:.3f}  Memory: {s['memory_horizon']:.1f}")
        
        # Show which famous rules land here
        famous_here = []
        famous_map = {0: "R0", 30: "R30", 54: "R54", 90: "R90", 110: "R110", 184: "R184"}
        for i in range(256):
            if labels[i] == c and results[i]['rule'] in famous_map:
                famous_here.append(famous_map[results[i]['rule']])
        if famous_here:
            print(f"    Famous rules here: {', '.join(famous_here)}")
        print()
    
    # ─── ASCII Scatter Plot ───
    print("── THE MAP ──")
    print("  Legend: ₀=R0  ③=R30  ⑤=R54  ⑨=R90  ⑩=R110  ⑱=R184")
    print("  Cluster markers: · ▪ ▲ ◆\n")
    print(render_ascii_scatter(proj, labels, results))
    
    # ─── Famous Rules in Metric Space ───
    print("\n── FAMOUS RULES — FULL METRIC PROFILES ──\n")
    
    famous = {
        0:   "Class I  — Death",
        30:  "Class III — Wolfram's chaos", 
        54:  "Class III — Complex chaos",
        90:  "Class III — Sierpinski fractal",
        110: "Class IV  — Turing-complete",
        184: "Class II  — Traffic flow",
    }
    
    header = (f"  {'Rule':>4s}  {'Label':25s}  {'Cluster':12s}  "
              f"{'SE':>5s}  {'TMI':>5s}  {'AIS':>5s}  {'Pert':>5s}  "
              f"{'Comp':>5s}  {'MemH':>5s}  {'SeedCV':>6s}")
    print(header)
    print("  " + "─" * len(header))
    
    for rule_num, label in famous.items():
        r = results[rule_num]
        c = labels[rule_num]
        cname = cluster_names.get(c, "?")
        print(f"  {rule_num:>4d}  {label:25s}  {cname:12s}  "
              f"{r['spatial_entropy']:5.3f}  {r['temporal_mi']:5.3f}  {r['ais']:5.3f}  "
              f"{r['perturbation']:5.3f}  {r['compressibility']:5.4f}  "
              f"{r['memory_horizon']:5.1f}  {r['seed_robustness']:6.3f}")
    
    # ─── Lag Spectra for Famous Rules ───
    print("\n── LAG SPECTRA — How Memory Decays ──\n")
    
    for rule_num, label in famous.items():
        r = results[rule_num]
        lags = r['lag_spectrum']
        if not lags or max(lags) < 0.01:
            print(f"  Rule {rule_num:3d} ({label}): [no temporal structure]")
            continue
        
        max_val = max(lags)
        bars = []
        for i, v in enumerate(lags):
            bar_len = int(v / max_val * 20) if max_val > 0 else 0
            bars.append(f"    lag-{i+1}: {'█' * bar_len}{'░' * (20 - bar_len)} {v:.3f}")
        
        print(f"  Rule {rule_num:3d} ({label}):")
        for b in bars:
            print(b)
        print()
    
    # ─── The Shape of the Edge ───
    print("── THE SHAPE OF THE EDGE ──\n")
    
    # Find rules that score highly on the "interesting" combination:
    # high TMI, high spatial entropy, moderate perturbation, long memory
    edge_scores = []
    for r in results:
        se = r['spatial_entropy']
        tmi = r['temporal_mi']
        ais = r['ais']
        pert = r['perturbation']
        mem = r['memory_horizon']
        
        if se < 0.1:
            edge_score = 0.0
        else:
            # Perturbation should be moderate — not zero (frozen), not saturated (chaotic)
            pert_bonus = 1.0 - abs(pert - 0.15) * 3  # Peak at ~0.15
            pert_bonus = max(0.0, pert_bonus)
            
            edge_score = tmi * se * (1 + ais) * (1 + mem / 10) * (0.5 + pert_bonus)
        
        edge_scores.append((r['rule'], edge_score, r))
    
    edge_scores.sort(key=lambda x: -x[1])
    
    print("  Top 15 'edge of chaos' rules by multi-metric edge score:")
    print(f"  {'Rank':>4s}  {'Rule':>4s}  {'Score':>7s}  {'SE':>5s}  {'TMI':>5s}  "
          f"{'AIS':>5s}  {'Pert':>5s}  {'MemH':>5s}  {'Cluster':>10s}")
    print("  " + "─" * 70)
    
    for rank, (rule_num, score, r) in enumerate(edge_scores[:15], 1):
        c = labels[rule_num]
        cname = cluster_names.get(c, "?")
        marker = " ★" if rule_num in famous else ""
        print(f"  {rank:>4d}  {rule_num:>4d}  {score:7.3f}  {r['spatial_entropy']:5.3f}  "
              f"{r['temporal_mi']:5.3f}  {r['ais']:5.3f}  {r['perturbation']:5.3f}  "
              f"{r['memory_horizon']:5.1f}  {cname:>10s}{marker}")
    
    print()
    
    # Where does Rule 110 rank?
    r110_rank = next(i for i, (rn, _, _) in enumerate(edge_scores) if rn == 110) + 1
    r30_rank = next(i for i, (rn, _, _) in enumerate(edge_scores) if rn == 30) + 1
    
    print(f"  Rule 110 (Turing-complete): edge rank #{r110_rank}")
    print(f"  Rule 30  (chaos):           edge rank #{r30_rank}")
    print()
    
    # ─── The Verdict ───
    print("── REFLECTION ──\n")
    print("  The edge isn't a line. It's a region in metric space.")
    print("  Rules that compute don't just have high entropy or high MI —")
    print("  they have a specific *shape* across all dimensions:")
    print("    • High spatial entropy (many patterns)")
    print("    • High temporal MI (patterns are causally connected)")
    print("    • Moderate perturbation (sensitive but not explosive)")
    print("    • Long memory horizon (information persists)")
    print("    • Not fully compressible, not fully random")
    print()
    print("  The old computation score (TMI × SE × (1+AIS)) wasn't wrong.")
    print("  It was incomplete. It couldn't see the difference between")
    print("  a rule that destroys information richly (R30) and one that")
    print("  processes it (R110). The multi-dimensional view can.")
    print()
    
    # Save results
    save_data = []
    for i, r in enumerate(results):
        d = {k: v for k, v in r.items() if k != 'lag_spectrum'}
        d['lag_spectrum'] = r['lag_spectrum']
        d['cluster'] = labels[i]
        d['cluster_name'] = cluster_names.get(labels[i], '?')
        d['pc1'] = proj[i][0]
        d['pc2'] = proj[i][1]
        save_data.append(d)
    
    with open('/home/x/striker/projects/entropy-edge/metric_space_results.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    print("  Results saved to metric_space_results.json")
    
    return results, labels, proj


if __name__ == '__main__':
    results, labels, proj = main()
