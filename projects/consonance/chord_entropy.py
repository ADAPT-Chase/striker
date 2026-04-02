#!/usr/bin/env python3
"""
Chord Entropy — Extending harmonic entropy from intervals to chords.

Day 016 established that harmonic entropy (r=0.817) beats roughness (r=0.738) 
and ratio simplicity (r=0.619) at predicting interval consonance.

Now the question: does harmonic entropy extend to chords?

A major triad should have lower entropy than a diminished triad.
A dominant 7th should have higher entropy than a major 7th.
A jazz voicing should sit near the phase boundary.

Two approaches to chord entropy:
1. Pairwise: average the interval entropies of all pairs within the chord
2. Joint: treat the chord as a point in N-dimensional ratio space and compute 
   the joint entropy over all possible ratio interpretations simultaneously

Approach 2 is theoretically correct but computationally explosive.
Approach 1 is an approximation but tractable. Start there, see if it predicts.

The test: correlate chord entropy with established music theory rankings
of chord consonance/stability.
"""

import math
import itertools
from harmonic_entropy import (
    harmonic_entropy, harmonic_entropy_consonance, 
    roughness_consonance, ratio_consonance,
    interval_roughness, pearson_correlation
)


# ─── Chord Definitions (semitones from root) ───

CHORDS = {
    # Triads
    'Major':        [0, 4, 7],
    'Minor':        [0, 3, 7],
    'Diminished':   [0, 3, 6],
    'Augmented':    [0, 4, 8],
    'Sus4':         [0, 5, 7],
    'Sus2':         [0, 2, 7],
    
    # 7th chords
    'Maj7':         [0, 4, 7, 11],
    'Dom7':         [0, 4, 7, 10],
    'Min7':         [0, 3, 7, 10],
    'Dim7':         [0, 3, 6, 9],
    'MinMaj7':      [0, 3, 7, 11],
    'Aug7':         [0, 4, 8, 10],
    'HalfDim7':     [0, 3, 6, 10],
    
    # Extended / jazz
    'Maj9':         [0, 4, 7, 11, 14],
    'Dom9':         [0, 4, 7, 10, 14],
    'Min9':         [0, 3, 7, 10, 14],
    'Dom7#9':       [0, 4, 7, 10, 15],   # Hendrix chord
    'Dom7b9':       [0, 4, 7, 10, 13],
    'Maj7#11':      [0, 4, 7, 11, 18],   # Lydian chord
    
    # Clusters and extremes
    'Chromatic3':   [0, 1, 2],            # Maximum dissonance
    'Quartal':      [0, 5, 10],           # Stacked 4ths
    'Tritone+':     [0, 6, 12],           # Tritones
    'Power':        [0, 7, 12],           # Power chord (5th + octave)
}

# Music-theoretic consonance ranking (higher = more consonant/stable)
# This is my synthesis from common practice harmony textbooks
CHORD_CONSONANCE_RANKING = {
    'Power':        0.95,   # Maximally stable (open 5th)
    'Major':        0.90,
    'Minor':        0.80,
    'Sus4':         0.70,
    'Sus2':         0.70,
    'Maj7':         0.65,
    'Augmented':    0.45,
    'Dom7':         0.50,
    'Min7':         0.55,
    'MinMaj7':      0.40,
    'Quartal':      0.50,
    'HalfDim7':     0.35,
    'Dom9':         0.40,
    'Maj9':         0.50,
    'Min9':         0.45,
    'Aug7':         0.30,
    'Diminished':   0.30,
    'Dim7':         0.25,
    'Maj7#11':      0.35,
    'Dom7#9':       0.20,
    'Dom7b9':       0.20,
    'Tritone+':     0.15,
    'Chromatic3':   0.05,
}


def semitones_to_ratio(semitones):
    """Convert semitones to frequency ratio (12-TET)."""
    return 2 ** (semitones / 12)


def chord_pairwise_entropy(semitones, s=0.01, max_n=48):
    """
    Pairwise chord entropy: average harmonic entropy of all interval pairs.
    
    For a triad [0, 4, 7], the pairs are:
    - 0→4 (major 3rd, ratio 1.260)
    - 0→7 (perfect 5th, ratio 1.498)
    - 4→7 (minor 3rd, ratio 1.189)
    
    This captures the "total information load" of the chord.
    """
    pairs = list(itertools.combinations(semitones, 2))
    if not pairs:
        return 0.0
    
    entropies = []
    for low, high in pairs:
        interval = high - low
        ratio = semitones_to_ratio(interval)
        he = harmonic_entropy(ratio, s=s, max_n=max_n)
        entropies.append(he)
    
    return sum(entropies) / len(entropies)


