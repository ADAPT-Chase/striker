#!/usr/bin/env python3
"""
🎵 TRANSITION ENTROPY — Harmonic function from entropy dynamics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The problem: static chord entropy can't distinguish major from minor
(same intervals → same entropy). And all diatonic triads in close
position have similar entropy profiles.

The insight (from emergence-sim): "Function lives in transitions, 
not states."

This module measures:
1. TRANSITION ENTROPY — entropy of the interval changes between 
   consecutive chords. High = the harmonic move is surprising.
   
2. VOICE-LEADING ENTROPY — entropy of the semitone distances each 
   voice moves. Smooth voice leading = low entropy.
   
3. RESOLUTION TENDENCY — does a chord transition reduce or increase
   total dissonance? Measured as Δ(harmonic entropy).

4. FUNCTIONAL FINGERPRINT — a chord's role (tonic/subdominant/dominant)
   should be identifiable from its transition statistics, not its 
   static properties.
"""

import math
import itertools
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional

# Import from existing modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from harmonic_entropy import harmonic_entropy
from chord_entropy import chord_pairwise_entropy, entropy_variance


# ─── Chord definitions ────────────────────────────────────────────

# Diatonic chords in C major with specific voicings (semitones from C3=0)
# Using 4-voice close position for voice-leading analysis
DIATONIC_4V = {
    'I':    [0, 4, 7, 12],      # C E G C
    'ii':   [2, 5, 9, 14],      # D F A D
    'iii':  [4, 7, 11, 16],     # E G B E
    'IV':   [5, 9, 12, 17],     # F A C F
    'V':    [7, 11, 14, 19],    # G B D G
    'vi':   [9, 12, 16, 21],    # A C E A
    'viio': [11, 14, 17, 23],   # B D F B
}

# 7th chords
SEVENTH_CHORDS = {
    'Imaj7':  [0, 4, 7, 11],    # C E G B
    'ii7':    [2, 5, 9, 12],    # D F A C
    'iii7':   [4, 7, 11, 14],   # E G B D
    'IVmaj7': [5, 9, 12, 16],   # F A C E
    'V7':     [7, 11, 14, 17],  # G B D F
    'vi7':    [9, 12, 16, 19],  # A C E G
    'viio7':  [11, 14, 17, 21], # B D F A (half-dim)
}

# Standard progressions for testing
PROGRESSIONS = {
    'I-IV-V-I':     ['I', 'IV', 'V', 'I'],
    'I-V-vi-IV':    ['I', 'V', 'vi', 'IV'],          # pop
    'I-vi-IV-V':    ['I', 'vi', 'IV', 'V'],          # 50s
    'ii-V-I':       ['ii', 'V', 'I'],                 # jazz
    'I-IV-vi-V':    ['I', 'IV', 'vi', 'V'],
    'vi-IV-I-V':    ['vi', 'IV', 'I', 'V'],           # Axis
    'I-V-I':        ['I', 'V', 'I'],                   # authentic cadence
    'IV-I':         ['IV', 'I'],                        # plagal
    'V-vi':         ['V', 'vi'],                        # deceptive
    'I-iii-vi-ii-V-I': ['I', 'iii', 'vi', 'ii', 'V', 'I'],  # circle of fifths
}


def ratio_from_semitones(semitones: float) -> float:
    """Convert semitone interval to frequency ratio."""
    return 2 ** (semitones / 12)


def chord_harmonic_entropy(chord: List[int]) -> float:
    """Total harmonic entropy of a chord (sum of pairwise)."""
    total = 0
    for i in range(len(chord)):
        for j in range(i+1, len(chord)):
            interval = abs(chord[j] - chord[i])
            ratio = ratio_from_semitones(interval)
            total += harmonic_entropy(ratio)
    return total


