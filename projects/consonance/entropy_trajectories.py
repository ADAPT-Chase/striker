#!/usr/bin/env python3
"""
🌊 ENTROPY TRAJECTORIES — Harmonic progressions as dynamical systems
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The bridge between consonance and entropy-edge.

Core insight: a chord progression is a temporal signal. Each chord is a
state, each transition is an event. We can measure the same triple-point
axes (memory, transport, transformation) that classify cellular automata —
but applied to MUSIC.

MEMORY: Does a progression reference its own history?
  - Chord recurrence (I shows up at start AND end of I-V-I)
  - Tonal center persistence (gravity toward tonic across transitions)
  - Harmonic rhythm patterns (regular vs irregular chord changes)

TRANSPORT: Does harmonic information propagate through time?
  - Voice-leading threads (a note moves stepwise across multiple chords)
  - Tension accumulation (each chord builds on the last's tension)
  - Key modulation (tonal center shifts smoothly)

TRANSFORMATION: Does the progression create something new?
  - Expectation violation (deceptive cadence = V→vi instead of V→I)
  - Schema breaking (familiar pattern altered)
  - Harmonic surprise (high transition entropy at key moments)

A great piece of music lives at the TRIPLE POINT of all three.
A boring loop has memory but no transformation.
A random sequence has surprise but no memory.
A sequence of unrelated cadences has transformation but no transport.

This is the hypothesis: the triple-point metric from cellular automata
applies to harmony because music IS computation on emotion.

Striker, April 2026
"""

import math
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from harmonic_entropy import harmonic_entropy
from chord_entropy import chord_pairwise_entropy, entropy_variance
from transition_entropy import (
    transition_entropy, voice_leading_entropy, resolution_delta,
    chord_harmonic_entropy, DIATONIC_4V
)
from tonal_gravity import tonal_resolution, chord_gravity, VOICINGS as TG_VOICINGS
from expectation_layer import implication_strength, IMPLICATIONS


# ═══════════════════════════════════════════════════════════════════
# VOICINGS
# ═══════════════════════════════════════════════════════════════════

VOICINGS = dict(TG_VOICINGS)
VOICINGS.update({
    'bVII': [10, 14, 17, 22],
    'bVI':  [8, 12, 15, 20],
    'bIII': [3, 7, 10, 15],
    'v':    [7, 10, 14, 19],
    'iv':   [5, 8, 12, 17],
    'i':    [0, 3, 7, 12],
    'I7':   [0, 4, 7, 11],
    'ii7':  [2, 5, 9, 12],
    'V7':   [7, 11, 14, 17],
    'vi7':  [9, 12, 16, 19],
})


# ═══════════════════════════════════════════════════════════════════
# AXIS 1: MEMORY — Does the progression remember itself?
# ═══════════════════════════════════════════════════════════════════

def harmonic_memory(chords: List[str]) -> float:
    """
    Measure how much a progression references its own history.
    
    Three components:
    1. Recurrence — how often chords repeat (range [0, 1])
    2. Tonal persistence — does gravity stay oriented? (range [0, 1]) 
    3. Rhythmic regularity — is the entropy profile periodic? (range [0, 1])
    
    Returns: combined memory score [0, 1]
    """
    if len(chords) < 2:
        return 0.0
    
    # 1. Recurrence: fraction of chords that appeared earlier
    # BUT penalize trivial repetition (all same chord)
    seen = set()
    recurrences = 0
    for i, c in enumerate(chords):
        if c in seen:
            recurrences += 1
        seen.add(c)
    recurrence = recurrences / (len(chords) - 1) if len(chords) > 1 else 0
    
    # Penalize trivial repetition: if vocabulary is 1 chord, recurrence is noise
    unique_ratio = len(set(chords)) / len(chords)
    if unique_ratio < 0.3:  # Nearly all the same chord
        recurrence *= 0.1  # Crush it — this isn't memory, it's stasis
    
    # 2. Tonal persistence: autocorrelation of gravity values
    # Only meaningful when there's actual movement
    if all(c in VOICINGS for c in chords):
        gravities = [chord_gravity(VOICINGS[c]) for c in chords]
        # Check if gravity actually varies
        grav_var = max(gravities) - min(gravities)
        if grav_var < 0.01:
            tonal_persist = 0.0  # No variation = no tonal memory signal
        else:
            tonal_persist = _autocorrelation(gravities)
    else:
        tonal_persist = 0.0
    
    # 3. Functional memory: does the progression reference related chords?
    # Not literal repetition but FUNCTIONAL recurrence (ii and IV are both subdominant)
    FUNCTION_GROUPS = {
        'tonic': {'I', 'i', 'iii', 'III', 'vi'},
        'subdominant': {'ii', 'IV', 'iv', 'ii7'},
        'dominant': {'V', 'V7', 'viio', 'vii7'},
    }
    chord_to_func = {}
    for func, members in FUNCTION_GROUPS.items():
        for m in members:
            chord_to_func[m] = func
    
    func_sequence = [chord_to_func.get(c, c) for c in chords]
    seen_funcs = set()
    func_recurrences = 0
    for f in func_sequence:
        if f in seen_funcs:
            func_recurrences += 1
        seen_funcs.add(f)
    func_memory = func_recurrences / (len(func_sequence) - 1) if len(func_sequence) > 1 else 0
    
    # 4. Rhythmic regularity: periodicity of transition entropy
    if len(chords) >= 4 and all(c in VOICINGS for c in chords):
        trans_entropies = []
        for i in range(len(chords) - 1):
            te = transition_entropy(VOICINGS[chords[i]], VOICINGS[chords[i+1]])
            trans_entropies.append(te)
        rhythmic = _periodicity(trans_entropies)
    else:
        rhythmic = 0.0
    
    # Weight: functional memory most important, then recurrence, tonal, rhythmic
    return 0.3 * recurrence + 0.3 * func_memory + 0.25 * tonal_persist + 0.15 * rhythmic


