#!/usr/bin/env python3
"""
🎵 CADENCE TRAJECTORIES — Harmony as paths through transition-entropy space
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Previous work:
- harmonic_entropy.py: r=0.817 with human consonance ratings
- chord_entropy.py: major/minor degeneracy (same intervals → same entropy)
- transition_entropy.py: BROKE the degeneracy (C→IV ≠ Am→IV)
- progression_trajectories.py: triads degenerate, 7th chords work

This module: use TRANSITION entropy (not just static) to build cadence
trajectories. Each step in a progression maps to:
  x = transition entropy (how surprising is this move?)
  y = resolution delta (tension increase or decrease?)
  z = voice-leading entropy (how smooth is the motion?)

Hypothesis: cadence TYPES (authentic, plagal, deceptive, half) have
distinct trajectory signatures. The "grammar" of harmony is a path
grammar in transition-entropy space.

Striker, April 2026
"""

import math
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from transition_entropy import (
    transition_entropy, voice_leading_entropy, resolution_delta,
    chord_harmonic_entropy, DIATONIC_4V
)

# ─── Extended voicings (4-voice, matching transition_entropy.py) ─────

VOICINGS = dict(DIATONIC_4V)  # I, ii, iii, IV, V, vi, vii°

# Add 7th chords
VOICINGS.update({
    'I7':    [0, 4, 7, 11],       # Cmaj7
    'ii7':   [2, 5, 9, 12],       # Dm7
    'iii7':  [4, 7, 11, 14],      # Em7
    'IV7':   [5, 9, 12, 16],      # Fmaj7
    'V7':    [7, 11, 14, 17],     # G7 (dom7)
    'vi7':   [9, 12, 16, 19],     # Am7
    'vii7':  [11, 14, 17, 21],    # Bm7b5
})

# ─── Cadence definitions ────────────────────────────────────────────

CADENCES = {
    # Classical cadences
    'Authentic (V→I)':           ['V', 'I'],
    'Plagal (IV→I)':             ['IV', 'I'],
    'Deceptive (V→vi)':          ['V', 'vi'],
    'Half (I→V)':                ['I', 'V'],
    
    # Extended cadences
    'ii-V-I':                    ['ii', 'V', 'I'],
    'IV-V-I':                    ['IV', 'V', 'I'],
    'vi-IV-V-I':                 ['vi', 'IV', 'V', 'I'],
    'I-vi-IV-V (50s)':           ['I', 'vi', 'IV', 'V'],
    'I-V-vi-IV (Axis)':          ['I', 'V', 'vi', 'IV'],
    'I-IV-V-IV (Rock)':          ['I', 'IV', 'V', 'IV'],
    'I-bVII-IV (Mixolydian)':    ['I', 'V', 'IV'],  # approx
    
    # Jazz cadences (7th chords)
    'ii7-V7-I7 (Jazz)':          ['ii7', 'V7', 'I7'],
    'iii7-vi7-ii7-V7-I7 (Full)': ['iii7', 'vi7', 'ii7', 'V7', 'I7'],
    'I7-vi7-ii7-V7 (Turnaround)':['I7', 'vi7', 'ii7', 'V7'],
    
    # Deceptive extended
    'ii-V-vi (Deceptive jazz)':  ['ii', 'V', 'vi'],
    'IV-V-vi (Deceptive full)':  ['IV', 'V', 'vi'],
}


def cadence_trajectory(chord_names):
    """
    Compute the trajectory of a chord progression through 
    (transition_entropy, resolution_delta, voice_leading_entropy) space.
    
    Returns list of steps, each with transition metrics.
    """
    chords = [VOICINGS[name] for name in chord_names]
    
    steps = []
    for i in range(len(chords) - 1):
        src, dst = chords[i], chords[i+1]
        te = transition_entropy(src, dst)
        rd = resolution_delta(src, dst)
        vle_result = voice_leading_entropy(src, dst)
        vle = vle_result[0] if isinstance(vle_result, tuple) else vle_result
        static_src = chord_harmonic_entropy(src)
        static_dst = chord_harmonic_entropy(dst)
        
        steps.append({
            'from': chord_names[i],
            'to': chord_names[i+1],
            'transition_entropy': te,
            'resolution_delta': rd,
            'voice_leading_entropy': vle,
            'static_entropy_from': static_src,
            'static_entropy_to': static_dst,
        })
    
    return steps