def transition_entropy(chord_a: List[int], chord_b: List[int]) -> float:
    """
    Entropy of the transition between two chords.
    
    Combines two signals:
    1. INTERVAL CHANGE: how do pairwise intervals change? (captures quality shifts)
    2. PITCH MOTION: how does each voice move? (captures root movement)
    
    Both are necessary because octave-doubled triads of the same quality
    have identical interval sets — only pitch motion distinguishes I→IV from I→V.
    """
    # Part 1: Interval changes (captures quality shifts: major→minor etc.)
    def pairwise_intervals(chord):
        intervals = []
        for i in range(len(chord)):
            for j in range(i+1, len(chord)):
                intervals.append(chord[j] - chord[i])
        return sorted(intervals)
    
    intervals_a = pairwise_intervals(chord_a)
    intervals_b = pairwise_intervals(chord_b)
    
    n = max(len(intervals_a), len(intervals_b))
    while len(intervals_a) < n: intervals_a.append(0)
    while len(intervals_b) < n: intervals_b.append(0)
    
    interval_deltas = [intervals_b[i] - intervals_a[i] for i in range(n)]
    
    # Part 2: Pitch motion (captures root movement)
    m = min(len(chord_a), len(chord_b))
    pitch_motions = [chord_b[i] - chord_a[i] for i in range(m)]
    
    # Combine both signals
    all_features = interval_deltas + pitch_motions
    
    feature_counts = Counter(all_features)
    total = len(all_features)
    if total == 0:
        return 0.0
    
    probs = [c / total for c in feature_counts.values()]
    h = -sum(p * math.log2(p) for p in probs if p > 0)
    
    return h


def voice_leading_entropy(chord_a: List[int], chord_b: List[int]) -> float:
    """
    Entropy of voice-leading motion.
    
    For matched voices (same index), measures the distribution of 
    semitone movements. Low entropy = all voices move similarly 
    (parallel motion). High entropy = voices move independently.
    
    Returns (entropy, mean_distance, max_distance)
    """
    n = min(len(chord_a), len(chord_b))
    movements = [chord_b[i] - chord_a[i] for i in range(n)]
    
    # Entropy of movement distribution
    move_counts = Counter(movements)
    total = len(movements)
    if total == 0:
        return 0.0, 0.0, 0.0
    
    probs = [c / total for c in move_counts.values()]
    h = -sum(p * math.log2(p) for p in probs if p > 0)
    
    # Voice leading efficiency
    mean_dist = sum(abs(m) for m in movements) / len(movements)
    max_dist = max(abs(m) for m in movements)
    
    return h, mean_dist, max_dist


def resolution_delta(chord_a: List[int], chord_b: List[int]) -> float:
    """
    Change in total harmonic entropy: H(chord_b) - H(chord_a).
    Negative = resolution (moves toward consonance).
    Positive = tensioning (moves toward dissonance).
    """
    return chord_harmonic_entropy(chord_b) - chord_harmonic_entropy(chord_a)


def functional_fingerprint(chord_name: str, all_chords: Dict[str, List[int]], 
                           progressions: Dict[str, List[str]]) -> Dict:
    """
    Build a chord's functional fingerprint from how it behaves in transitions.
    
    For each chord, compute:
    - Mean transition entropy when this chord is the SOURCE
    - Mean transition entropy when this chord is the TARGET
    - Mean resolution delta when departing
    - Mean resolution delta when arriving
    - Most common predecessor/successor
    """
    if chord_name not in all_chords:
        return {}
    
    source_transitions = []
    target_transitions = []
    source_deltas = []
    target_deltas = []
    predecessors = []
    successors = []
    
    for prog_name, prog in progressions.items():
        for i in range(len(prog)):
            if prog[i] == chord_name:
                # This chord as source
                if i + 1 < len(prog) and prog[i+1] in all_chords:
                    next_chord = prog[i+1]
                    te = transition_entropy(all_chords[chord_name], all_chords[next_chord])
                    rd = resolution_delta(all_chords[chord_name], all_chords[next_chord])
                    source_transitions.append(te)
                    source_deltas.append(rd)
                    successors.append(next_chord)
                
                # This chord as target
                if i > 0 and prog[i-1] in all_chords:
                    prev_chord = prog[i-1]
                    te = transition_entropy(all_chords[prev_chord], all_chords[chord_name])
                    rd = resolution_delta(all_chords[prev_chord], all_chords[chord_name])
                    target_transitions.append(te)
                    target_deltas.append(rd)
                    predecessors.append(prev_chord)
    
    def safe_mean(lst):
        return sum(lst) / len(lst) if lst else 0
    
    def mode(lst):
        if not lst: return None
        return Counter(lst).most_common(1)[0][0]
    
    return {
        "chord": chord_name,
        "mean_source_transition_entropy": round(safe_mean(source_transitions), 4),
        "mean_target_transition_entropy": round(safe_mean(target_transitions), 4),
        "mean_departure_delta": round(safe_mean(source_deltas), 4),
        "mean_arrival_delta": round(safe_mean(target_deltas), 4),
        "most_common_successor": mode(successors),
        "most_common_predecessor": mode(predecessors),
        "n_appearances": len(source_transitions) + len(target_transitions),
    }