def _autocorrelation(values: List[float], lag: int = 1) -> float:
    """Normalized autocorrelation at given lag. Returns [0, 1]."""
    if len(values) < lag + 2:
        return 0.0
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    if var < 1e-10:
        return 1.0  # Constant signal = perfect memory
    
    covar = sum((values[i] - mean) * (values[i + lag] - mean) 
                for i in range(n - lag)) / (n - lag)
    r = covar / var
    return max(0, r)  # Clamp negative correlations to 0


def _periodicity(values: List[float]) -> float:
    """Detect periodicity via max autocorrelation at any lag > 0."""
    if len(values) < 4:
        return 0.0
    max_lag = len(values) // 2
    best = 0.0
    for lag in range(1, max_lag + 1):
        r = _autocorrelation(values, lag)
        best = max(best, r)
    return best


# ═══════════════════════════════════════════════════════════════════
# AXIS 2: TRANSPORT — Does harmonic information propagate?
# ═══════════════════════════════════════════════════════════════════

def harmonic_transport(chords: List[str]) -> float:
    """
    Measure information propagation through the progression.
    
    Three components:
    1. Voice-leading continuity — do notes connect across boundaries?
    2. Tension propagation — does tension build and release coherently?
    3. Gravity trajectory coherence — smooth path through gravity space?
    
    Returns: transport score [0, 1]
    """
    if len(chords) < 2 or not all(c in VOICINGS for c in chords):
        return 0.0
    
    # 1. Voice-leading continuity: small, consistent motion
    # BUT zero motion = no transport (nothing is being carried)
    vl_scores = []
    for i in range(len(chords) - 1):
        _, mean_dist, max_dist = voice_leading_entropy(
            VOICINGS[chords[i]], VOICINGS[chords[i+1]]
        )
        if mean_dist < 0.01:
            # No movement at all — this isn't "good voice leading", it's stasis
            vl_scores.append(0.0)
        else:
            # Good voice leading: small but nonzero distance
            # Sweet spot around 1-3 semitones. Too much = jumpy, zero = static.
            efficiency = max(0, 1 - mean_dist / 12)
            vl_scores.append(efficiency)
    vl_continuity = sum(vl_scores) / len(vl_scores) if vl_scores else 0
    
    # 2. Tension propagation: monotonic tension build or release
    gravities = [chord_gravity(VOICINGS[c]) for c in chords]
    deltas = [gravities[i+1] - gravities[i] for i in range(len(gravities)-1)]
    
    if len(deltas) < 2:
        tension_prop = 0.5
    else:
        # Coherent tension = consistent sign of deltas (building or releasing)
        # Look at consecutive delta signs
        sign_consistency = 0
        for i in range(len(deltas) - 1):
            if deltas[i] * deltas[i+1] > 0:  # Same direction
                sign_consistency += 1
        tension_prop = sign_consistency / (len(deltas) - 1) if len(deltas) > 1 else 0
    
    # 3. Gravity trajectory smoothness
    if len(gravities) >= 3:
        # Second derivative of gravity (jerk) — smooth path = low jerk
        second_derivs = [gravities[i+2] - 2*gravities[i+1] + gravities[i] 
                        for i in range(len(gravities) - 2)]
        mean_jerk = sum(abs(d) for d in second_derivs) / len(second_derivs)
        # Normalize: 0 jerk = perfectly smooth, 2+ = chaotic
        smoothness = max(0, 1 - mean_jerk / 2)
    else:
        smoothness = 0.5
    
    return 0.4 * vl_continuity + 0.35 * tension_prop + 0.25 * smoothness


