#!/usr/bin/env python3
"""
🎼 HARMONIC ANALYSIS PIPELINE — The full stack, unified
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This chains every module in the consonance project into one coherent
analysis. Feed it a chord progression, get back everything:

  Layer 1: HARMONIC ENTROPY — raw consonance of each chord (intervals)
  Layer 2: CHORD ENTROPY — pairwise entropy, variance → phase space position
  Layer 3: TRANSITION ENTROPY — surprise of each harmonic move
  Layer 4: TONAL GRAVITY — gravitational pull toward tonic
  Layer 5: EXPECTATION — listener anticipation, debt, schema detection
  Layer 6: NARRATIVE — what the progression "means" musically

Each layer builds on the ones below. The pipeline outputs:
- Per-chord analysis (static properties)
- Per-transition analysis (movement properties)
- Trajectory (path through entropy/gravity space)
- Classification (resolving / tension / cycling / static / deceptive)
- Narrative (human-readable musical description)

This is the thing I've been building toward. Not just "does V resolve to I?"
but "what is this entire progression DOING, musically?"

Striker, April 2026
"""

import math
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from harmonic_entropy import harmonic_entropy
from chord_entropy import chord_pairwise_entropy, entropy_variance
from transition_entropy import (
    transition_entropy as calc_transition_entropy,
    voice_leading_entropy,
    resolution_delta,
    chord_harmonic_entropy,
)
from tonal_gravity import (
    tonal_resolution, chord_gravity, gravity_delta,
    tendency_resolution, bass_resolution, VOICINGS as TG_VOICINGS
)
from expectation_layer import (
    analyze_with_expectation, classify_with_expectation,
    implication_strength, expectation_debt, detect_schema,
    IMPLICATIONS
)


# ═══════════════════════════════════════════════════════════════════════
# MASTER VOICING DICTIONARY
# ═══════════════════════════════════════════════════════════════════════
# Unified voicings from all modules. 4-voice close position.

VOICINGS = dict(TG_VOICINGS)
VOICINGS.update({
    # Borrowed / chromatic / modal
    'bVII':  [10, 14, 17, 22],
    'bVI':   [8, 12, 15, 20],
    'bIII':  [3, 7, 10, 15],
    'bII':   [1, 5, 8, 13],
    'v':     [7, 10, 14, 19],
    'iv':    [5, 8, 12, 17],
    '#IVo':  [6, 9, 12, 18],
    'VII':   [11, 14, 17, 23],
    'III':   [4, 7, 11, 16],
    'VI':    [9, 13, 16, 21],
    'bV':    [6, 10, 13, 18],
    'i':     [0, 3, 7, 12],
    # 7th chords
    'I7':    [0, 4, 7, 11],
    'ii7':   [2, 5, 9, 12],
    'iii7':  [4, 7, 11, 14],
    'IV7':   [5, 9, 12, 16],
    'V7':    [7, 11, 14, 17],
    'vi7':   [9, 12, 16, 19],
    'viio7': [11, 14, 17, 21],
})


# ═══════════════════════════════════════════════════════════════════════
# LAYER 1 & 2: STATIC CHORD ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def analyze_chord_static(voicing: List[int], name: str = "?") -> Dict:
    """
    Everything we know about a single chord in isolation.
    
    Returns:
        harmonic_entropy: overall consonance (lower = more consonant)
        pairwise_entropy: avg pairwise interval entropy
        entropy_variance: spread of pairwise entropies (function indicator)
        gravity: tonal pull (lower = closer to tonic)
        implication: what this chord expects next
    """
    h_entropy = chord_harmonic_entropy(voicing)
    p_entropy = chord_pairwise_entropy(voicing)
    e_variance = entropy_variance(voicing)
    gravity = chord_gravity(voicing)
    impl_strength, impl_target = implication_strength(name)
    
    return {
        'name': name,
        'voicing': voicing,
        'harmonic_entropy': h_entropy,
        'pairwise_entropy': p_entropy,
        'entropy_variance': e_variance,
        'gravity': gravity,
        'implication_strength': impl_strength,
        'implied_target': impl_target,
        # Phase space coordinates
        'phase_x': p_entropy,        # consonance axis
        'phase_y': e_variance,       # function axis (low=tonic, high=dominant)
    }


