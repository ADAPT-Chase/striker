#!/usr/bin/env python3
"""
🔨 STRESS TEST — Push the expectation layer to its limits
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

100% on 16 songs is suspicious. Either the model is genuinely good or
we're overfitting to easy cases. Let's throw hard stuff at it:

1. Jazz reharmonizations (altered dominants, tritone subs)
2. Chromatic mediants (film score language)
3. Deceptive resolutions that FEEL resolving
4. Progressions that change key mid-stream
5. Ambiguous progressions that musicologists argue about
6. Really short (2 chord) and really long (8+ chord) progressions

Striker, April 2026
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tonal_gravity import VOICINGS, tonal_resolution, chord_gravity
from expectation_layer import (
    analyze_with_expectation, classify_with_expectation,
    implication_strength, expectation_debt
)
from real_music_test import feel_match

# Extended voicings for stress test
V = dict(VOICINGS)
V.update({
    # Borrowed / chromatic
    'bVII':  [10, 14, 17, 22],  # Bb major
    'bVI':   [8, 12, 15, 20],   # Ab major
    'bIII':  [3, 7, 10, 15],    # Eb major
    'bII':   [1, 5, 8, 13],     # Db major (Neapolitan)
    'v':     [7, 10, 14, 19],   # G minor
    'iv':    [5, 8, 12, 17],    # F minor
    '#IVo':  [6, 9, 12, 18],    # F# diminished
    'VII':   [11, 14, 17, 23],  # B major (in C — chromatic mediant)
    'III':   [4, 7, 11, 16],    # E major (chromatic mediant)
    'VI':    [9, 13, 16, 21],   # A major
    'bV':    [6, 10, 13, 18],   # Gb major (tritone sub)
    'i':     [0, 3, 7, 12],     # C minor
    'Im':    [0, 3, 7, 12],     # C minor (alt spelling)
})


STRESS_SONGS = {
    # ── Jazz: altered harmony ──
    'Tritone Sub (ii-bII-I)': {
        'chords': ['ii', 'bII', 'I'],
        'context': 'Jazz tritone substitution. bII resolves to I by half-step bass motion.',
        'expected_feel': 'resolving',
        'why': 'bII→I is one of the strongest resolutions in jazz (bass: Db→C)',
    },
    'Backdoor ii-V (iv-bVII-I)': {
        'chords': ['iv', 'bVII', 'I'],
        'context': 'Jazz backdoor resolution. bVII→I feels like a plagal cousin.',
        'expected_feel': 'resolving',
        'why': 'bVII→I resolves by whole step, feels like plagal but from mixolydian',
    },
    
    # ── Film score: chromatic mediants ──
    'Chromatic Mediant Up (I-III)': {
        'chords': ['I', 'III'],
        'context': 'John Williams / Hans Zimmer. C major → E major. Magical, expansive.',
        'expected_feel': 'tension_building',
        'why': 'Chromatic mediant is surprising, opens up harmonic space',
    },
    'Chromatic Mediant Chain (I-bVI-bIII-bVII-I)': {
        'chords': ['I', 'bVI', 'bIII', 'bVII', 'I'],
        'context': 'Film score descending mediants. Each step is a third down.',
        'expected_feel': 'resolving',
        'why': 'Returns to I, the journey resolves',
    },
    
    # ── Deceptive that feels satisfying ──
    'Deceptive to bVI (V-bVI)': {
        'chords': ['V', 'bVI'],
        'context': 'Classical deceptive cadence to flat-six. Picardy-adjacent surprise.',
        'expected_feel': 'deceptive',
        'why': 'V demands I but gets bVI — surprising but not unresolved',
    },
    
    # ── Modal / non-functional ──
    'Mixolydian Vamp (I-bVII-I)': {
        'chords': ['I', 'bVII', 'I'],
        'context': 'Classic rock mixolydian. Sweet Child O Mine, etc.',
        'expected_feel': 'resolving',
        'why': 'Returns to tonic, the bVII is color not function',
    },
    'Dorian Shuttle (i-IV)': {
        'chords': ['i', 'IV'],
        'context': 'Dorian mode. Daft Punk "Get Lucky", Santana "Oye Como Va".',
        'expected_feel': 'static',
        'why': 'Modal vamp, neither chord implies the other strongly',
    },
    'Phrygian Half Cadence (iv-bII-I)': {
        'chords': ['iv', 'bII', 'I'],
        'context': 'Phrygian cadence used in flamenco and metal.',
        'expected_feel': 'resolving',
        'why': 'bII→I is a half-step bass resolution, very final in flamenco',
    },
    
    # ── Really long progressions ──
    'Giant Steps Cycle (I-III-VI-II-bV-bVII-I)': {
        'chords': ['I', 'III', 'VI', 'ii', 'bV', 'bVII', 'I'],
        'context': 'Coltrane changes. Moving through three key centers by major thirds.',
        'expected_feel': 'resolving',
        'why': 'Returns to I after wild chromatic journey',
    },
    
    # ── Tension that resolves at the LAST second ──
    'Last Second Resolution (vi-IV-ii-V-I)': {
        'chords': ['vi', 'IV', 'ii', 'V', 'I'],
        'context': 'Builds tension through pre-dominants then resolves on last chord.',
        'expected_feel': 'resolving',
        'why': 'V-I at the end should override all the tension-building',
    },
    
    # ── The "unresolved" ending ──
    'Suspended End (I-IV-I-ii)': {
        'chords': ['I', 'IV', 'I', 'ii'],
        'context': 'Ends on ii — a pre-dominant. Like a sentence trailing off...',
        'expected_feel': 'tension_building',
        'why': 'ii implies V which implies I — double debt',
    },
    
    # ── Minor key progressions ──
    'Minor Plagal (iv-I)': {
        'chords': ['iv', 'I'],
        'context': 'Minor plagal cadence. The "amen" in minor. Radiohead loves this.',
        'expected_feel': 'resolving',
        'why': 'iv→I is one of the most evocative resolutions',
    },
    'Picardy Third (iv-V-I)': {
        'chords': ['iv', 'V', 'I'],
        'context': 'Minor context resolving to major tonic (Picardy third).',
        'expected_feel': 'resolving',
        'why': 'V→I is strong regardless of preceding context',
    },
}


def main():
    print("=" * 78)
    print("  🔨 STRESS TEST — Expectation layer vs hard cases")
    print("=" * 78)
    
    correct = 0
    total = 0
    
    print(f"\n  {'Song':<42s}  {'Expected':<16s}  {'Predicted':<16s}  {'Match'}")
    print(f"  {'─' * 90}")
    
    for name, info in STRESS_SONGS.items():
        chord_names = info['chords']
        expected = info['expected_feel']
        
        try:
            analysis = analyze_with_expectation(chord_names, V)
            predicted = classify_with_expectation(analysis)
        except KeyError as e:
            print(f"  {name:<42s}  {expected:<16s}  {'ERROR':<16s}  ⚠️  Missing voicing: {e}")
            total += 1
            continue
        
        match = feel_match(predicted, expected)
        if match:
            correct += 1
        total += 1
        
        icon = "✅" if match else "❌"
        print(f"  {name:<42s}  {expected:<16s}  {predicted:<16s}  {icon}")
        
        if not match:
            # Show why it failed
            debt_str = " → ".join(f"{d:.2f}" for d in analysis['debt_trajectory'])
            print(f"    ↳ debt=[{debt_str}]  final_impl={analysis['final_implication']:.2f}")
            print(f"    ↳ total_res={analysis['total_resolution']:+.3f}  final_res={analysis['final_resolution']:+.3f}")
            print(f"    ↳ reason: {info['why']}")
    
    acc = correct / total if total > 0 else 0
    print(f"\n  {'─' * 78}")
    print(f"\n  Stress test accuracy: {correct}/{total} = {acc:.0%}")
    
    if acc >= 0.85:
        print(f"  🎯 Model holds up under stress!")
    elif acc >= 0.7:
        print(f"  🔶 Decent but has blind spots")
    else:
        print(f"  ⚠️  Model breaks under harder cases")
    
    return correct, total


if __name__ == '__main__':
    main()