# ═══════════════════════════════════════════════════════════════════
# AXIS 3: TRANSFORMATION — Does the progression create surprise?
# ═══════════════════════════════════════════════════════════════════

def harmonic_transformation(chords: List[str]) -> float:
    """
    Measure genuine surprise/novelty in the progression.
    
    Three components:
    1. Transition surprise — high transition entropy moments
    2. Expectation violation — departures from implied continuations
    3. Harmonic vocabulary — ratio of unique chords to total
    
    Returns: transformation score [0, 1]
    """
    if len(chords) < 2 or not all(c in VOICINGS for c in chords):
        return 0.0
    
    # 1. Transition surprise: mean transition entropy (normalized)
    trans_entropies = []
    for i in range(len(chords) - 1):
        te = transition_entropy(VOICINGS[chords[i]], VOICINGS[chords[i+1]])
        trans_entropies.append(te)
    # Normalize: typical transition entropy range is [0.5, 3.0]
    mean_te = sum(trans_entropies) / len(trans_entropies)
    surprise = min(1.0, mean_te / 3.0)
    
    # 2. Expectation violation: do transitions go where we expect?
    violations = 0
    total_implications = 0
    for i in range(len(chords) - 1):
        strength, target = implication_strength(chords[i])
        if strength > 0.1:  # This chord implies something
            total_implications += 1
            actual_next = chords[i+1]
            # Check if actual matches implied target
            impl_dict = IMPLICATIONS.get(chords[i], {})
            match_strength = impl_dict.get(actual_next, 0.0)
            if match_strength < 0.3:  # Went somewhere unexpected
                violations += 1
    
    if total_implications > 0:
        violation_rate = violations / total_implications
    else:
        # No known implications — moderate surprise
        violation_rate = 0.5
    
    # 3. Harmonic vocabulary richness
    unique = len(set(chords))
    total = len(chords)
    vocabulary = unique / total  # 1.0 = all unique, low = repetitive
    
    return 0.4 * surprise + 0.35 * violation_rate + 0.25 * vocabulary


# ═══════════════════════════════════════════════════════════════════
# TRIPLE POINT — The conjunction
# ═══════════════════════════════════════════════════════════════════

def triple_point_score(memory: float, transport: float, 
                       transformation: float) -> float:
    """
    Triple-point distance: geometric mean of all three axes.
    
    Geometric mean rewards BALANCE — all three must be non-trivial.
    A boring loop (memory=1, transport=0, transform=0) scores 0.
    A random walk (memory=0, transport=0, transform=1) scores 0.
    Great music (memory=0.7, transport=0.8, transform=0.6) scores ~0.7.
    """
    return (memory * transport * transformation) ** (1/3)


def analyze_trajectory(chords: List[str], label: str = "") -> Dict:
    """
    Full triple-point analysis of a chord progression.
    
    Returns dict with all three axes, triple-point score,
    per-transition details, and trajectory classification.
    """
    mem = harmonic_memory(chords)
    trans = harmonic_transport(chords)
    transform = harmonic_transformation(chords)
    tp = triple_point_score(mem, trans, transform)
    
    # Per-transition entropy trajectory
    transitions = []
    if all(c in VOICINGS for c in chords):
        for i in range(len(chords) - 1):
            a, b = VOICINGS[chords[i]], VOICINGS[chords[i+1]]
            te = transition_entropy(a, b)
            rd = resolution_delta(a, b)
            vle, vl_mean, _ = voice_leading_entropy(a, b)
            grav = chord_gravity(b)
            transitions.append({
                'from': chords[i],
                'to': chords[i+1],
                'transition_entropy': round(te, 4),
                'resolution_delta': round(rd, 4),
                'voice_leading_dist': round(vl_mean, 2),
                'gravity': round(grav, 4),
            })
    
    # Classify the trajectory
    classification = classify_trajectory(mem, trans, transform)
    
    return {
        'label': label,
        'chords': chords,
        'memory': round(mem, 4),
        'transport': round(trans, 4),
        'transformation': round(transform, 4),
        'triple_point': round(tp, 4),
        'classification': classification,
        'transitions': transitions,
    }