# ═══════════════════════════════════════════════════════════════════════
# LAYER 3 & 4: TRANSITION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def analyze_transition(
    from_voicing: List[int], to_voicing: List[int],
    from_name: str = "?", to_name: str = "?"
) -> Dict:
    """
    Everything about the MOVEMENT from one chord to the next.
    
    Returns:
        transition_entropy: how surprising is this move?
        voice_leading_entropy: how smooth is the voice motion?
        resolution_delta: does dissonance increase or decrease?
        tonal_resolution: combined gravity-based resolution score
        gravity_delta: change in gravitational pull
        tendency: tendency-tone resolution score
        bass: bass motion resolution score
    """
    t_entropy = calc_transition_entropy(from_voicing, to_voicing)
    vl_result = voice_leading_entropy(from_voicing, to_voicing)
    # voice_leading_entropy returns (entropy, total_motion, num_voices) tuple
    vl_entropy = vl_result[0] if isinstance(vl_result, tuple) else vl_result
    res_delta = resolution_delta(from_voicing, to_voicing)
    tonal = tonal_resolution(from_voicing, to_voicing)
    
    return {
        'from': from_name,
        'to': to_name,
        'transition_entropy': t_entropy,
        'voice_leading_entropy': vl_entropy,
        'resolution_delta': res_delta,
        'tonal_resolution': tonal['resolution'],
        'gravity_delta': tonal['gravity_delta'],
        'tendency': tonal['tendency'],
        'bass_score': tonal['bass_score'],
        # Trajectory coordinates
        'traj_x': t_entropy,           # surprise axis
        'traj_y': tonal['resolution'],  # resolution axis
        'traj_z': vl_entropy,           # smoothness axis
    }


# ═══════════════════════════════════════════════════════════════════════
# LAYER 5: EXPECTATION & SCHEMA
# ═══════════════════════════════════════════════════════════════════════

def analyze_expectation(chord_names: List[str]) -> Dict:
    """
    Listener-model analysis: what does the ear expect?
    
    Returns:
        debt: unresolved expectation at end
        debt_trajectory: debt over time
        schema: detected schema (axis, turnaround, closed_form, etc.)
        is_loop: does this feel like it cycles?
        final_implication: how strongly the last chord demands continuation
    """
    debt, trajectory = expectation_debt(chord_names)
    schema, is_loop, loop_tension = detect_schema(chord_names)
    final_impl, final_target = implication_strength(chord_names[-1])
    
    return {
        'debt': debt,
        'debt_trajectory': trajectory,
        'schema': schema,
        'is_loop': is_loop,
        'loop_tension': loop_tension,
        'final_implication': final_impl,
        'final_implied': final_target,
    }


# ═══════════════════════════════════════════════════════════════════════
# LAYER 6: NARRATIVE
# ═══════════════════════════════════════════════════════════════════════

