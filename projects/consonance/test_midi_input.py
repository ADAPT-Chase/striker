#!/usr/bin/env python3
"""Test MIDI input module with generated MIDI files."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import mido
from midi_input import (
    extract_notes, segment_chords, identify_chord, 
    pitches_to_pitch_classes, detect_key, chord_to_roman,
    parse_midi, analyze_midi
)

TPB = 480  # ticks per beat

def make_test_midi(filename: str, chords: list, tpb=TPB):
    """
    Create a test MIDI file from chord definitions.
    Each chord is (pitches_list, duration_in_beats).
    """
    mid = mido.MidiFile(ticks_per_beat=tpb)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    for pitches, dur_beats in chords:
        dur_ticks = int(dur_beats * tpb)
        # Note on (all at once)
        for i, p in enumerate(pitches):
            track.append(mido.Message('note_on', note=p, velocity=80, time=0))
        # Note off (all at once, after duration)
        for i, p in enumerate(pitches):
            track.append(mido.Message('note_off', note=p, velocity=0, 
                                       time=dur_ticks if i == 0 else 0))
    
    mid.save(filename)
    return filename


def test_chord_identification():
    """Test that we correctly identify common chords."""
    print("═══ Chord Identification ═══")
    
    tests = [
        ({0, 4, 7}, '', 0, 'C major'),
        ({0, 3, 7}, 'm', 0, 'C minor'),
        ({2, 5, 9}, 'm', 2, 'D minor'),
        ({7, 11, 2}, '', 7, 'G major'),  # G B D
        ({5, 9, 0}, '', 5, 'F major'),   # F A C
        ({0, 4, 7, 10}, '7', 0, 'C7'),
        ({0, 4, 7, 11}, 'maj7', 0, 'Cmaj7'),
    ]
    
    passed = 0
    for pcs, exp_quality, exp_root, desc in tests:
        result = identify_chord(pcs)
        if result:
            quality, root = result
            ok = quality == exp_quality and root == exp_root
            status = '✅' if ok else '❌'
            if ok:
                passed += 1
            print(f"  {status} {desc}: got ({quality!r}, {root}) expected ({exp_quality!r}, {exp_root})")
        else:
            print(f"  ❌ {desc}: not identified")
    
    print(f"  {passed}/{len(tests)} passed\n")
    return passed == len(tests)


def test_key_detection():
    """Test key detection on simple progressions."""
    print("═══ Key Detection ═══")
    
    # C major: I-IV-V-I with lots of C
    # Create notes weighted toward C major scale
    c_major_notes = []
    t = 0
    for pitch in [60, 64, 67, 65, 69, 72, 67, 71, 74, 60, 64, 67]:
        c_major_notes.append({'pitch': pitch, 'start': t, 'end': t + 480, 
                              'velocity': 80, 'channel': 0})
        t += 480
    
    tonic, mode = detect_key(c_major_notes)
    ok = tonic == 0  # C
    print(f"  {'✅' if ok else '❌'} C major notes → {['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'][tonic]} {mode} (expected C)")
    
    # A minor: weight toward A minor
    a_minor_notes = []
    t = 0
    for pitch in [57, 60, 64, 57, 62, 65, 57, 59, 62, 57, 60, 64]:
        a_minor_notes.append({'pitch': pitch, 'start': t, 'end': t + 480,
                              'velocity': 80, 'channel': 0})
        t += 480
    
    tonic2, mode2 = detect_key(a_minor_notes)
    ok2 = tonic2 == 9  # A
    print(f"  {'✅' if ok2 else '❌'} A minor notes → {['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'][tonic2]} {mode2} (expected A minor)")
    print()
    return ok and ok2


def test_roman_numeral_mapping():
    """Test chord → Roman numeral conversion."""
    print("═══ Roman Numeral Mapping ═══")
    
    tests = [
        (0, '', 0, 'major', 'I'),       # C in C major
        (7, '', 0, 'major', 'V'),        # G in C major
        (9, 'm', 0, 'major', 'vi'),      # Am in C major
        (5, '', 0, 'major', 'IV'),       # F in C major
        (2, 'm', 0, 'major', 'ii'),      # Dm in C major
        (7, '7', 0, 'major', 'V7'),      # G7 in C major
        (10, '', 0, 'major', 'bVII'),    # Bb in C major
    ]
    
    passed = 0
    for root, qual, tonic, mode, expected in tests:
        result = chord_to_roman(root, qual, tonic, mode)
        ok = result == expected
        if ok:
            passed += 1
        status = '✅' if ok else '❌'
        print(f"  {status} root={root} qual={qual!r} in {mode} → {result!r} (expected {expected!r})")
    
    print(f"  {passed}/{len(tests)} passed\n")
    return passed == len(tests)


def test_full_midi_parse():
    """Test full MIDI → chord progression pipeline."""
    print("═══ Full MIDI Parse ═══")
    
    # I-V-vi-IV in C major (the "Axis of Awesome" progression)
    midi_file = '/tmp/test_axis.mid'
    make_test_midi(midi_file, [
        ([60, 64, 67], 4),    # C major
        ([55, 59, 62], 4),    # G major  (G3, B3, D4)
        ([57, 60, 64], 4),    # A minor
        ([53, 57, 60], 4),    # F major  (F3, A3, C4)
    ])
    
    result = parse_midi(midi_file, key='C major')
    print(f"  Key: {result['key']}")
    print(f"  Chords found: {result['total_chords']}")
    print(f"  Progression: {' → '.join(result['chord_names'])}")
    
    # Check we got the right chords
    expected = ['I', 'V', 'vi', 'IV']
    ok = result['chord_names'] == expected
    print(f"  {'✅' if ok else '❌'} Expected {expected}, got {result['chord_names']}")
    print()
    return ok


def test_full_analysis():
    """Test full MIDI → harmonic analysis."""
    print("═══ Full MIDI → Analysis ═══")
    
    # ii-V-I in C (jazz cadence)
    midi_file = '/tmp/test_251.mid'
    make_test_midi(midi_file, [
        ([62, 65, 69, 72], 4),  # Dm7: D F A C
        ([55, 59, 62, 65], 4),  # G7: G B D F
        ([60, 64, 67, 72], 4),  # Cmaj7: C E G C
    ])
    
    result = analyze_midi(midi_file, key='C major', verbose=True)
    
    ok = 'classification' in result and 'narrative' in result
    print(f"  {'✅' if ok else '❌'} Analysis complete: classification={result.get('classification')}")
    if 'narrative' in result:
        print(f"  📖 {result['narrative']}")
    
    return ok


if __name__ == '__main__':
    print("🎹 MIDI Input Test Suite\n")
    
    results = []
    results.append(('Chord ID', test_chord_identification()))
    results.append(('Key Detection', test_key_detection()))
    results.append(('Roman Numerals', test_roman_numeral_mapping()))
    results.append(('Full Parse', test_full_midi_parse()))
    results.append(('Full Analysis', test_full_analysis()))
    
    print("\n═══ SUMMARY ═══")
    all_pass = True
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
        if not ok:
            all_pass = False
    
    print(f"\n{'🎉 ALL TESTS PASSED' if all_pass else '⚠️  SOME TESTS FAILED'}")
    sys.exit(0 if all_pass else 1)
