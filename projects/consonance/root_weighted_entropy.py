#!/usr/bin/env python3
"""
Root-Weighted Harmonic Entropy — Breaking the Major/Minor Degeneracy

Day 017 found that pairwise chord entropy can't distinguish major from minor
triads because they contain identical interval sets {m3, M3, P5}. But our ears
clearly hear them differently. The missing ingredient: the ROOT.

The ear anchors harmonic perception to the bass note. The interval from bass
to each upper voice defines the chord's character more than the upper-voice 
intervals do. A major triad has M3 at the bottom (bright, stable); a minor 
triad has m3 at the bottom (dark, less stable).

This module implements root-weighted pairwise entropy: intervals from the bass
get weight α > 1, upper-voice intervals get weight 1. The question is whether
this simple weighting breaks the degeneracy and improves correlation with 
music theory consonance rankings.

The deeper question: does the auditory system literally weight bass intervals 
more in its entropy computation? If so, "root" isn't a music theory abstraction —
it's a computational primitive of perception.
"""

import math
import itertools
from harmonic_entropy import (
    harmonic_entropy, pearson_correlation,
    HUMAN_CONSONANCE
)
from chord_entropy import (
    CHORDS, CHORD_CONSONANCE_RANKING,
    semitones_to_ratio, chord_pairwise_entropy, entropy_variance
)


def root_weighted_entropy(semitones, alpha=2.0, s=0.01, max_n=48):
    """
    Root-weighted pairwise chord entropy.
    
    Intervals from the bass note (lowest pitch) get weight alpha.
    Upper-voice intervals get weight 1.
    
    For C major [0, 4, 7]:
      - 0→4 (M3): weight alpha (bass interval)
      - 0→7 (P5): weight alpha (bass interval)  
      - 4→7 (m3): weight 1 (upper interval)
    
    For A minor [0, 3, 7]:
      - 0→3 (m3): weight alpha (bass interval)
      - 0→7 (P5): weight alpha (bass interval)
      - 3→7 (M3): weight 1 (upper interval)
      
    Now major ≠ minor because the weighted-average entropy differs!
    """
    if len(semitones) < 2:
        return 0.0
    
    bass = min(semitones)
    pairs = list(itertools.combinations(sorted(semitones), 2))
    
    weighted_sum = 0.0
    total_weight = 0.0
    
    for low, high in pairs:
        interval = high - low
        ratio = semitones_to_ratio(interval)
        he = harmonic_entropy(ratio, s=s, max_n=max_n)
        
        # Bass interval gets higher weight
        w = alpha if low == bass else 1.0
        weighted_sum += w * he
        total_weight += w
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def root_weighted_variance(semitones, alpha=2.0, s=0.01, max_n=48):
    """
    Weighted variance of interval entropies, with bass intervals upweighted.
    """
    if len(semitones) < 2:
        return 0.0
    
    bass = min(semitones)
    pairs = list(itertools.combinations(sorted(semitones), 2))
    
    if len(pairs) < 2:
        return 0.0
    
    # Compute weighted mean first
    entropies = []
    weights = []
    for low, high in pairs:
        interval = high - low
        ratio = semitones_to_ratio(interval)
        he = harmonic_entropy(ratio, s=s, max_n=max_n)
        w = alpha if low == bass else 1.0
        entropies.append(he)
        weights.append(w)
    
    total_w = sum(weights)
    weighted_mean = sum(w * e for w, e in zip(weights, entropies)) / total_w
    
    # Weighted variance
    variance = sum(w * (e - weighted_mean) ** 2 for w, e in zip(weights, entropies)) / total_w
    return variance


def root_weighted_consonance(semitones, alpha=2.0, s=0.01, max_n=48):
    """Consonance = inverse of root-weighted entropy."""
    he = root_weighted_entropy(semitones, alpha=alpha, s=s, max_n=max_n)
    return 1.0 / (1.0 + he)


