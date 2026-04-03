#!/usr/bin/env python3
"""
🎹 MIDI INTEGRATION TEST — End-to-end: generate MIDI → parse → analyze
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Creates MIDI files from known progressions, then runs the full pipeline:
  MIDI → midi_input.parse_midi() → analyze_midi() → harmonic_pipeline.analyze()

This validates the entire chain on real MIDI data.

Striker, April 2026
"""

import mido
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from midi_input import parse_midi, analyze_midi
from harmonic_pipeline import analyze, compare

# ═══════════════════════════════════════════════════════════════════════
# MIDI GENERATION — create .mid files from chord specs
# ═══════════════════════════════════════════════════════════════════════

NOTE_MAP = {
    'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68,
    'Ab': 68, 'A': 69, 'A#': 70, 'Bb': 70, 'B': 71
}

# Chord voicings as MIDI note numbers (root position, middle register)
VOICINGS = {
    # Key of C major
    'C':    [48, 52, 55, 60],       # C3, E3, G3, C4
    'Dm':   [50, 53, 57, 62],       # D3, F3, A3, D4
    'Em':   [52, 55, 59, 64],       # E3, G3, B3, E4
    'F':    [53, 57, 60, 65],       # F3, A3, C4, F4
    'G':    [55, 59, 62, 67],       # G3, B3, D4, G4
    'Am':   [57, 60, 64, 69],       # A3, C4, E4, A4
    'Bdim': [59, 62, 65, 71],       # B3, D4, F4, B4
    'G7':   [55, 59, 62, 65],       # G3, B3, D4, F4
    'C7':   [48, 52, 55, 58],       # C3, E3, G3, Bb3
    
    # Key of G major
    'D':    [50, 54, 57, 62],       # D3, F#3, A3, D4
    'D7':   [50, 54, 57, 60],       # D3, F#3, A3, C4
    'Bm':   [59, 62, 66, 71],       # B3, D4, F#4, B4
    
    # Key of F major  
    'Bb':   [58, 62, 65, 70],       # Bb3, D4, F4, Bb4
    'Gm':   [55, 58, 62, 67],       # G3, Bb3, D4, G4
    
    # Jazz voicings
    'Cmaj7': [48, 52, 55, 59],      # C3, E3, G3, B3
    'Dm7':   [50, 53, 57, 60],      # D3, F3, A3, C4
    'Fmaj7': [53, 57, 60, 64],      # F3, A3, C4, E4
    'Em7':   [52, 55, 59, 62],      # E3, G3, B3, D4
    'Am7':   [57, 60, 64, 67],      # A3, C4, E4, G4
    
    # Giant Steps voicings (Bb major / modulating)
    'Bmaj7':  [59, 63, 66, 70],
    'D7_gs':  [50, 54, 57, 60],
    'Gmaj7':  [55, 59, 62, 66],
    'Bb7':    [58, 62, 65, 68],
    'Ebmaj7': [51, 55, 58, 62],
    'F#7':    [54, 58, 61, 64],
}

def create_midi(name: str, chords: list, ticks_per_beat=480, beats_per_chord=2) -> str:
    """Create a MIDI file from a list of chord names."""
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Set tempo (120 BPM)
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    
    duration = ticks_per_beat * beats_per_chord
    
    for chord_name in chords:
        if chord_name not in VOICINGS:
            print(f"  ⚠ No voicing for {chord_name}, skipping")
            continue
        
        notes = VOICINGS[chord_name]
        
        # Note on (all simultaneous)
        for i, note in enumerate(notes):
            track.append(mido.Message('note_on', note=note, velocity=80, time=0))
        
        # Note off after duration
        for i, note in enumerate(notes):
            track.append(mido.Message('note_off', note=note, velocity=0, 
                                       time=duration if i == 0 else 0))
    
    outdir = Path(__file__).parent / 'test_midi'
    outdir.mkdir(exist_ok=True)
    filepath = outdir / f'{name}.mid'
    mid.save(str(filepath))
    return str(filepath)


# ═══════════════════════════════════════════════════════════════════════
# TEST PROGRESSIONS
# ═══════════════════════════════════════════════════════════════════════

TEST_CASES = {
    'pachelbel_canon': {
        'chords': ['C', 'G', 'Am', 'Em', 'F', 'C', 'F', 'G'],
        'key': 'C',
        'description': "Pachelbel's Canon (I-V-vi-iii-IV-I-IV-V)",
        'expect_class': 'MUSIC',  # Should be rich, structured
    },
    'autumn_leaves': {
        'chords': ['Am7', 'D7', 'Gmaj7', 'Cmaj7', 'Fmaj7', 'Dm7', 'Em7', 'Am7'],
        'key': None,  # Let it detect
        'description': 'Autumn Leaves (vi-ii-V-I-IV-vii-iii-vi in G)',
        'expect_class': 'MUSIC',
    },
    'ii_V_I': {
        'chords': ['Dm7', 'G7', 'Cmaj7', 'Cmaj7'],
        'key': 'C',
        'description': 'Jazz ii-V-I (the canonical resolution)',
        'expect_class': 'RESOLVING',
    },
    'four_chord_pop': {
        'chords': ['C', 'G', 'Am', 'F'] * 2,
        'key': 'C',
        'description': 'Pop four-chord (I-V-vi-IV) x2',
        'expect_class': 'CYCLING',
    },
    'drone': {
        'chords': ['C'] * 8,
        'key': 'C',
        'description': 'Drone (just C major repeated)',
        'expect_class': 'STATIC',
    },
    'blues_12bar': {
        'chords': ['C7', 'C7', 'C7', 'C7', 'F', 'F', 'C7', 'C7', 'G7', 'F', 'C7', 'G7'],
        'key': 'C',
        'description': '12-bar blues in C',
        'expect_class': 'DEVELOPING',
    },
}