def classify_trajectory(mem: float, trans: float, transform: float) -> str:
    """
    Classify a progression by its triple-point profile.
    
    Like Wolfram classes for cellular automata:
    - Class 1 (fixed): High memory, low transport, low transform → LOOP
    - Class 2 (periodic): High memory, high transport, low transform → CYCLE
    - Class 3 (chaotic): Low memory, low transport, high transform → RANDOM
    - Class 4 (complex): All three balanced and non-trivial → MUSIC
    """
    tp = triple_point_score(mem, trans, transform)
    
    # Check for degenerate cases first
    if max(mem, trans, transform) < 0.15:
        return "STATIC"  # Nothing happening
    
    # Which axis dominates?
    axes = {'memory': mem, 'transport': trans, 'transformation': transform}
    dominant = max(axes, key=axes.get)
    dominant_val = axes[dominant]
    others = [v for k, v in axes.items() if k != dominant]
    mean_others = sum(others) / 2
    
    # Strong imbalance = degenerate
    if dominant_val > 0.5 and mean_others < 0.2:
        if dominant == 'memory':
            return "LOOP"  # Repeats without going anywhere
        elif dominant == 'transport':
            return "DRIFT"  # Moves but doesn't surprise or repeat
        else:
            return "RANDOM"  # Surprises but doesn't cohere
    
    # Two axes strong, one weak
    if mem > 0.3 and trans > 0.3 and transform < 0.15:
        return "CYCLE"  # Periodic pattern
    if mem > 0.3 and transform > 0.3 and trans < 0.15:
        return "RIFF"  # Repeated surprise (like a hook)
    if trans > 0.3 and transform > 0.3 and mem < 0.15:
        return "JOURNEY"  # Goes somewhere new, doesn't return
    
    # All three present
    if tp > 0.4:
        return "MUSIC"  # The triple point — all three balanced
    elif tp > 0.25:
        return "DEVELOPING"  # Getting there
    else:
        return "SPARSE"  # Present but weak


# ═══════════════════════════════════════════════════════════════════
# TEST SUITE
# ═══════════════════════════════════════════════════════════════════

PROGRESSIONS = {
    # Boring loops (should be LOOP or CYCLE)
    'I-I-I-I': ['I', 'I', 'I', 'I'],
    'I-V-I-V': ['I', 'V', 'I', 'V'],
    
    # Simple cadences (short, should be SPARSE or DEVELOPING)
    'V-I': ['V', 'I'],
    'IV-I': ['IV', 'I'],
    
    # Pop progressions (should be CYCLE or MUSIC)
    'I-V-vi-IV': ['I', 'V', 'vi', 'IV'],
    'I-vi-IV-V': ['I', 'vi', 'IV', 'V'],
    'vi-IV-I-V': ['vi', 'IV', 'I', 'V'],
    
    # Jazz (should be MUSIC — memory + transport + surprise)
    'ii-V-I': ['ii', 'V', 'I'],
    'I-vi-ii-V': ['I', 'vi', 'ii', 'V'],
    'iii-vi-ii-V-I': ['iii', 'vi', 'ii', 'V', 'I'],
    
    # Extended (more data = clearer signal)
    'I-IV-V-I': ['I', 'IV', 'V', 'I'],
    'I-iii-vi-ii-V-I': ['I', 'iii', 'vi', 'ii', 'V', 'I'],
    
    # Deceptive / surprising (should have high transformation)
    'I-V-vi-iii-IV': ['I', 'V', 'vi', 'iii', 'IV'],
    'I-bVII-IV-I': ['I', 'bVII', 'IV', 'I'],
    
    # Random (should be RANDOM)
    'I-iii-V-ii': ['I', 'iii', 'V', 'ii'],
    
    # Full song-length (repeat pop loop)
    'pop-loop-2x': ['I', 'V', 'vi', 'IV', 'I', 'V', 'vi', 'IV'],
    'jazz-turnaround-2x': ['I', 'vi', 'ii', 'V', 'I', 'vi', 'ii', 'V'],
}


