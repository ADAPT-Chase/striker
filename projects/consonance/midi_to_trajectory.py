#!/usr/bin/env python3
"""
🔗 MIDI → TRAJECTORY BRIDGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Connects the MIDI parser output to entropy trajectory analysis.

The problem: midi_input outputs chord names like 'vim7', 'II7', 'Vmaj7'
but entropy_trajectories expects Roman numerals matching its VOICINGS dict.

This module:
1. Maps extended chord names to base Roman numerals
2. Generates voicings dynamically from MIDI note data
3. Patches entropy_trajectories to work with arbitrary chords

Striker, April 2026
"""

import sys
import re
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from midi_input import parse_midi
from entropy_trajectories import (
    harmonic_memory, harmonic_transport, harmonic_transformation,
    triple_point_score, classify_trajectory, VOICINGS
)

# ═══════════════════════════════════════════════════════════════════════
# CHORD NAME NORMALIZATION — map extended names to base Roman numerals
# ═══════════════════════════════════════════════════════════════════════

# Map from extended chord names to closest VOICINGS key
NORMALIZE_MAP = {
    # Major chords
    'I': 'I', 'Imaj7': 'I', 'I7': 'I7', 'Iadd9': 'I',
    'II': 'V',  # secondary dominant approximation
    'II7': 'V7',
    'IV': 'IV', 'IVmaj7': 'IV', 'IV7': 'IV7',
    'V': 'V', 'Vmaj7': 'V', 'V7': 'V7',
    'bIII': 'bIII', 'bVI': 'bVI', 'bVII': 'bVII',
    'bII': 'bVII',  # Neapolitan → approximate
    
    # Minor chords  
    'i': 'i', 'im7': 'i',
    'ii': 'ii', 'iim7': 'ii', 'ii7': 'ii7',
    'iii': 'iii', 'iiim7': 'iii', 'iii7': 'iii7',
    'iv': 'iv', 'ivm7': 'iv',
    'v': 'v', 'vm7': 'v',
    'vi': 'vi', 'vim7': 'vi', 'vi7': 'vi7',
    'vii': 'viio', 'viio': 'viio', 'vii7': 'vii7', 'viim7': 'vii7',
    'viim7b5': 'vii7',
    
    # Diminished
    'iio': 'viio',  # approximate
    'viidim7': 'viio',
}


def normalize_chord(name: str) -> Optional[str]:
    """Map an extended chord name to nearest VOICINGS key."""
    # Strip trailing numbers (positional suffixes like '_11', '_12')
    clean = re.sub(r'_\d+$', '', name)
    
    # Direct lookup
    if clean in NORMALIZE_MAP:
        return NORMALIZE_MAP[clean]
    
    # Check VOICINGS directly
    if clean in VOICINGS:
        return clean
    
    # Try stripping extensions (7, maj7, m7, etc)
    base = re.sub(r'(maj7|m7b5|m7|dim7|dim|aug|7|sus[24]|add9)$', '', clean)
    if base in NORMALIZE_MAP:
        return NORMALIZE_MAP[base]
    if base in VOICINGS:
        return base
    
    return None


def midi_to_voicings(filepath: str, key: str = None) -> Dict:
    """
    Parse a MIDI file and return voicings suitable for entropy trajectory.
    
    Also dynamically registers any missing voicings in the VOICINGS dict
    based on actual MIDI note data.
    """
    parsed = parse_midi(filepath, key=key)
    chord_names = parsed.get('chord_names', [])
    
    # Get the actual note data for dynamic voicing registration
    segments = parsed.get('segments', [])
    
    normalized = []
    unmapped = []
    
    for i, name in enumerate(chord_names):
        mapped = normalize_chord(name)
        if mapped:
            normalized.append(mapped)
        else:
            unmapped.append(name)
            # Try to register a dynamic voicing from MIDI data
            if i < len(segments) and segments[i]:
                pitch_classes = sorted(set(n % 12 for n in segments[i]))
                # Use a synthetic voicing in middle register
                voicing = [48 + pc for pc in pitch_classes]
                VOICINGS[name] = voicing
                normalized.append(name)
            else:
                normalized.append('I')  # fallback
    
    return {
        'original': chord_names,
        'normalized': normalized,
        'unmapped': unmapped,
        'key': parsed.get('key', '?'),
        'n_chords': len(chord_names),
    }


def analyze_midi_trajectory(filepath: str, key: str = None, label: str = None) -> Dict:
    """
    Full trajectory analysis of a MIDI file.
    
    Returns triple-point metrics + classification.
    """
    result = midi_to_voicings(filepath, key=key)
    chords = result['normalized']
    
    if not label:
        label = Path(filepath).stem
    
    if len(chords) < 3:
        return {
            'label': label,
            'n_chords': len(chords),
            'memory': 0, 'transport': 0, 'transformation': 0,
            'triple_point': 0, 'classification': 'TOO_SHORT',
            'unmapped': result['unmapped'],
        }
    
    mem = harmonic_memory(chords)
    trans = harmonic_transport(chords)
    xform = harmonic_transformation(chords)
    tp = triple_point_score(mem, trans, xform)
    cls = classify_trajectory(mem, trans, xform)
    
    return {
        'label': label,
        'n_chords': len(chords),
        'key': result['key'],
        'memory': mem,
        'transport': trans,
        'transformation': xform,
        'triple_point': tp,
        'classification': cls,
        'unmapped': result['unmapped'],
        'chords_sample': chords[:12],
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN — test with generated MIDI files
# ═══════════════════════════════════════════════════════════════════════

def main():
    import os
    
    test_dir = Path(__file__).parent / 'test_midi'
    if not test_dir.exists():
        print("No test_midi directory. Run midi_integration_test.py first.")
        return
    
    midi_files = sorted(test_dir.glob('*.mid'))
    if not midi_files:
        print("No MIDI files found.")
        return
    
    print("=" * 72)
    print("🔗 MIDI → TRAJECTORY ANALYSIS")
    print("=" * 72)
    
    print(f"\n{'File':<22s} {'TP':>6s} {'Mem':>6s} {'Trans':>6s} {'Xform':>6s} {'Class':<14s} {'Chords':>6s}")
    print("─" * 75)
    
    results = []
    for f in midi_files:
        r = analyze_midi_trajectory(str(f))
        results.append(r)
        unmapped_note = f" ({len(r['unmapped'])} unmapped)" if r['unmapped'] else ""
        print(f"{r['label']:<22s} {r['triple_point']:6.3f} {r['memory']:6.3f} "
              f"{r['transport']:6.3f} {r['transformation']:6.3f} {r['classification']:<14s} "
              f"{r['n_chords']:>6d}{unmapped_note}")
    
    # Rankings
    print(f"\n{'─' * 75}")
    print("📊 RANKED BY TRIPLE-POINT:")
    ranked = sorted(results, key=lambda r: r['triple_point'], reverse=True)
    for i, r in enumerate(ranked, 1):
        print(f"  {i}. {r['label']:<22s} TP={r['triple_point']:.3f} ({r['classification']})")
    
    # Show chord mappings for debugging
    print(f"\n{'─' * 75}")
    print("🔍 CHORD MAPPING SAMPLES:")
    for r in results[:3]:
        print(f"  {r['label']}: {' → '.join(r.get('chords_sample', []))}")


if __name__ == '__main__':
    main()
