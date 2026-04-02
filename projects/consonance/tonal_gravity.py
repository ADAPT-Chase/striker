#!/usr/bin/env python3
"""
🌊 TONAL GRAVITY — Key-center attraction as information-theoretic force
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Previous work:
- harmonic_entropy.py: r=0.817 with human consonance (interval-level)
- transition_entropy.py: broke major/minor degeneracy  
- cadence_trajectories.py: surprise works, tonal gravity missing

Problem: resolution_delta only fires on quality-changing transitions 
(major↔minor). V→I (both major) shows Δ=0. But V→I is THE strongest 
resolution in Western music. Why? Because of GRAVITY — the pull toward 
the tonic, not just the change in dissonance.

This module: model tonal gravity from first principles.

Three components:
1. PITCH-CLASS GRAVITY: Each pitch class has a "distance" from the tonic
   in a perceptually-weighted space (circle of fifths + octave).
   Closer = more stable = lower gravitational potential.

2. TENDENCY TONE PULL: Leading tone (B→C), fa (F→E), and tritone 
   resolution create directional force vectors. These are information-
   theoretic: high-information (rare/unstable) states "want" to become
   low-information (common/stable) states.

3. CHORD GRAVITY: Aggregate of note gravities, weighted by voicing.
   A chord's gravity = its potential energy in the tonal field.
   Resolution = moving from high to low potential.

The model should predict:
- V→I is strongly resolving (high → low gravity)
- V→vi is NOT resolving (gravity stays high)  
- ii→V builds tension (moderate → high gravity)
- IV→I resolves plagally (moderate → low)

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

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 1: Pitch-class gravity field
# ═══════════════════════════════════════════════════════════════════════
# 
# Each pitch class has a stability in a given key. This comes from two 
# sources: (a) position on the circle of fifths relative to tonic, and
# (b) membership in the tonic triad/scale.
#
# The circle of fifths distance is perceptually real — it maps to shared 
# harmonics. Notes closer on the CoF share more overtones with the tonic.
#
# We use GRAVITATIONAL POTENTIAL: low = stable, high = unstable.
# Resolution = moving from high potential to low potential.

# Circle of fifths position relative to C (0 = unison, 1 = fifth, etc.)
# This gives the "harmonic distance" from tonic
COF_POSITION = {
    0: 0,   # C (tonic)
    7: 1,   # G (fifth)  
    2: 2,   # D
    9: 3,   # A
    4: 4,   # E
    11: 5,  # B
    6: 6,   # F#/Gb (tritone - maximally distant)
    1: 5,   # Db
    8: 4,   # Ab
    3: 3,   # Eb
    10: 2,  # Bb
    5: 1,   # F (fourth = one fifth below)
}

# Tonal stability weights — how stable each scale degree is in C major
# Based on cognitive research (Krumhansl probe-tone profiles)
# Higher = more stable = lower gravitational potential
KRUMHANSL_MAJOR = {
    0: 6.35,   # C  - tonic (most stable)
    1: 2.23,   # C# - chromatic
    2: 3.48,   # D  - supertonic
    3: 2.33,   # Eb - chromatic  
    4: 4.38,   # E  - mediant
    5: 4.09,   # F  - subdominant
    6: 2.52,   # F# - chromatic
    7: 5.19,   # G  - dominant (very stable)
    8: 2.39,   # Ab - chromatic
    9: 3.66,   # A  - submediant
    10: 2.29,  # Bb - chromatic
    11: 2.88,  # B  - leading tone (unstable but diatonic)
}


def pitch_gravity(pitch_class, key=0):
    """
    Gravitational potential of a single pitch class in a key.
    Higher = more unstable = more gravitational potential energy.
    
    Combines:
    - Circle of fifths distance (harmonic remoteness)
    - Inverse Krumhansl stability (cognitive instability)
    """
    pc = (pitch_class - key) % 12
    
    # Harmonic distance (0-6, normalized to 0-1)
    cof_dist = COF_POSITION[pc] / 6.0
    
    # Cognitive instability (invert Krumhansl: high stability → low gravity)
    max_k = max(KRUMHANSL_MAJOR.values())
    cognitive_instability = 1.0 - (KRUMHANSL_MAJOR[pc] / max_k)
    
    # Combine: both contribute to gravitational potential
    # Weight cognitive more — it's empirically grounded
    gravity = 0.4 * cof_dist + 0.6 * cognitive_instability
    
    return gravity


def chord_gravity(pitches, key=0):
    """
    Total gravitational potential of a chord.
    Sum of individual pitch gravities, with bass note weighted more heavily.
    """
    if not pitches:
        return 0.0
    
    pcs = [(p - key) % 12 for p in pitches]
    
    # Bass note gets extra weight (it defines harmonic function most)
    bass_weight = 1.5
    gravities = []
    for i, pc in enumerate(pcs):
        w = bass_weight if i == 0 else 1.0
        gravities.append(w * pitch_gravity(pc, key=0))  # already transposed
    
    # Normalize by number of voices to make comparable across chord sizes
    total = sum(gravities) / (len(pcs) + (bass_weight - 1.0))
    
    return total


# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 2: Tendency tone forces
# ═══════════════════════════════════════════════════════════════════════
#
# Some pitch motions have DIRECTIONAL force beyond just "moving to 
# stability." The leading tone B→C isn't just "B is unstable and C is 
# stable" — it's that B *specifically wants* C. The tritone B-F wants 
# to resolve to C-E.
#
# These are modeled as resolution vectors: specific pitch-class motions 
# that have extra gravitational pull.

TENDENCY_TONES = {
    # (from_pc, to_pc): strength of pull
    (11, 0): 1.0,    # Leading tone → tonic (strongest)
    (5, 4): 0.7,     # Fa → mi (subdominant resolution)
    (1, 0): 0.8,     # Chromatic upper neighbor → tonic
    (6, 7): 0.6,     # Tritone → fifth (augmented 4th resolves up)
    (6, 5): 0.5,     # Tritone → fourth (diminished 5th resolves down)
    (11, 11): 0.0,   # No self-tendency
    (4, 4): 0.0,
    # Tritone pair resolution
    (11, 0): 1.0,    # B→C (in context of V→I)
    (5, 4): 0.7,     # F→E (in context of V→I: 7th resolves down)
}


def tendency_resolution(from_pitches, to_pitches, key=0):
    """
    How much tendency-tone resolution occurs between two chords.
    Looks for specific pitch-class motions that carry directional force.
    
    Returns: total tendency satisfaction (0 = none, higher = more resolution)
    """
    from_pcs = set((p - key) % 12 for p in from_pitches)
    to_pcs = set((p - key) % 12 for p in to_pitches)
    
    total_tendency = 0.0
    
    for fpc in from_pcs:
        for tpc in to_pcs:
            pair = (fpc, tpc)
            if pair in TENDENCY_TONES:
                total_tendency += TENDENCY_TONES[pair]
    
    # Also check: does the tritone resolve?
    # If from_chord contains both 11 and 5, and to_chord contains both 0 and 4,
    # that's a complete tritone resolution (the essence of V→I)
    if 11 in from_pcs and 5 in from_pcs:
        if 0 in to_pcs and 4 in to_pcs:
            total_tendency += 0.5  # Bonus for complete tritone resolution
    
    return total_tendency


# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 3: Combined tonal gravity model  
# ═══════════════════════════════════════════════════════════════════════

def gravity_delta(from_pitches, to_pitches, key=0):
    """
    Change in gravitational potential from one chord to another.
    
    Negative = resolution (moving toward stability)
    Positive = tension building (moving away from stability)
    
    This is what resolution_delta SHOULD have been.
    """
    g_from = chord_gravity(from_pitches, key)
    g_to = chord_gravity(to_pitches, key)
    
    return g_to - g_from


def bass_resolution(from_pitches, to_pitches, key=0):
    """
    Does the bass motion resolve toward tonic?
    
    Strong resolution bass motions (in order):
    - Fifth down / fourth up to tonic (V→I bass: G→C) 
    - Fourth down to tonic (IV→I bass: F→C)
    - Step down to tonic (ii→I bass: D→C)
    
    Weak/deceptive bass motions:
    - Third down (V→vi bass: G→A... wait, that's third DOWN from G?)
    - Actually G→A is step UP. The bass doesn't go home.
    
    Returns: bass resolution score (higher = bass resolves more toward tonic)
    """
    bass_from = (from_pitches[0] - key) % 12
    bass_to = (to_pitches[0] - key) % 12
    
    # Does the bass land on tonic?
    tonic_landing = 1.0 if bass_to == 0 else 0.0
    
    # Does the bass land on the fifth?
    fifth_landing = 0.5 if bass_to == 7 else 0.0
    
    # Is this a strong-beat interval? (4th/5th motion = strongest)
    interval = (bass_to - bass_from) % 12
    strong_motion = {
        5: 0.8,   # Fourth up (or fifth down) — V→I
        7: 0.8,   # Fifth up — I→V (tension-building but strong)
        0: 0.0,   # Same note
    }
    motion_strength = strong_motion.get(interval, 0.3)
    
    # Gravity of bass landing
    bass_gravity = pitch_gravity(bass_to, key=0)
    bass_stability = 1.0 - bass_gravity  # Higher = more stable landing
    
    return {
        'tonic_landing': tonic_landing,
        'fifth_landing': fifth_landing,
        'motion_strength': motion_strength,
        'bass_stability': bass_stability,
        'bass_from_gravity': pitch_gravity(bass_from, key=0),
        'bass_to_gravity': pitch_gravity(bass_to, key=0),
    }


def tonal_resolution(from_pitches, to_pitches, key=0):
    """
    Complete resolution score combining:
    1. Gravity delta (potential energy change)
    2. Tendency tone satisfaction
    3. Voice leading smoothness
    4. Bass motion resolution (NEW — addresses deceptive cadence problem)
    
    Higher = more resolution
    """
    # Gravity change (negative = resolving)
    g_delta = gravity_delta(from_pitches, to_pitches, key)
    
    # Tendency tone satisfaction (positive = resolving) 
    tendency = tendency_resolution(from_pitches, to_pitches, key)
    
    # Voice leading smoothness (lower entropy = smoother)
    vle_result = voice_leading_entropy(from_pitches, to_pitches)
    vle = vle_result[0] if isinstance(vle_result, tuple) else vle_result
    
    # Bass resolution (NEW)
    bass = bass_resolution(from_pitches, to_pitches, key)
    bass_score = (bass['tonic_landing'] * 0.5 + 
                  bass['bass_stability'] * 0.3 + 
                  bass['motion_strength'] * 0.2)
    
    # Combined: resolution = gravity drop + tendency + bass landing - voice leading cost
    resolution = -g_delta + tendency * 0.2 + bass_score * 0.3 - vle * 0.05
    
    return {
        'resolution': resolution,
        'gravity_delta': g_delta,
        'tendency': tendency,
        'voice_leading_entropy': vle,
        'gravity_from': chord_gravity(from_pitches, key),
        'gravity_to': chord_gravity(to_pitches, key),
        'bass_score': bass_score,
        'bass_detail': bass,
    }


# ═══════════════════════════════════════════════════════════════════════
# VOICINGS (from cadence_trajectories.py)  
# ═══════════════════════════════════════════════════════════════════════

VOICINGS = dict(DIATONIC_4V)
VOICINGS.update({
    'I7':    [0, 4, 7, 11],
    'ii7':   [2, 5, 9, 12],
    'iii7':  [4, 7, 11, 14],
    'IV7':   [5, 9, 12, 16],
    'V7':    [7, 11, 14, 17],
    'vi7':   [9, 12, 16, 19],
    'vii7':  [11, 14, 17, 21],
})

# ═══════════════════════════════════════════════════════════════════════
# TESTING & VALIDATION
# ═══════════════════════════════════════════════════════════════════════

CADENCES = {
    'Authentic (V→I)':           ['V', 'I'],
    'Plagal (IV→I)':             ['IV', 'I'],
    'Deceptive (V→vi)':          ['V', 'vi'],
    'Half (I→V)':                ['I', 'V'],
    'ii-V-I':                    ['ii', 'V', 'I'],
    'IV-V-I':                    ['IV', 'V', 'I'],
    'vi-IV-V-I':                 ['vi', 'IV', 'V', 'I'],
    'I-vi-IV-V (50s)':           ['I', 'vi', 'IV', 'V'],
    'I-V-vi-IV (Axis)':          ['I', 'V', 'vi', 'IV'],
    'ii7-V7-I7 (Jazz)':          ['ii7', 'V7', 'I7'],
    'iii7-vi7-ii7-V7-I7 (Full)': ['iii7', 'vi7', 'ii7', 'V7', 'I7'],
    'ii-V-vi (Deceptive jazz)':  ['ii', 'V', 'vi'],
    'IV-V-vi (Deceptive full)':  ['IV', 'V', 'vi'],
}


def main():
    print("=" * 72)
    print("  TONAL GRAVITY — Key-center attraction model")
    print("=" * 72)
    
    # ── Part 1: Pitch gravity field ──
    print("\n\n" + "─" * 72)
    print("  GRAVITATIONAL FIELD (key of C)")
    print("─" * 72)
    print(f"\n  {'Note':>5s}  {'CoF dist':>8s}  {'Krumhansl':>9s}  {'Gravity':>8s}  {'Bar'}")
    print(f"  {'─'*60}")
    
    note_names = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    for pc in range(12):
        g = pitch_gravity(pc)
        cof = COF_POSITION[pc]
        k = KRUMHANSL_MAJOR[pc]
        bar = "█" * int(g * 30)
        print(f"  {note_names[pc]:>5s}  {cof:>8d}  {k:>9.2f}  {g:>8.3f}  {bar}")
    
    # ── Part 2: Chord gravities ──
    print("\n\n" + "─" * 72)
    print("  CHORD GRAVITATIONAL POTENTIALS")
    print("─" * 72)
    
    print(f"\n  {'Chord':>8s}  {'Gravity':>8s}  {'Bar'}")
    print(f"  {'─'*50}")
    
    chord_order = ['I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii°']
    # vii° might not be in VOICINGS by that name
    for name in ['I', 'ii', 'iii', 'IV', 'V', 'vi']:
        if name in VOICINGS:
            g = chord_gravity(VOICINGS[name])
            bar = "█" * int(g * 40)
            print(f"  {name:>8s}  {g:>8.3f}  {bar}")
    
    print()
    for name in ['I7', 'ii7', 'iii7', 'IV7', 'V7', 'vi7', 'vii7']:
        if name in VOICINGS:
            g = chord_gravity(VOICINGS[name])
            bar = "█" * int(g * 40)
            print(f"  {name:>8s}  {g:>8.3f}  {bar}")
    
    # ── Part 3: Key test — V→I vs V→vi ──
    print("\n\n" + "=" * 72)
    print("  CRITICAL TEST: V→I vs V→vi")
    print("  (This is what the old model couldn't distinguish)")
    print("=" * 72)
    
    auth = tonal_resolution(VOICINGS['V'], VOICINGS['I'])
    dec = tonal_resolution(VOICINGS['V'], VOICINGS['vi'])
    
    print(f"\n  {'Metric':<30s}  {'V→I':>10s}  {'V→vi':>10s}  {'Difference':>12s}")
    print(f"  {'─'*70}")
    print(f"  {'Gravity delta':<30s}  {auth['gravity_delta']:>+10.4f}  {dec['gravity_delta']:>+10.4f}  {auth['gravity_delta']-dec['gravity_delta']:>+12.4f}")
    print(f"  {'Tendency satisfaction':<30s}  {auth['tendency']:>10.4f}  {dec['tendency']:>10.4f}  {auth['tendency']-dec['tendency']:>+12.4f}")
    print(f"  {'Voice leading entropy':<30s}  {auth['voice_leading_entropy']:>10.4f}  {dec['voice_leading_entropy']:>10.4f}  {auth['voice_leading_entropy']-dec['voice_leading_entropy']:>+12.4f}")
    print(f"  {'TOTAL RESOLUTION':<30s}  {auth['resolution']:>10.4f}  {dec['resolution']:>10.4f}  {auth['resolution']-dec['resolution']:>+12.4f}")
    
    if auth['resolution'] > dec['resolution']:
        print(f"\n  ✅ V→I resolves MORE than V→vi! (ratio: {auth['resolution']/max(dec['resolution'], 0.001):.2f}x)")
    else:
        print(f"\n  ❌ Model fails: V→vi shouldn't resolve more than V→I")
    
    # ── Part 4: All cadences with gravity ──
    print("\n\n" + "=" * 72)
    print("  ALL CADENCE GRAVITY TRAJECTORIES")
    print("=" * 72)
    
    results = {}
    
    for name, chords in CADENCES.items():
        chord_voicings = [VOICINGS[c] for c in chords]
        steps = []
        for i in range(len(chord_voicings) - 1):
            res = tonal_resolution(chord_voicings[i], chord_voicings[i+1])
            te = transition_entropy(chord_voicings[i], chord_voicings[i+1])
            steps.append({
                'from': chords[i], 'to': chords[i+1],
                **res,
                'surprise': te,
            })
        
        total_resolution = sum(s['resolution'] for s in steps)
        final_resolution = steps[-1]['resolution'] if steps else 0
        total_surprise = sum(s['surprise'] for s in steps)
        
        results[name] = {
            'steps': steps,
            'total_resolution': total_resolution,
            'final_resolution': final_resolution,
            'total_surprise': total_surprise,
            'resolves': final_resolution > 0,  # positive = resolving
        }
        
        print(f"\n  {name}: {' → '.join(chords)}")
        for s in steps:
            arrow = "↘" if s['resolution'] > 0.01 else "↗" if s['resolution'] < -0.01 else "→"
            print(f"    {s['from']:>5s} {arrow} {s['to']:<5s}  "
                  f"grav={s['gravity_delta']:+.3f}  "
                  f"tend={s['tendency']:.2f}  "
                  f"res={s['resolution']:+.3f}  "
                  f"T(E)={s['surprise']:.3f}")
        print(f"    Total: Σres={total_resolution:+.3f}  "
              f"final_res={final_resolution:+.3f}  "
              f"ΣT(E)={total_surprise:.3f}  "
              f"{'✓ resolves' if final_resolution > 0 else '✗ doesn''t resolve'}")
    
    # ── Part 5: Classification accuracy ──
    print("\n\n" + "=" * 72)
    print("  CLASSIFICATION: Does gravity predict cadence function?")
    print("=" * 72)
    
    expected_resolve = {
        'Authentic (V→I)': True,
        'Plagal (IV→I)': True,
        'Deceptive (V→vi)': False,  # Should NOT resolve
        'Half (I→V)': False,         # Should NOT resolve
        'ii-V-I': True,
        'IV-V-I': True,
        'vi-IV-V-I': True,
        'ii7-V7-I7 (Jazz)': True,
        'iii7-vi7-ii7-V7-I7 (Full)': True,
        'ii-V-vi (Deceptive jazz)': False,
        'IV-V-vi (Deceptive full)': False,
    }
    
    correct = 0
    total = 0
    
    print(f"\n  {'Cadence':<40s}  {'Expected':>8s}  {'Got':>8s}  {'Score':>8s}  {'Match'}")
    print(f"  {'─'*80}")
    
    for name, should_resolve in expected_resolve.items():
        if name in results:
            total += 1
            does_resolve = results[name]['final_resolution'] > 0
            match = does_resolve == should_resolve
            if match:
                correct += 1
            print(f"  {name:<40s}  "
                  f"{'resolv' if should_resolve else 'non-res':>8s}  "
                  f"{'resolv' if does_resolve else 'non-res':>8s}  "
                  f"{results[name]['final_resolution']:>+8.3f}  "
                  f"{'✅' if match else '❌'}")
    
    acc = correct / total if total > 0 else 0
    print(f"\n  Accuracy: {correct}/{total} = {acc:.0%}")
    
    if acc > 0.7:
        print(f"  ✅ Tonal gravity PREDICTS cadence function!")
    elif acc > 0.5:
        print(f"  ⚠️  Partial success — gravity helps but isn't sufficient")
    else:
        print(f"  ❌ Model needs work")
    
    # Compare with old model
    print(f"\n  Comparison with resolution_delta (old model): 27% accuracy")
    print(f"  Tonal gravity model: {acc:.0%} accuracy")
    if acc > 0.27:
        print(f"  ✅ Improvement: {acc - 0.27:+.0%} absolute")
    
    # ── Part 6: Combined score — surprise + gravity ──
    print("\n\n" + "=" * 72)
    print("  COMBINED: Surprise × Gravity (the full picture)")
    print("=" * 72)
    print(f"\n  The complete model: T(E) captures HOW SURPRISING a move is.")
    print(f"  Gravity captures WHERE it goes relative to the tonal center.")
    print(f"  Together they should predict musical function.")
    
    print(f"\n  {'Cadence':<40s}  {'Surprise':>8s}  {'Gravity':>8s}  {'Character'}")
    print(f"  {'─'*75}")
    
    for name, r in sorted(results.items(), key=lambda x: -x[1]['total_resolution']):
        # Characterize
        high_surprise = r['total_surprise'] > 2.0
        resolves = r['total_resolution'] > 0
        
        if resolves and high_surprise:
            character = "Strong resolution, eventful path"
        elif resolves and not high_surprise:
            character = "Gentle resolution, smooth path"
        elif not resolves and high_surprise:
            character = "Tension-building, surprising"
        else:
            character = "Static, circular"
        
        print(f"  {name:<40s}  "
              f"{r['total_surprise']:>8.3f}  "
              f"{r['total_resolution']:>+8.3f}  "
              f"{character}")
    
    # ── Summary ──
    print("\n\n" + "=" * 72)
    print("  KEY FINDINGS")
    print("=" * 72)
    
    v_i = results.get('Authentic (V→I)', {})
    v_vi = results.get('Deceptive (V→vi)', {})
    
    if v_i and v_vi:
        print(f"\n  1. V→I vs V→vi DIFFERENTIATION:")
        print(f"     V→I  resolution: {v_i['final_resolution']:+.4f}")
        print(f"     V→vi resolution: {v_vi['final_resolution']:+.4f}")
        if v_i['final_resolution'] > v_vi['final_resolution']:
            print(f"     ✅ Gravity correctly separates authentic from deceptive!")
    
    jazz_ii_v_i = results.get('ii7-V7-I7 (Jazz)', {})
    triad_ii_v_i = results.get('ii-V-I', {})
    if jazz_ii_v_i and triad_ii_v_i:
        print(f"\n  2. JAZZ vs CLASSICAL ii-V-I:")
        print(f"     Triad total resolution:  {triad_ii_v_i['total_resolution']:+.4f}")
        print(f"     Jazz 7th total resolution: {jazz_ii_v_i['total_resolution']:+.4f}")
    
    print(f"\n  3. CLASSIFICATION ACCURACY: {acc:.0%}")
    print(f"     vs old resolution_delta: 27%")
    print(f"     Improvement: {acc - 0.27:+.0%}")


if __name__ == "__main__":
    main()