def generate_narrative(
    chords: List[Dict], transitions: List[Dict],
    expectation: Dict, classification: str
) -> str:
    """
    Turn numbers into a musical story.
    
    Not a summary — a narrative of what the ear experiences
    as this progression unfolds.
    """
    parts = []
    n = len(chords)
    
    # Opening
    first = chords[0]
    if first['gravity'] < 0.15:
        parts.append(f"Begins at home ({first['name']}) — stable, grounded.")
    elif first['gravity'] > 0.3:
        parts.append(f"Starts away from home ({first['name']}) — already in motion.")
    else:
        parts.append(f"Opens on {first['name']} — neutral territory.")
    
    # Journey
    peak_tension_idx = 0
    peak_tension = 0
    for i, t in enumerate(transitions):
        res = t['tonal_resolution']
        surprise = t['transition_entropy']
        
        if res > 0.4:
            parts.append(f"  {t['from']} → {t['to']}: strong resolution (gravity pulls home)")
        elif res > 0.1:
            parts.append(f"  {t['from']} → {t['to']}: gentle settling")
        elif res < -0.1:
            parts.append(f"  {t['from']} → {t['to']}: tension increases")
            if abs(res) > peak_tension:
                peak_tension = abs(res)
                peak_tension_idx = i
        else:
            if surprise > 0.5:
                parts.append(f"  {t['from']} → {t['to']}: lateral move (surprising but not tense)")
            else:
                parts.append(f"  {t['from']} → {t['to']}: drifting")
    
    # Ending
    last = chords[-1]
    debt = expectation['debt']
    
    if classification == 'resolving':
        if debt < 0.1:
            parts.append(f"Lands on {last['name']} — resolved, complete. The ear is satisfied.")
        else:
            parts.append(f"Resolves to {last['name']}, though some expectation lingers.")
    elif classification == 'tension_building':
        if expectation['final_implication'] > 0.5:
            parts.append(
                f"Ends on {last['name']} — which demands {expectation['final_implied']}. "
                f"The listener is left leaning forward."
            )
        else:
            parts.append(f"Ends unresolved on {last['name']}. Tension hangs in the air.")
    elif classification == 'cycling':
        parts.append(
            f"Ends on {last['name']} — but wants to loop back. "
            f"Not resolved, not tense — perpetual motion."
        )
    elif classification == 'static':
        if expectation.get('final_implication', 0) > 0.3:
            parts.append(f"Ends on {last['name']} — suspended. Wants to move but doesn't.")
        else:
            parts.append(f"Ends on {last['name']} — neither arriving nor departing. Modal float.")
    elif classification == 'deceptive':
        parts.append(
            f"Lands on {last['name']} — not where the ear expected. "
            f"Surprise without chaos."
        )
    elif classification == 'partial_resolve':
        parts.append(
            f"Lands on {last['name']} — partially resolved. "
            f"Some tension remains, but not uncomfortably so."
        )
    else:
        parts.append(f"Ends on {last['name']} — ambiguous. The ear isn't sure what just happened.")
    
    # Schema
    if expectation['schema']:
        schema_names = {
            'axis': 'the Axis of Awesome progression (I-V-vi-IV)',
            '50s_turnaround': 'the classic 50s turnaround',
            'jazz_turnaround': 'a jazz turnaround',
            'pop_loop': 'a modern pop loop',
            'anthem': 'an arena anthem pattern',
            'rock_shuttle': 'a rock mixolydian shuttle',
            'closed_form': 'a closed form (returns to start)',
            'implied_loop': 'an implied loop (ending wants beginning)',
        }
        schema_label = schema_names.get(expectation['schema'], expectation['schema'])
        parts.append(f"  Schema: {schema_label}")
    
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════
# THE PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def analyze(
    chord_names: List[str],
    voicings_dict: Optional[Dict] = None,
    verbose: bool = False
) -> Dict:
    """
    Full harmonic analysis pipeline.
    
    Takes a progression as chord names (e.g., ['I', 'V', 'vi', 'IV'])
    Returns a complete multi-layer analysis.
    
    This is the one function that does everything.
    """
    V = voicings_dict or VOICINGS
    voicings = [V[c] for c in chord_names]
    
    # Layer 1-2: Static chord analysis
    chord_analyses = [
        analyze_chord_static(v, name)
        for v, name in zip(voicings, chord_names)
    ]
    
    # Layer 3-4: Transition analysis
    transition_analyses = [
        analyze_transition(
            voicings[i], voicings[i+1],
            chord_names[i], chord_names[i+1]
        )
        for i in range(len(voicings) - 1)
    ]
    
    # Layer 5: Expectation
    exp = analyze_expectation(chord_names)
    
    # Aggregate metrics
    total_resolution = sum(t['tonal_resolution'] for t in transition_analyses)
    final_resolution = transition_analyses[-1]['tonal_resolution'] if transition_analyses else 0
    avg_surprise = (
        sum(t['transition_entropy'] for t in transition_analyses) / len(transition_analyses)
        if transition_analyses else 0
    )
    avg_smoothness = (
        sum(t['voice_leading_entropy'] for t in transition_analyses) / len(transition_analyses)
        if transition_analyses else 0
    )
    gravity_arc = [c['gravity'] for c in chord_analyses]
    entropy_arc = [c['harmonic_entropy'] for c in chord_analyses]
    
    # Layer 5b: Classification
    # Build the analysis dict that classify_with_expectation expects
    exp_analysis = analyze_with_expectation(chord_names, V)
    classification = classify_with_expectation(exp_analysis)
    
    # Layer 6: Narrative
    narrative = generate_narrative(chord_analyses, transition_analyses, exp, classification)
    
    result = {
        # Per-chord
        'chords': chord_analyses,
        # Per-transition  
        'transitions': transition_analyses,
        # Expectation
        'expectation': exp,
        # Aggregates
        'total_resolution': total_resolution,
        'final_resolution': final_resolution,
        'avg_surprise': avg_surprise,
        'avg_smoothness': avg_smoothness,
        'gravity_arc': gravity_arc,
        'entropy_arc': entropy_arc,
        # Classification
        'classification': classification,
        # Narrative
        'narrative': narrative,
        # Trajectory (for plotting)
        'trajectory': {
            'phase_space': [(c['phase_x'], c['phase_y']) for c in chord_analyses],
            'transition_space': [
                (t['traj_x'], t['traj_y'], t['traj_z']) 
                for t in transition_analyses
            ],
            'gravity': gravity_arc,
            'entropy': entropy_arc,
            'debt': exp['debt_trajectory'],
        }
    }
    
    if verbose:
        print_analysis(result, chord_names)
    
    return result