def scan_alpha(alphas=None):
    """
    Sweep alpha values to find optimal root-weighting.
    
    If alpha=1 is equivalent to unweighted pairwise entropy.
    If alpha→∞ only bass intervals matter.
    The optimum should be somewhere in between.
    """
    if alphas is None:
        alphas = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0]
    
    ranked_chords = [n for n in CHORDS if n in CHORD_CONSONANCE_RANKING]
    theory_vals = [CHORD_CONSONANCE_RANKING[n] for n in ranked_chords]
    
    print(f"\n  Alpha Sweep — Finding optimal root weight")
    print(f"  {'Alpha':>6s}  │ {'Corr (entropy)':>14s}  {'Corr (combined)':>15s}  │ {'Major H':>8s}  {'Minor H':>8s}  {'Δ(Maj-Min)':>10s}")
    print(f"  {'─'*6}  │ {'─'*14}  {'─'*15}  │ {'─'*8}  {'─'*8}  {'─'*10}")
    
    best_alpha = 1.0
    best_corr = 0.0
    
    for alpha in alphas:
        # Compute consonance for all chords
        cons_vals = [root_weighted_consonance(CHORDS[n], alpha=alpha) for n in ranked_chords]
        var_vals = [root_weighted_variance(CHORDS[n], alpha=alpha) for n in ranked_chords]
        combined = [c / (1.0 + v) for c, v in zip(cons_vals, var_vals)]
        
        corr_ent = pearson_correlation(theory_vals, cons_vals)
        corr_comb = pearson_correlation(theory_vals, combined)
        
        # Check major vs minor
        h_major = root_weighted_entropy(CHORDS['Major'], alpha=alpha)
        h_minor = root_weighted_entropy(CHORDS['Minor'], alpha=alpha)
        delta = h_major - h_minor
        
        print(f"  {alpha:>6.2f}  │ {corr_ent:>+14.4f}  {corr_comb:>+15.4f}  │ {h_major:>8.4f}  {h_minor:>8.4f}  {delta:>+10.4f}")
        
        if abs(corr_comb) > abs(best_corr):
            best_corr = corr_comb
            best_alpha = alpha
    
    print(f"\n  Best alpha: {best_alpha} (correlation: {best_corr:+.4f})")
    return best_alpha


def test_degeneracy_breaking(alpha=2.0):
    """
    Test whether root-weighting breaks the triad degeneracy.
    
    Key pairs that should now differ:
    - Major vs Minor (same intervals, different stacking)
    - Maj7 vs MinMaj7
    - Dom7 vs HalfDim7 (both contain tritone)
    """
    print(f"\n  Degeneracy Breaking Test (alpha={alpha})")
    print(f"  {'Chord A':>12s}  {'Chord B':>12s}  │ {'Pairwise':>10s}  │ {'Root-Wtd A':>10s}  {'Root-Wtd B':>10s}  {'Δ':>8s}  │ {'Status':>8s}")
    print(f"  {'─'*12}  {'─'*12}  │ {'─'*10}  │ {'─'*10}  {'─'*10}  {'─'*8}  │ {'─'*8}")
    
    test_pairs = [
        ('Major', 'Minor'),
        ('Maj7', 'MinMaj7'),
        ('Sus2', 'Sus4'),
        ('Dom7', 'HalfDim7'),
        ('Augmented', 'Diminished'),
        ('Maj9', 'Min9'),
        ('Dom7#9', 'Dom7b9'),
    ]
    
    for name_a, name_b in test_pairs:
        if name_a not in CHORDS or name_b not in CHORDS:
            continue
        
        # Unweighted (should be degenerate for some pairs)
        pw_a = chord_pairwise_entropy(CHORDS[name_a])
        pw_b = chord_pairwise_entropy(CHORDS[name_b])
        pw_same = abs(pw_a - pw_b) < 0.001
        
        # Root-weighted
        rw_a = root_weighted_entropy(CHORDS[name_a], alpha=alpha)
        rw_b = root_weighted_entropy(CHORDS[name_b], alpha=alpha)
        delta = rw_a - rw_b
        
        was_degenerate = "DEGEN" if pw_same else "diff"
        now_status = "BROKEN ✓" if pw_same and abs(delta) > 0.001 else ("still =" if abs(delta) < 0.001 else "diff")
        
        print(f"  {name_a:>12s}  {name_b:>12s}  │ {'SAME' if pw_same else 'diff':>10s}  │ "
              f"{rw_a:>10.4f}  {rw_b:>10.4f}  {delta:>+8.4f}  │ {now_status:>8s}")