def trajectory_signature(steps):
    """
    Compute summary statistics of a trajectory — the 'fingerprint' of a cadence.
    """
    if not steps:
        return {}
    
    tes = [s['transition_entropy'] for s in steps]
    rds = [s['resolution_delta'] for s in steps]
    vles = [s['voice_leading_entropy'] for s in steps]
    
    return {
        'total_transition_entropy': sum(tes),
        'mean_transition_entropy': sum(tes) / len(tes),
        'max_transition_entropy': max(tes),
        'total_resolution': sum(rds),
        'final_resolution': rds[-1],
        'mean_voice_leading': sum(vles) / len(vles),
        'tension_arc': rds,  # the shape of tension over time
        'n_steps': len(steps),
        # Does it resolve? (final step decreases entropy)
        'resolves': rds[-1] < 0,
        # Is it a "round trip"? (net resolution near zero)
        'circularity': 1.0 / (1.0 + abs(sum(rds))),
        # Entropy momentum: is transition entropy increasing or decreasing?
        'entropy_momentum': tes[-1] - tes[0] if len(tes) > 1 else 0,
    }


def ascii_trajectory(name, steps, width=60, height=15):
    """Draw a trajectory through (transition_entropy, resolution_delta) space."""
    if not steps:
        return
    
    tes = [s['transition_entropy'] for s in steps]
    rds = [s['resolution_delta'] for s in steps]
    
    # Include origin-ish point for context
    all_x = tes
    all_y = rds
    
    x_min, x_max = min(all_x) - 0.1, max(all_x) + 0.1
    y_min, y_max = min(all_y) - 0.05, max(all_y) + 0.05
    
    if x_max - x_min < 0.01:
        x_min -= 0.5
        x_max += 0.5
    if y_max - y_min < 0.01:
        y_min -= 0.2
        y_max += 0.2
    
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    def to_grid(x, y):
        gx = int((x - x_min) / (x_max - x_min) * (width - 1))
        gy = int((1 - (y - y_min) / (y_max - y_min)) * (height - 1))
        return max(0, min(width-1, gx)), max(0, min(height-1, gy))
    
    # Draw zero line if in range
    if y_min <= 0 <= y_max:
        zy = int((1 - (0 - y_min) / (y_max - y_min)) * (height - 1))
        if 0 <= zy < height:
            for x in range(width):
                if grid[zy][x] == ' ':
                    grid[zy][x] = '·'
    
    # Plot points
    for i, (x, y) in enumerate(zip(tes, rds)):
        gx, gy = to_grid(x, y)
        label = str(i + 1)
        grid[gy][gx] = label
    
    # Draw connections
    for i in range(len(tes) - 1):
        gx1, gy1 = to_grid(tes[i], rds[i])
        gx2, gy2 = to_grid(tes[i+1], rds[i+1])
        # Simple line
        n = max(abs(gx2-gx1), abs(gy2-gy1), 1)
        for j in range(1, n):
            px = gx1 + int((gx2-gx1) * j / n)
            py = gy1 + int((gy2-gy1) * j / n)
            if grid[py][px] == ' ' or grid[py][px] == '·':
                grid[py][px] = '─' if abs(gx2-gx1) > abs(gy2-gy1) else '│'
    
    print(f"\n  {name}")
    print(f"  Δ(dissonance) ↑  (+ = more tension)")
    for row in grid:
        print(f"  │{''.join(row)}│")
    print(f"  └{'─'*width}→ Transition Entropy (surprise)")
    
    for i, s in enumerate(steps):
        arrow = "→" if i < len(steps) - 1 else ""
        print(f"    {i+1} = {s['from']}→{s['to']}  "
              f"T(E)={s['transition_entropy']:.3f}  "
              f"Δ={s['resolution_delta']:+.3f}  "
              f"VL={s['voice_leading_entropy']:.3f}")