def main():
    print("=" * 70)
    print("  🌊 ENTROPY TRAJECTORIES — Progressions as Dynamical Systems")
    print("  The bridge between consonance and entropy-edge")
    print("=" * 70)
    
    results = {}
    for name, chords in PROGRESSIONS.items():
        r = analyze_trajectory(chords, label=name)
        results[name] = r
    
    # ── Display results sorted by triple-point score ──
    print("\n" + "=" * 70)
    print("  TRIPLE-POINT RANKINGS")
    print("  Memory × Transport × Transformation → Music")
    print("=" * 70)
    
    ranked = sorted(results.values(), key=lambda x: x['triple_point'], reverse=True)
    
    print(f"\n  {'Progression':<30s} {'Mem':>5s} {'Trn':>5s} {'Tfm':>5s} {'TP':>5s}  Class")
    print(f"  {'─'*30} {'─'*5} {'─'*5} {'─'*5} {'─'*5}  {'─'*12}")
    
    for r in ranked:
        print(f"  {r['label']:<30s} {r['memory']:5.3f} {r['transport']:5.3f} "
              f"{r['transformation']:5.3f} {r['triple_point']:5.3f}  {r['classification']}")
    
    # ── Detailed trajectory for the top scoring progression ──
    if ranked:
        top = ranked[0]
        print(f"\n\n{'=' * 70}")
        print(f"  DETAILED TRAJECTORY: {top['label']}")
        print(f"  {' → '.join(top['chords'])}")
        print(f"{'=' * 70}")
        
        for t in top['transitions']:
            direction = "↓ resolve" if t['resolution_delta'] < 0 else "↑ tension"
            print(f"    {t['from']:>5s} → {t['to']:<5s}  "
                  f"T(E)={t['transition_entropy']:.3f}  "
                  f"Δ={t['resolution_delta']:+.3f} {direction}  "
                  f"VL={t['voice_leading_dist']:.1f}  "
                  f"grav={t['gravity']:.3f}")
    
    # ── Key findings ──
    print(f"\n\n{'=' * 70}")
    print(f"  KEY FINDINGS")
    print(f"{'=' * 70}")
    
    # Do loops score low?
    loop_scores = [r['triple_point'] for r in results.values() 
                   if 'LOOP' in r['classification'] or 'STATIC' in r['classification'] 
                   or 'CYCLE' in r['classification']]
    music_scores = [r['triple_point'] for r in results.values()
                    if 'MUSIC' in r['classification'] or 'DEVELOPING' in r['classification']]
    
    if loop_scores and music_scores:
        mean_loop = sum(loop_scores) / len(loop_scores)
        mean_music = sum(music_scores) / len(music_scores)
        separation = mean_music / mean_loop if mean_loop > 0 else float('inf')
        print(f"\n  Mean loop/static TP score: {mean_loop:.3f}")
        print(f"  Mean music/developing TP:  {mean_music:.3f}")
        print(f"  Separation ratio: {separation:.1f}x")
        if separation > 1.5:
            print(f"  ✅ Triple-point metric separates boring from interesting progressions")
        else:
            print(f"  ⚠️  Separation is weak — metric needs tuning")
    
    # Does repeated loop score higher than single? (memory should increase)
    if 'I-V-vi-IV' in results and 'pop-loop-2x' in results:
        single = results['I-V-vi-IV']
        double = results['pop-loop-2x']
        print(f"\n  Pop loop 1x vs 2x:")
        print(f"    1x: mem={single['memory']:.3f} trn={single['transport']:.3f} "
              f"tfm={single['transformation']:.3f} TP={single['triple_point']:.3f}")
        print(f"    2x: mem={double['memory']:.3f} trn={double['transport']:.3f} "
              f"tfm={double['transformation']:.3f} TP={double['triple_point']:.3f}")
        if double['memory'] > single['memory']:
            print(f"    ✅ Repetition increases memory (as expected)")
        else:
            print(f"    ⚠️  Repetition didn't increase memory — reconsider metric")
    
    # Does circle-of-fifths score highest? (memory + transport + some transformation)
    cof_name = 'I-iii-vi-ii-V-I'
    if cof_name in results:
        cof = results[cof_name]
        print(f"\n  Circle of fifths ({cof_name}):")
        print(f"    mem={cof['memory']:.3f} trn={cof['transport']:.3f} "
              f"tfm={cof['transformation']:.3f} TP={cof['triple_point']:.3f}")
        print(f"    Class: {cof['classification']}")
    
    # Connection to entropy-edge
    print(f"\n\n{'═' * 70}")
    print(f"  BRIDGE TO ENTROPY-EDGE")
    print(f"{'═' * 70}")
    print(f"""
  Wolfram classes → Musical classes:
    Class 1 (fixed point)  → LOOP / STATIC (drone, single chord)
    Class 2 (periodic)     → CYCLE (pop loop, vamp)
    Class 3 (chaotic)      → RANDOM (free jazz, atonal)
    Class 4 (complex)      → MUSIC (Bach, jazz standards, prog rock)

  The triple-point metric works in both domains because both are
  about COMPUTATION: cellular automata compute on bit patterns,
  music computes on listener expectations.

  A boring loop = Class 2 = periodic memory, no transformation.
  A great solo = Class 4 = references its own history, builds
  coherently, AND surprises.

  Rule 110 is to automata what a Bach fugue is to music:
  the triple point where all three axes converge.
    """)
    
    return results


if __name__ == "__main__":
    results = main()
