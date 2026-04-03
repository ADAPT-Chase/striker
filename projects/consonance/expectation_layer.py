#!/usr/bin/env python3
"""
🧠 EXPECTATION LAYER — What the listener anticipates changes what they feel
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Previous work:
- tonal_gravity.py: 81% on real music, perfect cadence ranking
- Three failures share one cause: no concept of EXPECTATION

The problem: V at the end of a turnaround (I-vi-ii-V) has positive 
resolution from ii→V... but V IMPLIES I is coming. The listener hears 
tension because they're waiting for resolution that hasn't arrived.

This is Narmour's Implication-Realization theory meets information theory:
- Every chord creates EXPECTATIONS about what comes next
- Unresolved expectations = tension (the listener is "owed" something)
- The strength of expectation depends on how strongly the chord implies 
  its successor in common practice

Three components:
1. IMPLICATION STRENGTH: How strongly does this chord demand a specific 
   continuation? (V demands I. IV suggests I. ii suggests V.)
2. SCHEMA MATCHING: Does this ending match a known schema (loop, cadence, 
   through-composed)? Loops end on unstable chords by definition.
3. EXPECTATION DEBT: The accumulated unresolved implications at the end 
   of the progression. High debt = tension, regardless of last step.

Striker, April 2026
"""

import math
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from tonal_gravity import (
    tonal_resolution, chord_gravity, gravity_delta,
    tendency_resolution, bass_resolution, VOICINGS
)


# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 1: Chord implication vectors
# ═══════════════════════════════════════════════════════════════════════
# 
# Each chord in a key implies certain continuations with varying strength.
# This is the common-practice Markov structure, but weighted by how 
# COMPULSORY the continuation feels, not just how frequent it is.
#
# Scale: 0 = no implication, 1 = near-mandatory continuation
# Only strong implications listed. Weak ones (many possible continuations) 
# are omitted — they create LOW expectation, not high.

IMPLICATIONS = {
    # Chord: {implied_next: strength}
    'V':    {'I': 0.85, 'vi': 0.35},           # V demands I. Deceptive is known but surprising.
    'V7':   {'I': 0.92, 'vi': 0.25},           # V7 even more demanding (tritone MUST resolve)
    'viio': {'I': 0.80},                        # Leading tone chord → tonic
    'ii':   {'V': 0.65, 'V7': 0.65},           # Pre-dominant → dominant
    'IV':   {'I': 0.45, 'V': 0.40, 'iv': 0.2}, # Subdominant is versatile, less demanding
    'vi':   {'ii': 0.40, 'IV': 0.40, 'V': 0.25}, # Submediant — many good paths
    'I':    {},                                  # Tonic implies nothing — it's HOME
    'iii':  {'IV': 0.35, 'vi': 0.35},          # Mediant — weak implications
    'iv':   {'I': 0.55},                        # Minor iv → I (plagal in minor)
    'bVII': {'I': 0.30, 'IV': 0.30},           # Modal mixture — weak pull
}


def implication_strength(chord_name):
    """
    How strongly does this chord demand a specific continuation?
    Returns (max_implication_strength, implied_target).
    
    High value = this chord creates strong expectation.
    Low value = this chord could go anywhere (or is home).
    """
    impl = IMPLICATIONS.get(chord_name, {})
    if not impl:
        return 0.0, None
    
    strongest = max(impl.items(), key=lambda x: x[1])
    return strongest[1], strongest[0]


def expectation_debt(chord_sequence):
    """
    How much unresolved expectation exists at the END of this progression?
    
    Walk through the sequence. At each chord:
    - Previous chord created expectations
    - If this chord matches what was expected → debt DECREASES
    - If this chord doesn't match → debt INCREASES (surprise) or carries forward
    
    Returns: (total_debt, debt_trajectory)
    Debt at end > 0.3 means the listener is left hanging → tension.
    """
    if len(chord_sequence) < 2:
        return 0.0, [0.0]
    
    debt = 0.0
    trajectory = [0.0]
    
    for i in range(len(chord_sequence) - 1):
        current = chord_sequence[i]
        next_chord = chord_sequence[i + 1]
        
        impl = IMPLICATIONS.get(current, {})
        
        if not impl:
            # Current chord creates no expectation → debt unchanged
            trajectory.append(debt)
            continue
        
        max_strength, expected = implication_strength(current)
        
        if next_chord in impl:
            # Expectation MET — debt decreases proportional to how expected this was
            satisfaction = impl[next_chord]
            debt = max(0, debt - satisfaction)
        else:
            # Expectation VIOLATED — debt increases
            # The stronger the implication, the more debt from violation
            debt += max_strength * 0.7  # Scaled: not full strength, some surprise is ok
        
        trajectory.append(debt)
    
    # Final chord's OWN implications add to debt
    # (V at the end means the listener expects I — that's debt)
    final_strength, final_expected = implication_strength(chord_sequence[-1])
    debt += final_strength
    trajectory[-1] = debt
    
    return debt, trajectory


# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 2: Schema detection  
# ═══════════════════════════════════════════════════════════════════════
#
# Some progressions are heard as LOOPS vs one-shots. This changes meaning:
# - Loop ending on V → tension (V is a pickup to I at top of loop)
# - One-shot ending on V → half cadence (intentional stopping point)
# - Loop ending on IV → cycling (IV as subdominant plateau)

KNOWN_LOOPS = {
    # (tuple of chord sequence): schema name
    ('I', 'V', 'vi', 'IV'): 'axis',           # Axis of Awesome
    ('I', 'vi', 'IV', 'V'): '50s_turnaround',  # 50s doo-wop
    ('I', 'vi', 'ii', 'V'): 'jazz_turnaround',  # Rhythm changes
    ('vi', 'IV', 'I', 'V'): 'pop_loop',        # Modern pop
    ('I', 'IV', 'vi', 'V'): 'anthem',          # Arena rock
    ('I', 'bVII', 'IV', 'I'): 'rock_shuttle',  # Classic rock
}


def detect_schema(chord_sequence):
    """
    Does this sequence match a known loop or cadential schema?
    Returns: (schema_name, is_loop, loop_tension_at_end)
    """
    seq_tuple = tuple(chord_sequence)
    
    if seq_tuple in KNOWN_LOOPS:
        schema = KNOWN_LOOPS[seq_tuple]
        # Loops always have tension at the end (they want to cycle)
        final_impl, _ = implication_strength(chord_sequence[-1])
        return schema, True, final_impl
    
    # Check if the progression ENDS where it STARTED (closed form)
    if len(chord_sequence) >= 3 and chord_sequence[0] == chord_sequence[-1]:
        return 'closed_form', False, 0.0
    
    # Check if last chord has strong implication toward FIRST chord
    # (this makes it feel like a loop even if not in our dictionary)
    impl = IMPLICATIONS.get(chord_sequence[-1], {})
    if chord_sequence[0] in impl and impl[chord_sequence[0]] > 0.5:
        return 'implied_loop', True, impl[chord_sequence[0]]
    
    return None, False, 0.0


# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 3: Enhanced classifier with expectation
# ═══════════════════════════════════════════════════════════════════════

def analyze_with_expectation(chord_names, voicings_dict):
    """
    Full analysis including gravity + expectation.
    Returns enriched analysis dict.
    """
    voicings = [voicings_dict[c] for c in chord_names]
    
    # Gravity analysis (existing)
    gravities = [chord_gravity(v) for v in voicings]
    steps = []
    for i in range(len(voicings) - 1):
        res = tonal_resolution(voicings[i], voicings[i+1])
        steps.append({
            'from': chord_names[i],
            'to': chord_names[i+1],
            'resolution': res['resolution'],
            'detail': res,
        })
    
    total_resolution = sum(s['resolution'] for s in steps)
    final_resolution = steps[-1]['resolution'] if steps else 0
    
    # Expectation analysis (new)
    debt, debt_trajectory = expectation_debt(chord_names)
    schema, is_loop, loop_tension = detect_schema(chord_names)
    final_impl_strength, final_implied = implication_strength(chord_names[-1])
    
    return {
        'chords': chord_names,
        'total_resolution': total_resolution,
        'final_resolution': final_resolution,
        'gravities': gravities,
        'steps': steps,
        # Expectation
        'expectation_debt': debt,
        'debt_trajectory': debt_trajectory,
        'schema': schema,
        'is_loop': is_loop,
        'loop_tension': loop_tension,
        'final_implication': final_impl_strength,
        'final_implied_chord': final_implied,
    }


def classify_with_expectation(analysis):
    """
    Enhanced classifier that uses both gravity and expectation.
    
    Key insight: a positive final resolution step can STILL be tension
    if the final chord creates strong expectation of continuation.
    """
    total = analysis['total_resolution']
    final = analysis['final_resolution']
    debt = analysis['expectation_debt']
    is_loop = analysis['is_loop']
    final_impl = analysis['final_implication']
    
    # ── STATIC DETECTION (before expectation, to avoid false tension) ──
    # Short progressions (2 chords) with low gravity movement = static/modal
    # Modal contexts don't carry common-practice implications as strongly
    n_chords = len(analysis.get('chords', []))
    if n_chords <= 2 and abs(total) < 0.15 and abs(final) < 0.15:
        return 'static'
    
    # ── LOOP / STRONG ENDING IMPLICATION ──
    # If the final chord strongly implies a continuation (V→I, etc)
    # and that continuation hasn't arrived, the listener is left hanging.
    # This is tension, not cycling. "Cycling" requires actually HEARING 
    # the loop restart — we only see one pass.
    if final_impl > 0.6:
        # Final chord demands continuation → tension regardless
        return 'tension_building'
    
    # ── EXPECTATION DEBT ──
    # High debt at end = listener is left hanging, regardless of last step
    # But only if the progression is long enough to accumulate real debt
    if debt > 0.7 and final < 0.5 and n_chords >= 3:
        return 'tension_building'
    
    # ── CYCLING (loop detected, but ending implication is moderate) ──
    # Loops with moderate ending implication and forward motion = cycling
    if is_loop and final_impl > 0.3 and total > 0:
        return 'cycling'
    
    # ── GRAVITY-BASED (existing logic, slightly refined) ──
    if final > 0.3 and total > 0.3:
        return 'resolving'
    elif final > 0.1 and total > 0:
        return 'partial_resolve'
    elif final < -0.1:
        return 'tension_building'
    elif abs(total) < 0.15 and abs(final) < 0.1:
        return 'static'
    elif final > 0 and total < 0:
        return 'cycling'
    else:
        return 'ambiguous'