# ═══════════════════════════════════════════════════════════════════════
# RUN THE FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def run_tests():
    print("=" * 72)
    print("🎹 MIDI INTEGRATION TEST — Full Pipeline")
    print("=" * 72)
    
    results = {}
    
    for name, spec in TEST_CASES.items():
        print(f"\n{'─' * 60}")
        print(f"📄 {name}: {spec['description']}")
        print(f"{'─' * 60}")
        
        # Step 1: Generate MIDI
        filepath = create_midi(name, spec['chords'])
        print(f"  ✅ Generated: {filepath}")
        
        # Step 2: Parse MIDI
        try:
            parsed = parse_midi(filepath, key=spec.get('key'))
            print(f"  ✅ Parsed: key={parsed.get('key', '?')}, "
                  f"chords={len(parsed.get('chords', []))}")
            
            chord_names = parsed.get('chord_names', [])
            roman = parsed.get('roman_numerals', [])
            print(f"  📊 Chords: {' → '.join(chord_names[:8])}")
            print(f"  📊 Roman:  {' → '.join(roman[:8])}")
        except Exception as e:
            print(f"  ❌ Parse failed: {e}")
            import traceback; traceback.print_exc()
            results[name] = {'status': 'PARSE_FAIL', 'error': str(e)}
            continue
        
        # Step 3: Full analysis via analyze_midi
        try:
            analysis = analyze_midi(filepath, key=spec.get('key'))
            print(f"  ✅ Analyzed!")
            
            classification = analysis.get('classification', '?')
            narrative = analysis.get('narrative', '')
            total_res = analysis.get('total_resolution', 0)
            final_res = analysis.get('final_resolution', 0)
            exp_debt = analysis.get('trajectory', {}).get('expectation_debt', [0])[-1] if 'trajectory' in analysis else 0
            
            # Get trajectory/triple-point if available
            traj = analysis.get('trajectory', {})
            tp_score = traj.get('triple_point', 0)
            
            print(f"  🏷️  Classification: {classification}")
            print(f"  📊 Total resolution: {total_res:.3f}")
            print(f"  📊 Final resolution: {final_res:.3f}")
            print(f"  📊 Expectation debt: {exp_debt:.3f}")
            if tp_score:
                print(f"  📈 Triple-point:    {tp_score:.3f}")
            print(f"  📖 {narrative[:120]}")
            
            results[name] = {
                'status': 'OK',
                'classification': classification,
                'total_resolution': total_res,
                'triple_point': tp_score,
                'expected': spec['expect_class'],
                'match': classification.upper() == spec['expect_class'].upper()
            }
                
        except Exception as e:
            print(f"  ❌ Analysis failed: {e}")
            import traceback; traceback.print_exc()
            results[name] = {'status': 'ANALYSIS_FAIL', 'error': str(e)}
    
    # ═══════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'=' * 72}")
    print("📊 SUMMARY")
    print(f"{'=' * 72}")
    
    for name, r in results.items():
        status = r.get('status', '?')
        if status == 'OK':
            match = '✅' if r.get('match') else '⚠'
            tp = r.get('triple_point', 0)
            print(f"  {match} {name:20s} → {r['classification']:12s} "
                  f"(expected: {r['expected']:12s}) TP={tp:.3f}")
        else:
            print(f"  ❌ {name:20s} → {status}: {r.get('error', 'unknown')[:60]}")
    
    ok = sum(1 for r in results.values() if r.get('status') == 'OK')
    total = len(results)
    matched = sum(1 for r in results.values() if r.get('match'))
    print(f"\n  Pipeline success: {ok}/{total}")
    print(f"  Classification match: {matched}/{total}")
    
    # Compare the best and worst
    if ok >= 2:
        print(f"\n{'─' * 60}")
        print("🔬 COMPARISON: Autumn Leaves vs Drone")
        print(f"{'─' * 60}")
        try:
            comp = compare(
                ['Am7', 'D7', 'Gmaj7', 'Cmaj7', 'Fmaj7', 'Dm7', 'Em7', 'Am7'],
                ['C', 'C', 'C', 'C', 'C', 'C', 'C', 'C']
            )
            if 'comparison' in comp:
                c = comp['comparison']
                for key in ['entropy_ratio', 'gravity_ratio', 'classification_a', 'classification_b']:
                    if key in c:
                        print(f"  {key}: {c[key]}")
        except Exception as e:
            print(f"  Compare failed: {e}")
    
    return results


if __name__ == '__main__':
    results = run_tests()
