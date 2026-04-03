#!/usr/bin/env python3
"""
🎵 REAL MUSIC TEST — Does tonal gravity predict resolution in actual songs?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The tonal gravity model gets perfect ranking on textbook cadences.
But textbook cadences are textbook for a reason — they're idealized.

Real music does weird things:
- Deceptive cadences that feel satisfying anyway (Radiohead)
- Plagal cadences that feel more final than authentic (gospel, rock)
- Progressions that never truly resolve but feel complete (modal jazz)
- The "Axis of Awesome" progression that works in every song ever

Question: Does our model's resolution score track with musical function
in the wild? Or is it just a fancy way to confirm what theory textbooks
already say?

Striker, April 2026
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tonal_gravity import (
    tonal_resolution, chord_gravity, gravity_delta,
    tendency_resolution, bass_resolution, VOICINGS
)
from transition_entropy import transition_entropy

# ═══════════════════════════════════════════════════════════════════════
# REAL SONG PROGRESSIONS
# ═══════════════════════════════════════════════════════════════════════
# Voicings in C major for comparability. Each entry has:
#   - progression (chord symbols mapped to VOICINGS)
#   - key context
#   - what it SHOULD feel like (ground truth from musical intuition)
#   - the actual song/genre context

# Extended voicing dictionary for progressions we need
V = dict(VOICINGS)
V.update({
    # Borrowed chords / chromatic
    'bVII':  [10, 14, 17, 22],  # Bb major (borrowed from mixolydian)
    'bVI':   [8, 12, 15, 20],   # Ab major (borrowed from minor)
    'bIII':  [3, 7, 10, 15],    # Eb major
    'v':     [7, 10, 14, 19],   # G minor (borrowed from parallel minor)
    'IV/IV': [10, 14, 17, 22],  # secondary dominant area (Bb as IV of F)
    '#iv°':  [6, 9, 12, 18],    # raised 4 diminished
})


SONGS = {
    # ── Category: Strong resolvers ──
    'Let It Be (IV-I ending)': {
        'chords': ['IV', 'I'],
        'context': 'Beatles — the repeated "let it be" always lands on I after IV',
        'expected_feel': 'resolving',  # Plagal "amen" cadence
        'strength': 'strong',
    },
    'Hey Jude (V-I climax)': {
        'chords': ['V', 'I'],
        'context': 'Beatles — the big "na na na" vamp resolves V to I',
        'expected_feel': 'resolving',
        'strength': 'strong',
    },
    'ii-V-I Jazz Standard': {
        'chords': ['ii', 'V', 'I'],
        'context': 'The most common jazz cadence. Autumn Leaves, All The Things You Are, etc.',
        'expected_feel': 'resolving',
        'strength': 'strong',
    },
    'Gospel Plagal (IV-I)': {
        'chords': ['vi', 'IV', 'I'],
        'context': 'Gospel music — the "amen" feeling. Often feels MORE final than V-I in context.',
        'expected_feel': 'resolving',
        'strength': 'strong',
    },

    # ── Category: Partial / ambiguous resolution ──
    'Axis of Awesome (I-V-vi-IV)': {
        'chords': ['I', 'V', 'vi', 'IV'],
        'context': 'The most common pop progression. Loops forever. Never fully resolves but feels complete.',
        'expected_feel': 'cycling',  # Not resolving, not tense — just moving
        'strength': 'neutral',
    },
    'Pachelbel Canon (I-V-vi-iii-IV-I-IV-V)': {
        'chords': ['I', 'V', 'vi', 'iii', 'IV', 'I', 'IV', 'V'],
        'context': 'The canon progression. Descending bass gives forward momentum. Ends on V = open.',
        'expected_feel': 'tension_building',
        'strength': 'moderate',
    },
    '50s Doo-Wop (I-vi-IV-V)': {
        'chords': ['I', 'vi', 'IV', 'V'],
        'context': 'Stand By Me, etc. Classic cycling. Ends on V = wants to go back to I.',
        'expected_feel': 'tension_building',
        'strength': 'moderate',
    },
    'Creep Radiohead (I-III-IV-iv)': {
        'chords': ['I', 'iii', 'IV', 'vi'],  # Approximating — actual uses III major and iv minor
        'context': 'Radiohead Creep. I→III→IV→iv. The iv at the end is the gut punch. Approximating with diatonic.',
        'expected_feel': 'tension_building',
        'strength': 'moderate',
    },

    # ── Category: Deceptive / non-resolving ──
    'Deceptive Jazz (ii-V-vi)': {
        'chords': ['ii', 'V', 'vi'],
        'context': 'Jazz deceptive cadence. You expect I but get vi. Surprise but not wrong.',
        'expected_feel': 'deceptive',
        'strength': 'weak',
    },
    'Andalusian Cadence (vi-V-IV-iii)': {
        'chords': ['vi', 'V', 'IV', 'iii'],
        'context': 'Flamenco, Bm-A-G-F#. Descending. Lands on iii which is unstable. Haunting, not resolved.',
        'expected_feel': 'tension_building',
        'strength': 'weak',
    },
    'Stairway to Heaven End (vi-IV-I-V)': {
        'chords': ['vi', 'IV', 'I', 'V'],
        'context': 'Led Zeppelin stairway ending phrase. Passes through I but ends on V. Open.',
        'expected_feel': 'tension_building',
        'strength': 'moderate',
    },

    # ── Category: Modal / non-functional ──
    'Dorian Vamp (i-IV in minor feel)': {
        'chords': ['vi', 'ii'],  # Am-Dm in C = dorian-ish feel
        'context': 'Dorian vamp. Two minor chords trading. Miles Davis "So What" energy. No resolution.',
        'expected_feel': 'static',
        'strength': 'none',
    },
    'Rock Shuttle (I-bVII-IV-I)': {
        'chords': ['I', 'V', 'IV', 'I'],  # Approximating bVII as V since we lack borrowed chords
        'context': 'Rock mixolydian. AC/DC territory. I→bVII→IV→I. Approximating. Gravity is flat.',
        'expected_feel': 'resolving',
        'strength': 'moderate',
    },

    # ── Category: Maximum tension ──
    'Half Cadence Baroque (I-ii-V)': {
        'chords': ['I', 'ii', 'V'],
        'context': 'Classical half cadence. Ends on V. Maximum "to be continued" energy.',
        'expected_feel': 'tension_building',
        'strength': 'strong_tension',
    },
    'Circle of Fifths (vi-ii-V-I)': {
        'chords': ['vi', 'ii', 'V', 'I'],
        'context': 'Full circle of fifths descent. Each step builds then releases. Maximum resolution.',
        'expected_feel': 'resolving',
        'strength': 'strong',
    },
    'Turnaround (I-vi-ii-V)': {
        'chords': ['I', 'vi', 'ii', 'V'],
        'context': 'Jazz turnaround. Goes FROM stable TO unstable. Ends on V wanting I.',
        'expected_feel': 'tension_building',
        'strength': 'strong_tension',
    },
}


def analyze_progression(name, info):
    """Full analysis of a progression."""
    chords = info['chords']
    voicings = [V[c] for c in chords]
    
    steps = []
    for i in range(len(voicings) - 1):
        res = tonal_resolution(voicings[i], voicings[i+1])
        te = transition_entropy(voicings[i], voicings[i+1])
        steps.append({
            'from': chords[i],
            'to': chords[i+1],
            'resolution': res['resolution'],
            'gravity_delta': res['gravity_delta'],
            'tendency': res['tendency'],
            'bass_score': res['bass_score'],
            'surprise': te,
        })
    
    # Key metrics
    total_resolution = sum(s['resolution'] for s in steps)
    final_step_resolution = steps[-1]['resolution'] if steps else 0
    total_surprise = sum(s['surprise'] for s in steps)
    max_step_resolution = max(s['resolution'] for s in steps) if steps else 0
    min_step_resolution = min(s['resolution'] for s in steps) if steps else 0
    
    # Gravity trajectory
    gravities = [chord_gravity(v) for v in voicings]
    gravity_start = gravities[0]
    gravity_end = gravities[-1]
    gravity_range = max(gravities) - min(gravities)
    
    # Net direction: does gravity decrease overall? (= resolution)
    net_gravity_change = gravity_end - gravity_start
    
    return {
        'steps': steps,
        'total_resolution': total_resolution,
        'final_step_resolution': final_step_resolution,
        'total_surprise': total_surprise,
        'max_resolution': max_step_resolution,
        'min_resolution': min_step_resolution,
        'gravity_start': gravity_start,
        'gravity_end': gravity_end,
        'gravity_range': gravity_range,
        'net_gravity_change': net_gravity_change,
        'gravities': gravities,
    }


def classify_feel(analysis):
    """
    What does the model PREDICT this progression feels like?
    Based purely on the numbers, not the expected answer.
    """
    total = analysis['total_resolution']
    final = analysis['final_step_resolution']
    net_grav = analysis['net_gravity_change']
    
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


def feel_match(predicted, expected):
    """Fuzzy matching of predicted vs expected feel."""
    # Exact match
    if predicted == expected:
        return True
    # Partial matches
    matches = {
        ('partial_resolve', 'resolving'): True,  # Close enough
        ('partial_resolve', 'deceptive'): True,   # Deceptive = partial resolve
        ('ambiguous', 'cycling'): True,
        ('ambiguous', 'static'): True,
        ('cycling', 'static'): True,
        ('tension_building', 'cycling'): False,  # These are distinct
        ('resolving', 'tension_building'): False,
    }
    return matches.get((predicted, expected), False)


def main():
    print("=" * 78)
    print("  🎵 REAL MUSIC TEST — Tonal Gravity vs Actual Songs")
    print("=" * 78)
    
    results = {}
    
    for name, info in SONGS.items():
        analysis = analyze_progression(name, info)
        predicted = classify_feel(analysis)
        results[name] = {**analysis, 'predicted': predicted, 'info': info}
    
    # ── Print detailed results ──
    categories = {
        'Strong resolvers': [n for n, i in SONGS.items() if i['strength'] == 'strong'],
        'Partial / ambiguous': [n for n, i in SONGS.items() if i['strength'] in ('neutral', 'moderate')],
        'Weak / deceptive': [n for n, i in SONGS.items() if i['strength'] == 'weak'],
        'Static / modal': [n for n, i in SONGS.items() if i['strength'] == 'none'],
        'Maximum tension': [n for n, i in SONGS.items() if i['strength'] == 'strong_tension'],
    }
    
    for cat_name, song_names in categories.items():
        if not song_names:
            continue
        print(f"\n\n{'─' * 78}")
        print(f"  {cat_name.upper()}")
        print(f"{'─' * 78}")
        
        for name in song_names:
            r = results[name]
            info = r['info']
            chords = info['chords']
            expected = info['expected_feel']
            predicted = r['predicted']
            match = feel_match(predicted, expected)
            
            icon = "✅" if match else "❌"
            
            print(f"\n  {icon} {name}")
            print(f"     {' → '.join(chords)}")
            print(f"     {info['context']}")
            
            # Step-by-step
            for s in r['steps']:
                arrow = "↘" if s['resolution'] > 0.05 else "↗" if s['resolution'] < -0.05 else "→"
                print(f"     {s['from']:>5s} {arrow} {s['to']:<5s}  "
                      f"res={s['resolution']:+.3f}  "
                      f"gΔ={s['gravity_delta']:+.3f}  "
                      f"bass={s['bass_score']:.2f}  "
                      f"T(E)={s['surprise']:.3f}")
            
            # Gravity trajectory visualization
            gravs = r['gravities']
            grav_str = " → ".join(f"{g:.2f}" for g in gravs)
            print(f"     Gravity: [{grav_str}]")
            print(f"     Σres={r['total_resolution']:+.3f}  "
                  f"final={r['final_step_resolution']:+.3f}  "
                  f"ΔG={r['net_gravity_change']:+.3f}")
            print(f"     Expected: {expected}  |  Model says: {predicted}")
    
    # ── Summary statistics ──
    print(f"\n\n{'=' * 78}")
    print(f"  SUMMARY: How well does the model track musical intuition?")
    print(f"{'=' * 78}")
    
    correct = 0
    total = len(results)
    
    print(f"\n  {'Song':<45s}  {'Expected':<18s}  {'Predicted':<18s}  {'Match'}")
    print(f"  {'─' * 95}")
    
    for name, r in results.items():
        expected = r['info']['expected_feel']
        predicted = r['predicted']
        match = feel_match(predicted, expected)
        if match:
            correct += 1
        icon = "✅" if match else "❌"
        print(f"  {name:<45s}  {expected:<18s}  {predicted:<18s}  {icon}")
    
    acc = correct / total if total > 0 else 0
    print(f"\n  Accuracy: {correct}/{total} = {acc:.0%}")
    
    # ── The interesting part: what do the NUMBERS tell us? ──
    print(f"\n\n{'=' * 78}")
    print(f"  RANKINGS: Resolution score across all progressions")
    print(f"{'=' * 78}")
    
    ranked = sorted(results.items(), key=lambda x: x[1]['total_resolution'], reverse=True)
    
    print(f"\n  {'#':<4s} {'Song':<45s}  {'Σres':>8s}  {'final':>8s}  {'Feel'}")
    print(f"  {'─' * 78}")
    
    for i, (name, r) in enumerate(ranked, 1):
        feel = r['info']['expected_feel']
        print(f"  {i:<4d} {name:<45s}  {r['total_resolution']:>+8.3f}  {r['final_step_resolution']:>+8.3f}  {feel}")
    
    # ── The real question ──
    print(f"\n\n{'=' * 78}")
    print(f"  THE REAL QUESTION")
    print(f"{'=' * 78}")
    
    # Do strongly resolving songs rank higher than non-resolving ones?
    resolving_scores = [r['total_resolution'] for r in results.values() 
                        if r['info']['expected_feel'] == 'resolving']
    tension_scores = [r['total_resolution'] for r in results.values()
                      if r['info']['expected_feel'] == 'tension_building']
    
    if resolving_scores and tension_scores:
        avg_resolve = sum(resolving_scores) / len(resolving_scores)
        avg_tension = sum(tension_scores) / len(tension_scores)
        
        print(f"\n  Average resolution score:")
        print(f"    Resolving songs:        {avg_resolve:+.3f}")
        print(f"    Tension-building songs:  {avg_tension:+.3f}")
        print(f"    Separation:             {avg_resolve - avg_tension:+.3f}")
        
        if avg_resolve > avg_tension:
            print(f"\n  ✅ Model correctly ranks resolving > tension-building")
            print(f"     Ratio: {avg_resolve / max(abs(avg_tension), 0.001):.1f}x")
        else:
            print(f"\n  ❌ Model fails to separate resolving from tension-building")
    
    # Final verdict
    print(f"\n  {'─' * 60}")
    if acc >= 0.7:
        print(f"  🎯 Model captures musical intuition reasonably well ({acc:.0%})")
        print(f"  The tonal gravity framework extends beyond textbook examples.")
    elif acc >= 0.5:
        print(f"  🔶 Model partially captures musical reality ({acc:.0%})")
        print(f"  Works for clear cases but misses nuance in ambiguous progressions.")
    else:
        print(f"  ⚠️  Model struggles with real music ({acc:.0%})")
        print(f"  Good for textbook cadences but musical reality is more complex.")
    
    return results


if __name__ == '__main__':
    results = main()