def rerun_progressions(alpha=2.0):
    """
    Re-run progression trajectories with root-weighted entropy.
    The key test: do triadic progressions now trace DIFFERENT paths?
    """
    from progression_trajectories import VOICINGS, PROGRESSIONS
    
    print(f"\n  Progression Trajectories with Root-Weighted Entropy (alpha={alpha})")
    print(f"  ═══════════════════════════════════════════════════════════════\n")
    
    # Compute coordinates for all voicings
    def rw_coords(voicing):
        base = min(voicing)
        normalized = [n - base for n in voicing]
        return {
            'avg_entropy': root_weighted_entropy(normalized, alpha=alpha),
            'variance': root_weighted_variance(normalized, alpha=alpha),
        }
    
    # Test: do C major and A minor now differ?
    c_coords = rw_coords(VOICINGS['C'])
    am_coords = rw_coords(VOICINGS['Am'])
    
    print(f"  C major:  H(E)={c_coords['avg_entropy']:.4f}  var={c_coords['variance']:.4f}")
    print(f"  A minor:  H(E)={am_coords['avg_entropy']:.4f}  var={am_coords['variance']:.4f}")
    delta_h = am_coords['avg_entropy'] - c_coords['avg_entropy']
    delta_v = am_coords['variance'] - c_coords['variance']
    print(f"  Δ(Am - C): ΔH={delta_h:+.4f}  ΔVar={delta_v:+.4f}")
    
    if abs(delta_h) > 0.001 or abs(delta_v) > 0.001:
        print(f"  ✅ DEGENERACY BROKEN — triads now occupy different positions!")
    else:
        print(f"  ❌ Still degenerate — root weighting didn't help for voicings")
    
    # Print all diatonic chord positions
    print(f"\n  Diatonic Chords in C Major (root-weighted)")
    print(f"  {'Chord':>8s}  │ {'H(E)':>8s}  {'Var':>8s}")
    print(f"  {'─'*8}  │ {'─'*8}  {'─'*8}")
    
    diatonic = ['C', 'Dm', 'Em', 'F', 'G', 'Am', 'Bdim']
    for name in diatonic:
        if name in VOICINGS:
            coords = rw_coords(VOICINGS[name])
            print(f"  {name:>8s}  │ {coords['avg_entropy']:>8.4f}  {coords['variance']:>8.4f}")
    
    # Now trace key progressions
    print(f"\n  I-V-I Trajectory (triads)")
    prog_names = ['I-V-I (Authentic)', 'I-IV-V-I (Classical)', 'I-vi-IV-V (50s)', 'I-V-vi-IV (Axis)']
    
    for prog_name in prog_names:
        if prog_name not in PROGRESSIONS:
            continue
        chords = PROGRESSIONS[prog_name]
        print(f"\n  {prog_name}:")
        
        prev_h = None
        for chord_name in chords:
            if chord_name not in VOICINGS:
                continue
            coords = rw_coords(VOICINGS[chord_name])
            arrow = ""
            if prev_h is not None:
                dh = coords['avg_entropy'] - prev_h
                arrow = f"  (ΔH={dh:+.3f})"
            print(f"    {chord_name:>6s}  H(E)={coords['avg_entropy']:.4f}  var={coords['variance']:.4f}{arrow}")
            prev_h = coords['avg_entropy']