def print_analysis(result: Dict, chord_names: List[str]):
    """Pretty-print a full analysis."""
    print("=" * 78)
    print(f"  🎼 HARMONIC ANALYSIS: {' → '.join(chord_names)}")
    print("=" * 78)
    
    # Chord properties
    print(f"\n  ── Per-chord properties ──")
    print(f"  {'Chord':<8s} {'H(ent)':<8s} {'Gravity':<8s} {'Variance':<9s} {'Implies'}")
    print(f"  {'─' * 55}")
    for c in result['chords']:
        impl = f"→{c['implied_target']} ({c['implication_strength']:.2f})" if c['implied_target'] else "—"
        print(f"  {c['name']:<8s} {c['harmonic_entropy']:<8.3f} {c['gravity']:<8.3f} "
              f"{c['entropy_variance']:<9.4f} {impl}")
    
    # Transitions
    print(f"\n  ── Transitions ──")
    print(f"  {'Move':<12s} {'Resolve':<9s} {'Surprise':<9s} {'Smooth':<9s} {'Gravity Δ'}")
    print(f"  {'─' * 55}")
    for t in result['transitions']:
        move = f"{t['from']}→{t['to']}"
        print(f"  {move:<12s} {t['tonal_resolution']:>+7.3f}  {t['transition_entropy']:>7.3f}  "
              f"{t['voice_leading_entropy']:>7.3f}  {t['gravity_delta']:>+7.3f}")
    
    # Arcs
    print(f"\n  ── Trajectories ──")
    grav_str = " → ".join(f"{g:.2f}" for g in result['gravity_arc'])
    ent_str = " → ".join(f"{e:.3f}" for e in result['entropy_arc'])
    debt_str = " → ".join(f"{d:.2f}" for d in result['expectation']['debt_trajectory'])
    print(f"  Gravity:     [{grav_str}]")
    print(f"  Entropy:     [{ent_str}]")
    print(f"  Exp. debt:   [{debt_str}]")
    
    # Summary
    print(f"\n  ── Summary ──")
    print(f"  Total resolution:  {result['total_resolution']:+.3f}")
    print(f"  Final resolution:  {result['final_resolution']:+.3f}")
    print(f"  Avg surprise:      {result['avg_surprise']:.3f}")
    print(f"  Avg smoothness:    {result['avg_smoothness']:.3f}")
    print(f"  Expectation debt:  {result['expectation']['debt']:.3f}")
    if result['expectation']['schema']:
        print(f"  Schema:            {result['expectation']['schema']}")
    print(f"  Classification:    {result['classification'].upper()}")
    
    # Narrative
    print(f"\n  ── Narrative ──")
    for line in result['narrative'].split('\n'):
        print(f"  {line}")
    
    print()