def main():
    print("=" * 72)
    print("  CADENCE TRAJECTORIES — Harmony as paths through transition space")
    print("=" * 72)
    
    all_sigs = {}
    
    # ── Part 1: Compute all cadence trajectories ──
    print("\n\n" + "─" * 72)
    print("  ALL CADENCE TRAJECTORIES")
    print("─" * 72)
    
    for name, chords in CADENCES.items():
        steps = cadence_trajectory(chords)
        sig = trajectory_signature(steps)
        all_sigs[name] = sig
        
        print(f"\n  {name}: {' → '.join(chords)}")
        for s in steps:
            arrow = "↗" if s['resolution_delta'] > 0.01 else "↘" if s['resolution_delta'] < -0.01 else "→"
            print(f"    {s['from']:>5s} {arrow} {s['to']:<5s}  "
                  f"T(E)={s['transition_entropy']:.3f}  "
                  f"Δ={s['resolution_delta']:+.4f}  "
                  f"VL={s['voice_leading_entropy']:.3f}")
        
        if sig:
            print(f"    Summary: ΣT(E)={sig['total_transition_entropy']:.3f}  "
                  f"ΣΔ={sig['total_resolution']:+.4f}  "
                  f"resolves={'✓' if sig['resolves'] else '✗'}  "
                  f"circ={sig['circularity']:.3f}")
    
    # ── Part 2: Draw interesting trajectories ──
    print("\n\n" + "=" * 72)
    print("  TRAJECTORY VISUALIZATIONS")
    print("=" * 72)
    
    interesting = [
        'ii-V-I',
        'vi-IV-V-I',
        'ii7-V7-I7 (Jazz)',
        'iii7-vi7-ii7-V7-I7 (Full)',
        'Deceptive (V→vi)',
        'Authentic (V→I)',
    ]
    
    for name in interesting:
        if name in CADENCES:
            steps = cadence_trajectory(CADENCES[name])
            ascii_trajectory(name, steps)
    
    # ── Part 3: Classify cadences by trajectory shape ──
    print("\n\n" + "=" * 72)
    print("  CADENCE CLASSIFICATION BY TRAJECTORY")
    print("=" * 72)
    
    # Group by: resolves vs doesn't, high vs low total T(E)
    resolving = {k: v for k, v in all_sigs.items() if v.get('resolves')}
    non_resolving = {k: v for k, v in all_sigs.items() if not v.get('resolves')}
    
    print(f"\n  RESOLVING cadences (final Δ < 0):")
    for name, sig in sorted(resolving.items(), key=lambda x: x[1]['total_resolution']):
        print(f"    {name:40s}  ΣΔ={sig['total_resolution']:+.4f}  "
              f"ΣT(E)={sig['total_transition_entropy']:.3f}")
    
    print(f"\n  NON-RESOLVING cadences (final Δ ≥ 0):")
    for name, sig in sorted(non_resolving.items(), key=lambda x: x[1]['total_resolution']):
        print(f"    {name:40s}  ΣΔ={sig['total_resolution']:+.4f}  "
              f"ΣT(E)={sig['total_transition_entropy']:.3f}")
    
    # ── Part 4: Compare authentic vs deceptive ──
    print("\n\n" + "=" * 72)
    print("  AUTHENTIC vs DECEPTIVE — Same start, different landing")
    print("=" * 72)
    
    auth_steps = cadence_trajectory(['V', 'I'])
    dec_steps = cadence_trajectory(['V', 'vi'])
    
    if auth_steps and dec_steps:
        a, d = auth_steps[0], dec_steps[0]
        print(f"\n  Authentic (V→I):   T(E)={a['transition_entropy']:.4f}  "
              f"Δ={a['resolution_delta']:+.4f}  VL={a['voice_leading_entropy']:.4f}")
        print(f"  Deceptive (V→vi):  T(E)={d['transition_entropy']:.4f}  "
              f"Δ={d['resolution_delta']:+.4f}  VL={d['voice_leading_entropy']:.4f}")
        
        te_ratio = d['transition_entropy'] / a['transition_entropy'] if a['transition_entropy'] > 0 else float('inf')
        print(f"\n  Deceptive/Authentic T(E) ratio: {te_ratio:.3f}")
        if te_ratio > 1:
            print(f"  ✅ Deceptive cadence IS more surprising (higher T(E))")
        else:
            print(f"  Deceptive cadence is NOT more surprising")
        
        if d['resolution_delta'] > a['resolution_delta']:
            print(f"  ✅ Deceptive cadence INCREASES tension more (or resolves less)")
    
    # ── Part 5: Jazz vs Classical trajectory comparison ──
    print("\n\n" + "=" * 72)
    print("  JAZZ vs CLASSICAL — 7th chords vs triads on same progressions")
    print("=" * 72)
    
    pairs = [
        ('ii-V-I', ['ii', 'V', 'I'], 'ii7-V7-I7 (Jazz)', ['ii7', 'V7', 'I7']),
    ]
    
    for classical_name, classical_chords, jazz_name, jazz_chords in pairs:
        c_steps = cadence_trajectory(classical_chords)
        j_steps = cadence_trajectory(jazz_chords)
        c_sig = trajectory_signature(c_steps)
        j_sig = trajectory_signature(j_steps)
        
        print(f"\n  {classical_name} (triads) vs {jazz_name} (7ths):")
        print(f"    {'Metric':<30s}  {'Classical':>10s}  {'Jazz':>10s}  {'Δ':>10s}")
        print(f"    {'─'*65}")
        
        for metric in ['total_transition_entropy', 'total_resolution', 
                       'mean_voice_leading', 'circularity']:
            cv = c_sig.get(metric, 0)
            jv = j_sig.get(metric, 0)
            label = metric.replace('_', ' ').title()
            print(f"    {label:<30s}  {cv:>10.4f}  {jv:>10.4f}  {jv-cv:>+10.4f}")
    
    # ── Part 6: Summary ──
    print("\n\n" + "=" * 72)
    print("  KEY FINDINGS")
    print("=" * 72)
    
    # Highest surprise cadence
    max_te = max(all_sigs.items(), key=lambda x: x[1].get('total_transition_entropy', 0))
    print(f"\n  Most surprising progression: {max_te[0]}")
    print(f"    Total T(E) = {max_te[1]['total_transition_entropy']:.4f}")
    
    # Best resolving
    best_resolve = min(all_sigs.items(), key=lambda x: x[1].get('total_resolution', 0))
    print(f"\n  Strongest resolution: {best_resolve[0]}")
    print(f"    ΣΔ = {best_resolve[1]['total_resolution']:+.4f}")
    
    # Most circular
    most_circ = max(all_sigs.items(), key=lambda x: x[1].get('circularity', 0))
    print(f"\n  Most circular: {most_circ[0]}")
    print(f"    Circularity = {most_circ[1]['circularity']:.4f}")
    
    # Does the resolves/non-resolves classification match musical intuition?
    print(f"\n  Classification accuracy:")
    expected_resolve = ['Authentic (V→I)', 'Plagal (IV→I)', 'ii-V-I', 'IV-V-I',
                       'vi-IV-V-I', 'ii7-V7-I7 (Jazz)', 'iii7-vi7-ii7-V7-I7 (Full)']
    expected_non = ['Deceptive (V→vi)', 'Half (I→V)', 'ii-V-vi (Deceptive jazz)',
                    'IV-V-vi (Deceptive full)']
    
    correct = 0
    total = 0
    for name in expected_resolve:
        if name in all_sigs:
            total += 1
            if all_sigs[name].get('resolves'):
                correct += 1
                print(f"    ✅ {name}: correctly classified as resolving")
            else:
                print(f"    ❌ {name}: expected resolving, got non-resolving")
    
    for name in expected_non:
        if name in all_sigs:
            total += 1
            if not all_sigs[name].get('resolves'):
                correct += 1
                print(f"    ✅ {name}: correctly classified as non-resolving")
            else:
                print(f"    ❌ {name}: expected non-resolving, got resolving")
    
    if total > 0:
        acc = correct / total
        print(f"\n  Accuracy: {correct}/{total} = {acc:.0%}")
        if acc > 0.7:
            print(f"  ✅ Transition entropy trajectory PREDICTS cadence function!")
        else:
            print(f"  ⚠️  Transition entropy has limited cadence prediction power")


if __name__ == "__main__":
    main()