def analyze_progression(prog_names: List[str], chords: Dict[str, List[int]], 
                        label: str = "") -> Dict:
    """Full transition analysis of a chord progression."""
    print(f"\n  {'─'*56}")
    print(f"  {label}: {' → '.join(prog_names)}")
    print(f"  {'─'*56}")
    
    results = {
        "progression": prog_names,
        "transitions": [],
        "total_transition_entropy": 0,
        "total_resolution": 0,
        "path_length": 0,
    }
    
    for i in range(len(prog_names) - 1):
        name_a = prog_names[i]
        name_b = prog_names[i+1]
        
        if name_a not in chords or name_b not in chords:
            continue
        
        chord_a = chords[name_a]
        chord_b = chords[name_b]
        
        te = transition_entropy(chord_a, chord_b)
        vle, vl_mean, vl_max = voice_leading_entropy(chord_a, chord_b)
        rd = resolution_delta(chord_a, chord_b)
        he_a = chord_harmonic_entropy(chord_a)
        he_b = chord_harmonic_entropy(chord_b)
        
        transition = {
            "from": name_a,
            "to": name_b,
            "transition_entropy": round(te, 4),
            "voice_leading_entropy": round(vle, 4),
            "voice_leading_distance": round(vl_mean, 2),
            "resolution_delta": round(rd, 4),
            "source_entropy": round(he_a, 4),
            "target_entropy": round(he_b, 4),
        }
        results["transitions"].append(transition)
        results["total_transition_entropy"] += te
        results["total_resolution"] += rd
        results["path_length"] += abs(rd)
        
        direction = "↓ resolve" if rd < 0 else "↑ tension" if rd > 0 else "= static"
        print(f"    {name_a:>5s} → {name_b:<5s}  "
              f"T(E)={te:.3f}  VL(E)={vle:.3f}  "
              f"Δ={rd:+.3f} {direction}  "
              f"VL dist={vl_mean:.1f}")
    
    results["total_transition_entropy"] = round(results["total_transition_entropy"], 4)
    results["total_resolution"] = round(results["total_resolution"], 4)
    results["path_length"] = round(results["path_length"], 4)
    
    net = results["total_resolution"]
    print(f"\n    Net resolution: {net:+.3f} {'(resolves)' if net < 0 else '(tensions)' if net > 0 else '(neutral)'}")
    print(f"    Total transition entropy: {results['total_transition_entropy']:.3f}")
    print(f"    Path length: {results['path_length']:.3f}")
    
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("  🎵 TRANSITION ENTROPY ANALYSIS")
    print("  Function lives in transitions, not states.")
    print("=" * 60)
    
    # ── Part 1: Analyze standard progressions ──
    print("\n" + "=" * 60)
    print("  PART 1: Diatonic Progressions (4-voice)")
    print("=" * 60)
    
    prog_results = {}
    for name, prog in PROGRESSIONS.items():
        prog_results[name] = analyze_progression(prog, DIATONIC_4V, label=name)
    
    # ── Part 2: Compare cadence types ──
    print("\n\n" + "=" * 60)
    print("  PART 2: Cadence Comparison")
    print("=" * 60)
    
    cadences = {
        "Authentic (V→I)":  ['V', 'I'],
        "Plagal (IV→I)":    ['IV', 'I'],
        "Deceptive (V→vi)": ['V', 'vi'],
        "Half (I→V)":       ['I', 'V'],
    }
    
    for name, prog in cadences.items():
        chord_a = DIATONIC_4V[prog[0]]
        chord_b = DIATONIC_4V[prog[1]]
        te = transition_entropy(chord_a, chord_b)
        rd = resolution_delta(chord_a, chord_b)
        vle, vl_mean, _ = voice_leading_entropy(chord_a, chord_b)
        
        print(f"\n  {name:25s}  T(E)={te:.3f}  Δ={rd:+.3f}  VL={vl_mean:.1f}")
    
    # ── Part 3: Functional fingerprints ──
    print("\n\n" + "=" * 60)
    print("  PART 3: Functional Fingerprints")
    print("  Can we identify tonic/subdominant/dominant from transitions?")
    print("=" * 60)
    
    # Expected functions: I=tonic, IV=subdominant, V=dominant
    expected = {'I': 'tonic', 'ii': 'pre-dom', 'iii': 'tonic-sub',
                'IV': 'subdominant', 'V': 'dominant', 'vi': 'tonic-sub', 
                'viio': 'dominant'}
    
    fingerprints = {}
    for chord_name in DIATONIC_4V:
        fp = functional_fingerprint(chord_name, DIATONIC_4V, PROGRESSIONS)
        fingerprints[chord_name] = fp
        if fp:
            print(f"\n  {chord_name:>5s} ({expected.get(chord_name, '?'):12s}): "
                  f"source T(E)={fp['mean_source_transition_entropy']:.3f}  "
                  f"target T(E)={fp['mean_target_transition_entropy']:.3f}  "
                  f"depart Δ={fp['mean_departure_delta']:+.3f}  "
                  f"arrive Δ={fp['mean_arrival_delta']:+.3f}")
            if fp['most_common_successor']:
                print(f"        Most goes to: {fp['most_common_successor']}, "
                      f"Most comes from: {fp['most_common_predecessor']}")
    
    # ── Part 4: Can transition entropy distinguish what static entropy can't? ──
    print("\n\n" + "=" * 60)
    print("  PART 4: Breaking the Major/Minor Degeneracy")
    print("  Static entropy: C major = A minor (same intervals)")  
    print("  Transition entropy: different because they MOVE differently")
    print("=" * 60)
    
    # C major and A minor have the same static entropy
    C_major = [0, 4, 7, 12]
    A_minor = [9, 12, 16, 21]
    
    static_C = chord_harmonic_entropy(C_major)
    static_Am = chord_harmonic_entropy(A_minor)
    print(f"\n  Static H(E): C={static_C:.4f}  Am={static_Am:.4f}  "
          f"{'SAME' if abs(static_C - static_Am) < 0.01 else 'different'}")
    
    # But they transition differently to the same targets
    targets = {'IV': [5, 9, 12, 17], 'V': [7, 11, 14, 19], 'vi': [9, 12, 16, 21]}
    
    print(f"\n  Transitions FROM C major vs A minor:")
    for target_name, target_chord in targets.items():
        te_from_C = transition_entropy(C_major, target_chord)
        te_from_Am = transition_entropy(A_minor, target_chord)
        rd_from_C = resolution_delta(C_major, target_chord)
        rd_from_Am = resolution_delta(A_minor, target_chord)
        
        print(f"    → {target_name:5s}: C: T(E)={te_from_C:.3f} Δ={rd_from_C:+.3f}  "
              f"Am: T(E)={te_from_Am:.3f} Δ={rd_from_Am:+.3f}  "
              f"{'✅ DIFFERENT' if abs(te_from_C - te_from_Am) > 0.01 or abs(rd_from_C - rd_from_Am) > 0.01 else '❌ same'}")
    
    # ── Part 5: Summary statistics ──
    print("\n\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    # Rank progressions by total transition entropy
    ranked = sorted(prog_results.items(), key=lambda x: x[1]['total_transition_entropy'], reverse=True)
    print("\n  Progressions ranked by total transition entropy:")
    for name, r in ranked:
        print(f"    {name:25s}: T(E)={r['total_transition_entropy']:.3f}  "
              f"Net Δ={r['total_resolution']:+.3f}  "
              f"Path={r['path_length']:.3f}")
    
    # Key finding
    print(f"\n  {'─'*56}")
    print(f"  KEY FINDINGS:")
    
    # Check if transition entropy varies more than static entropy
    static_entropies = [chord_harmonic_entropy(c) for c in DIATONIC_4V.values()]
    static_range = max(static_entropies) - min(static_entropies)
    
    transition_entropies = []
    for name, r in prog_results.items():
        for t in r['transitions']:
            transition_entropies.append(t['transition_entropy'])
    
    if transition_entropies:
        trans_range = max(transition_entropies) - min(transition_entropies)
        print(f"\n  Static entropy range:     {static_range:.4f}")
        print(f"  Transition entropy range: {trans_range:.4f}")
        if trans_range > static_range:
            print(f"  ✅ Transitions have MORE variation than static chords")
            print(f"     → Function IS more visible in transitions than states")
        else:
            print(f"  ❌ Static chords vary more than transitions")
    
    # Does departure delta predict function?
    print(f"\n  Functional prediction from departure Δ:")
    for chord_name in ['I', 'IV', 'V']:
        fp = fingerprints.get(chord_name, {})
        if fp:
            dep = fp['mean_departure_delta']
            label = expected[chord_name]
            print(f"    {chord_name:>3s} ({label:12s}): depart Δ = {dep:+.4f}")
    
    print(f"\n  (Tonic should depart ↑, Dominant should depart ↓)")