# ═══════════════════════════════════════════════════════════════════════
# COMPARISON: Analyze multiple progressions side by side
# ═══════════════════════════════════════════════════════════════════════

def compare(progressions: Dict[str, List[str]], verbose: bool = True) -> Dict:
    """
    Analyze and compare multiple progressions.
    
    Args:
        progressions: {name: [chord_names]}
    
    Returns:
        Dict of analyses keyed by name, plus comparison metrics.
    """
    results = {}
    for name, chords in progressions.items():
        results[name] = analyze(chords)
    
    if verbose:
        print("=" * 78)
        print("  🎼 COMPARATIVE HARMONIC ANALYSIS")
        print("=" * 78)
        
        print(f"\n  {'Progression':<35s} {'Class':<16s} {'Σres':>7s} {'Debt':>6s} {'Surp':>6s}")
        print(f"  {'─' * 78}")
        
        # Sort by total resolution (most resolving first)
        ranked = sorted(results.items(), key=lambda x: x[1]['total_resolution'], reverse=True)
        
        for name, r in ranked:
            chords = progressions[name]
            label = ' → '.join(chords)
            if len(label) > 30:
                label = label[:27] + "..."
            print(f"  {name:<35s} {r['classification']:<16s} "
                  f"{r['total_resolution']:>+7.3f} {r['expectation']['debt']:>6.2f} "
                  f"{r['avg_surprise']:>6.3f}")
        
        # Print narratives
        for name, r in ranked:
            print(f"\n  ── {name} ──")
            for line in r['narrative'].split('\n'):
                print(f"  {line}")
    
    return results


# ═══════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════

def demo():
    """Show what the pipeline can do."""
    
    print("\n" + "━" * 78)
    print("  PART 1: Single progression deep-dive")
    print("━" * 78)
    
    # The classic: ii-V-I
    analyze(['ii', 'V', 'I'], verbose=True)
    
    # Something more complex
    analyze(['I', 'vi', 'IV', 'V'], verbose=True)
    
    print("\n" + "━" * 78)
    print("  PART 2: Comparative analysis — cadence types")
    print("━" * 78)
    
    compare({
        'Authentic (V→I)':        ['V', 'I'],
        'Plagal (IV→I)':          ['IV', 'I'],
        'Deceptive (V→vi)':       ['V', 'vi'],
        'Half (I→V)':             ['I', 'V'],
        'Full ii-V-I':            ['ii', 'V', 'I'],
        'Circle of 5ths':         ['vi', 'ii', 'V', 'I'],
    })
    
    print("\n" + "━" * 78)
    print("  PART 3: Comparative analysis — famous progressions")
    print("━" * 78)
    
    compare({
        'Axis of Awesome':        ['I', 'V', 'vi', 'IV'],
        '50s Doo-Wop':            ['I', 'vi', 'IV', 'V'],
        'Pachelbel Canon':        ['I', 'V', 'vi', 'iii', 'IV', 'I', 'IV', 'V'],
        'Jazz Turnaround':        ['I', 'vi', 'ii', 'V'],
        'Andalusian':             ['vi', 'V', 'IV', 'iii'],
        'Let It Be (IV→I)':       ['IV', 'I'],
    })


if __name__ == '__main__':
    demo()