def chord_pairwise_consonance(semitones, s=0.01, max_n=48):
    """Consonance = inverse of pairwise entropy."""
    he = chord_pairwise_entropy(semitones, s=s, max_n=max_n)
    return 1.0 / (1.0 + he)


def chord_max_entropy(semitones, s=0.01, max_n=48):
    """
    Max-pair entropy: the dissonance of a chord is dominated by its 
    worst interval (the most ambiguous pair).
    
    Hypothesis: perception might weight the worst pair more heavily
    than the average, because dissonance is more salient than consonance.
    """
    pairs = list(itertools.combinations(semitones, 2))
    if not pairs:
        return 0.0
    
    max_he = 0.0
    for low, high in pairs:
        interval = high - low
        ratio = semitones_to_ratio(interval)
        he = harmonic_entropy(ratio, s=s, max_n=max_n)
        max_he = max(max_he, he)
    
    return max_he


def chord_total_roughness(semitones, base_freq=220, n_partials=6):
    """Total roughness of all pairs in the chord."""
    pairs = list(itertools.combinations(semitones, 2))
    if not pairs:
        return 0.0
    
    total = 0.0
    for low, high in pairs:
        interval = high - low
        ratio = semitones_to_ratio(interval)
        total += interval_roughness(ratio, base_freq, n_partials)
    
    return total / len(pairs)


def chord_roughness_consonance(semitones, base_freq=220, n_partials=6):
    """Consonance = inverse roughness."""
    r = chord_total_roughness(semitones, base_freq, n_partials)
    return 1.0 / (1.0 + 10 * r)


def chord_ratio_consonance(semitones, max_denom=64):
    """Average ratio simplicity of all pairs."""
    pairs = list(itertools.combinations(semitones, 2))
    if not pairs:
        return 0.0
    
    total = 0.0
    for low, high in pairs:
        interval = high - low
        ratio = semitones_to_ratio(interval)
        total += ratio_consonance(ratio, max_denom)
    
    return total / len(pairs)


def chord_entropy_profile(semitones, s=0.01, max_n=48):
    """
    Detailed entropy profile showing each interval's contribution.
    Returns dict with per-pair breakdown.
    """
    pairs = list(itertools.combinations(semitones, 2))
    profile = []
    
    for low, high in pairs:
        interval = high - low
        ratio = semitones_to_ratio(interval)
        he = harmonic_entropy(ratio, s=s, max_n=max_n)
        profile.append({
            'pair': (low, high),
            'interval_semitones': interval,
            'ratio': ratio,
            'entropy': he,
        })
    
    return sorted(profile, key=lambda x: -x['entropy'])


def entropy_variance(semitones, s=0.01, max_n=48):
    """
    Variance of entropies across pairs.
    
    Hypothesis: chords where all pairs have similar entropy feel more 
    "stable" than chords with one very consonant and one very dissonant pair.
    The variance captures internal tension/conflict.
    """
    pairs = list(itertools.combinations(semitones, 2))
    if len(pairs) < 2:
        return 0.0
    
    entropies = []
    for low, high in pairs:
        interval = high - low
        ratio = semitones_to_ratio(interval)
        entropies.append(harmonic_entropy(ratio, s=s, max_n=max_n))
    
    mean = sum(entropies) / len(entropies)
    variance = sum((e - mean) ** 2 for e in entropies) / len(entropies)
    return variance