def full_comparison(alpha=2.0):
    """
    Full side-by-side comparison: pairwise vs root-weighted.
    """
    print(f"\n  ═══════════════════════════════════════════════════════════════")
    print(f"  Full Chord Entropy Comparison: Pairwise vs Root-Weighted (α={alpha})")
    print(f"  ═══════════════════════════════════════════════════════════════\n")
    
    print(f"  {'Chord':>12s}  │ {'PW H(E)':>8s} {'PW Var':>8s}  │ {'RW H(E)':>8s} {'RW Var':>8s}  │ {'ΔH(E)':>8s}  {'Theory':>6s}")
    print(f"  {'─'*12}  │ {'─'*8} {'─'*8}  │ {'─'*8} {'─'*8}  │ {'─'*8}  {'─'*6}")
    
    for name in sorted(CHORDS, key=lambda n: chord_pairwise_entropy(CHORDS[n])):
        pw_h = chord_pairwise_entropy(CHORDS[name])
        pw_v = entropy_variance(CHORDS[name])
        rw_h = root_weighted_entropy(CHORDS[name], alpha=alpha)
        rw_v = root_weighted_variance(CHORDS[name], alpha=alpha)
        delta = rw_h - pw_h
        theory = CHORD_CONSONANCE_RANKING.get(name, -1)
        theory_str = f"{theory:.2f}" if theory >= 0 else "  -- "
        
        print(f"  {name:>12s}  │ {pw_h:>8.4f} {pw_v:>8.4f}  │ {rw_h:>8.4f} {rw_v:>8.4f}  │ {delta:>+8.4f}  {theory_str:>6s}")
    
    # Correlations
    ranked = [n for n in CHORDS if n in CHORD_CONSONANCE_RANKING]
    theory_vals = [CHORD_CONSONANCE_RANKING[n] for n in ranked]
    
    pw_cons = [1.0 / (1.0 + chord_pairwise_entropy(CHORDS[n])) for n in ranked]
    rw_cons = [root_weighted_consonance(CHORDS[n], alpha=alpha) for n in ranked]
    
    pw_corr = pearson_correlation(theory_vals, pw_cons)
    rw_corr = pearson_correlation(theory_vals, rw_cons)
    
    print(f"\n  Correlation with music theory rankings:")
    print(f"    Pairwise:      r = {pw_corr:+.4f}")
    print(f"    Root-weighted: r = {rw_corr:+.4f}")
    print(f"    Improvement:   Δr = {rw_corr - pw_corr:+.4f}")


def main():
    print("=" * 80)
    print("  ROOT-WEIGHTED HARMONIC ENTROPY")
    print("  Breaking the Major/Minor Degeneracy")
    print("=" * 80)
    
    # Step 1: Find optimal alpha
    best_alpha = scan_alpha()
    
    # Step 2: Test degeneracy breaking
    test_degeneracy_breaking(alpha=best_alpha)
    
    # Step 3: Full comparison
    full_comparison(alpha=best_alpha)
    
    # Step 4: Re-run progression trajectories
    rerun_progressions(alpha=best_alpha)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"  SUMMARY")
    print(f"{'='*80}\n")
    print(f"  Root-weighted entropy (α={best_alpha}) addresses the pairwise degeneracy")
    print(f"  by weighting bass intervals more heavily — matching how the auditory")
    print(f"  system anchors harmonic perception to the lowest tone.")
    print(f"")
    print(f"  Key question: does the improvement justify the added parameter?")
    print(f"  Or is the degeneracy telling us something deeper — that the difference")
    print(f"  between major and minor isn't about interval entropy at all, but about")
    print(f"  virtual pitch (which note the brain hears as 'the fundamental')?")


if __name__ == '__main__':
    main()