# ═══════════════════════════════════════════════════════════════════════
# TEST: Run against the real music test
# ═══════════════════════════════════════════════════════════════════════

def main():
    from real_music_test import SONGS, V as song_voicings, feel_match
    
    print("=" * 78)
    print("  🧠 EXPECTATION LAYER — Does anticipation fix the failures?")
    print("=" * 78)
    
    # Build voicing dict
    voicings = dict(VOICINGS)
    voicings.update(song_voicings)
    
    correct_old = 0
    correct_new = 0
    total = 0
    improvements = []
    regressions = []
    
    print(f"\n  {'Song':<42s}  {'Expected':<16s}  {'Old':<16s}  {'New':<16s}  {'Δ'}")
    print(f"  {'─' * 100}")
    
    for name, info in SONGS.items():
        expected = info['expected_feel']
        chord_names = info['chords']
        
        # Old classification (import from real_music_test logic)
        analysis = analyze_with_expectation(chord_names, voicings)
        
        # Old classifier (gravity only)
        old_pred = _classify_old(analysis)
        old_match = feel_match(old_pred, expected)
        
        # New classifier (gravity + expectation)
        new_pred = classify_with_expectation(analysis)
        new_match = feel_match(new_pred, expected)
        
        if old_match: correct_old += 1
        if new_match: correct_new += 1
        total += 1
        
        delta = ""
        if new_match and not old_match:
            delta = "✨ FIXED"
            improvements.append(name)
        elif old_match and not new_match:
            delta = "💥 BROKE"
            regressions.append(name)
        elif new_match:
            delta = "✅"
        else:
            delta = "❌"
        
        print(f"  {name:<42s}  {expected:<16s}  {old_pred:<16s}  {new_pred:<16s}  {delta}")
        
        # Show expectation details for interesting cases
        if analysis['expectation_debt'] > 0.3 or analysis['is_loop']:
            debt_str = " → ".join(f"{d:.2f}" for d in analysis['debt_trajectory'])
            schema_str = f"  schema={analysis['schema']}" if analysis['schema'] else ""
            impl_str = f"  implies={analysis['final_implied_chord']}" if analysis['final_implied_chord'] else ""
            print(f"    ↳ debt=[{debt_str}]  final_impl={analysis['final_implication']:.2f}{schema_str}{impl_str}")
    
    print(f"\n  {'─' * 78}")
    print(f"\n  OLD accuracy:  {correct_old}/{total} = {correct_old/total:.0%}")
    print(f"  NEW accuracy:  {correct_new}/{total} = {correct_new/total:.0%}")
    
    if improvements:
        print(f"\n  ✨ Fixed: {', '.join(improvements)}")
    if regressions:
        print(f"\n  💥 Broke: {', '.join(regressions)}")
    
    if correct_new > correct_old:
        print(f"\n  🎯 Expectation layer improves accuracy by {correct_new - correct_old} songs!")
    elif correct_new == correct_old:
        print(f"\n  ➡️  Same accuracy — expectation layer doesn't help/hurt")
    else:
        print(f"\n  ⚠️  Expectation layer made things WORSE. Investigate.")
    
    return correct_new, total


def _classify_old(analysis):
    """Old classifier from real_music_test.py (gravity only)."""
    total = analysis['total_resolution']
    final = analysis['final_resolution']
    # Approximate net gravity change
    gravs = analysis['gravities']
    net_grav = gravs[-1] - gravs[0] if len(gravs) >= 2 else 0
    
    if final > 0.3 and total > 0.3:
        return 'resolving'
    elif final > 0.1 and total > 0:
        return 'partial_resolve'
    elif final < -0.1 or net_grav > 0.05:
        return 'tension_building'
    elif abs(total) < 0.15 and abs(final) < 0.1:
        return 'static'
    elif final > 0 and total < 0:
        return 'cycling'
    else:
        return 'ambiguous'


if __name__ == '__main__':
    main()