def main():
    print("=" * 90)
    print("  CHORD ENTROPY — Phase Transitions in Harmony")
    print("  Extending harmonic entropy from intervals to chords")
    print("=" * 90)
    
    # ─── Compute all metrics for all chords ───
    results = {}
    
    for name, semitones in CHORDS.items():
        he_avg = chord_pairwise_entropy(semitones)
        he_max = chord_max_entropy(semitones)
        he_var = entropy_variance(semitones)
        he_cons = chord_pairwise_consonance(semitones)
        rough_cons = chord_roughness_consonance(semitones)
        ratio_cons = chord_ratio_consonance(semitones)
        n_pairs = len(list(itertools.combinations(semitones, 2)))
        
        results[name] = {
            'semitones': semitones,
            'n_notes': len(semitones),
            'n_pairs': n_pairs,
            'avg_entropy': he_avg,
            'max_entropy': he_max,
            'entropy_var': he_var,
            'he_consonance': he_cons,
            'rough_consonance': rough_cons,
            'ratio_consonance': ratio_cons,
        }
    
    # ─── Print Results Table ───
    print(f"\n  {'Chord':>12s}  {'Notes':>5s}  {'Pairs':>5s}  │ {'AvgH(E)':>8s}  {'MaxH(E)':>8s}  {'Var':>6s}  │ {'H.E.':>5s}  {'Rough':>5s}  {'Ratio':>5s}  │ {'Theory':>6s}")
    print(f"  {'─'*12}  {'─'*5}  {'─'*5}  │ {'─'*8}  {'─'*8}  {'─'*6}  │ {'─'*5}  {'─'*5}  {'─'*5}  │ {'─'*6}")
    
    # Sort by avg entropy (most consonant first)
    for name in sorted(results, key=lambda n: results[n]['avg_entropy']):
        r = results[name]
        theory = CHORD_CONSONANCE_RANKING.get(name, -1)
        theory_str = f"{theory:.2f}" if theory >= 0 else "  -- "
        print(f"  {name:>12s}  {r['n_notes']:>5d}  {r['n_pairs']:>5d}  │ "
              f"{r['avg_entropy']:>8.3f}  {r['max_entropy']:>8.3f}  {r['entropy_var']:>6.3f}  │ "
              f"{r['he_consonance']:>5.3f}  {r['rough_consonance']:>5.3f}  {r['ratio_consonance']:>5.3f}  │ "
              f"{theory_str:>6s}")
    
    # ─── Correlation Analysis ───
    print(f"\n{'='*90}")
    print(f"  CORRELATION WITH MUSIC THEORY RANKINGS")
    print(f"{'='*90}\n")
    
    # Only use chords that have theory rankings
    ranked_chords = [n for n in results if n in CHORD_CONSONANCE_RANKING]
    
    theory_vals = [CHORD_CONSONANCE_RANKING[n] for n in ranked_chords]
    he_cons_vals = [results[n]['he_consonance'] for n in ranked_chords]
    rough_cons_vals = [results[n]['rough_consonance'] for n in ranked_chords]
    ratio_cons_vals = [results[n]['ratio_consonance'] for n in ranked_chords]
    
    # Also try: 1/(1 + max_entropy) and combined metrics
    he_max_cons = [1.0 / (1.0 + results[n]['max_entropy']) for n in ranked_chords]
    he_var_vals = [results[n]['entropy_var'] for n in ranked_chords]
    
    # Combined: avg entropy penalized by variance (internal conflict hurts)
    combined = [results[n]['he_consonance'] / (1.0 + results[n]['entropy_var']) for n in ranked_chords]
    
    metrics = [
        ('Pairwise H.E. consonance', he_cons_vals),
        ('Max-pair H.E. consonance', he_max_cons),
        ('Roughness consonance', rough_cons_vals),
        ('Ratio simplicity', ratio_cons_vals),
        ('Combined (H.E. / (1+var))', combined),
        ('Entropy variance (neg)', [-v for v in he_var_vals]),  # Higher var = less consonant
    ]
    
    for name, vals in metrics:
        corr = pearson_correlation(theory_vals, vals)
        print(f"  {name:>35s}:  r = {corr:+.4f}")
    
    # ─── Entropy Profiles for Key Chords ───
    print(f"\n{'='*90}")
    print(f"  ENTROPY PROFILES — Where the dissonance lives")
    print(f"{'='*90}")
    
    profile_chords = ['Major', 'Minor', 'Diminished', 'Dom7', 'Dom7#9', 'Chromatic3']
    
    interval_names = {
        1: 'm2', 2: 'M2', 3: 'm3', 4: 'M3', 5: 'P4', 6: 'TT',
        7: 'P5', 8: 'm6', 9: 'M6', 10: 'm7', 11: 'M7', 12: 'P8',
        13: 'm9', 14: 'M9', 15: 'A9', 16: 'm10', 17: 'M10', 18: 'A11',
    }
    
    for chord_name in profile_chords:
        if chord_name not in CHORDS:
            continue
        semitones = CHORDS[chord_name]
        profile = chord_entropy_profile(semitones)
        avg = chord_pairwise_entropy(semitones)
        
        print(f"\n  {chord_name} {semitones}  (avg entropy: {avg:.3f})")
        
        for p in profile:
            iname = interval_names.get(p['interval_semitones'], f"{p['interval_semitones']}st")
            bar_len = int(p['entropy'] * 8)
            bar = '█' * bar_len + '░' * max(0, 40 - bar_len)
            print(f"    {p['pair'][0]:>2d}→{p['pair'][1]:<2d} ({iname:>3s}) H(E)={p['entropy']:.3f}  {bar}")
    
    # ─── The Phase Space of Chords ───
    print(f"\n{'='*90}")
    print(f"  CHORD PHASE SPACE")
    print(f"  Avg Entropy (x) vs Entropy Variance (y)")
    print(f"{'='*90}\n")
    
    # ASCII scatter plot: avg entropy vs variance
    PLOT_W, PLOT_H = 65, 25
    grid = [[' ' for _ in range(PLOT_W)] for _ in range(PLOT_H)]
    
    all_avg = [results[n]['avg_entropy'] for n in results]
    all_var = [results[n]['entropy_var'] for n in results]
    
    min_avg, max_avg = min(all_avg), max(all_avg)
    min_var, max_var = min(all_var), max(all_var)
    
    # Avoid division by zero
    range_avg = max(max_avg - min_avg, 0.001)
    range_var = max(max_var - min_var, 0.001)
    
    labels = {}
    for name, r in results.items():
        x = int((r['avg_entropy'] - min_avg) / range_avg * (PLOT_W - 1))
        y = PLOT_H - 1 - int((r['entropy_var'] - min_var) / range_var * (PLOT_H - 1))
        x = max(0, min(PLOT_W - 1, x))
        y = max(0, min(PLOT_H - 1, y))
        
        # Use first char of chord type
        ch = name[0]
        if name.startswith('Dom'): ch = 'D'
        elif name.startswith('Dim'): ch = 'd'
        elif name.startswith('Min'): ch = 'm'
        elif name.startswith('Maj'): ch = 'M'
        elif name.startswith('Aug'): ch = 'A'
        elif name.startswith('Sus'): ch = 'S'
        elif name.startswith('Pow'): ch = 'P'
        elif name.startswith('Qua'): ch = 'Q'
        elif name.startswith('Tri'): ch = 'T'
        elif name.startswith('Chr'): ch = 'X'
        elif name.startswith('Hal'): ch = 'h'
        
        grid[y][x] = ch
        labels[ch] = name
    
    print("  Entropy Variance ↑")
    for row in grid:
        print("  │" + ''.join(row))
    print("  └" + "─" * PLOT_W + "→ Avg Entropy")
    print()
    
    # Legend
    seen = set()
    legend_items = []
    for ch, name in sorted(labels.items()):
        if ch not in seen:
            legend_items.append(f"{ch}={name}")
            seen.add(ch)
    
    # Print legend in columns
    cols = 3
    for i in range(0, len(legend_items), cols):
        row_items = legend_items[i:i+cols]
        print("  " + "  ".join(f"{item:<25s}" for item in row_items))
    
    # ─── Key Insight ───
    print(f"\n{'='*90}")
    print(f"  FINDINGS")
    print(f"{'='*90}\n")
    
    # Find best predictor
    best_name = None
    best_corr = 0
    for name, vals in metrics:
        corr = abs(pearson_correlation(theory_vals, vals))
        if corr > best_corr:
            best_corr = corr
            best_name = name
    
    print(f"  Best predictor of chord consonance: {best_name}")
    print(f"  Correlation: r = {best_corr:.4f}")
    print()
    
    # Compare triads
    triads = ['Major', 'Minor', 'Diminished', 'Augmented']
    print("  Triad entropy ordering:")
    for name in sorted(triads, key=lambda n: results[n]['avg_entropy']):
        print(f"    {name:>12s}: avg H(E) = {results[name]['avg_entropy']:.3f}")
    
    print()
    
    # Compare 7th chords  
    sevenths = ['Maj7', 'Min7', 'Dom7', 'Dim7', 'HalfDim7']
    print("  7th chord entropy ordering:")
    for name in sorted(sevenths, key=lambda n: results[n]['avg_entropy']):
        print(f"    {name:>12s}: avg H(E) = {results[name]['avg_entropy']:.3f}")
    
    print()
    print("  Phase transition hypothesis:")
    print("  - Low entropy, low variance → STABLE (major, power chords)")
    print("  - High entropy, low variance → UNIFORMLY TENSE (chromatic clusters)")
    print("  - Moderate entropy, HIGH variance → INTERESTING (dominant 7th, jazz)")
    print("  - The 'edge' chords (high variance) are the ones that MOVE music forward")
    print()
    print("  If this is right, the variance axis captures *function* —")
    print("  stable chords (tonic) vs unstable chords (dominant) vs")
    print("  maximally unstable chords (augmented 6th, Neapolitan).")


if __name__ == '__main__':
    main()
