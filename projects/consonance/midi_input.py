#!/usr/bin/env python3
"""
🎹 MIDI INPUT — Parse MIDI files into the harmonic analysis pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Takes a .mid file, extracts chord progressions, identifies chord names
relative to a detected (or specified) key, and feeds them into
harmonic_pipeline.analyze().

This is the bridge between real music and the analysis engine.

The hard problem: MIDI is polyphonic time-series data. We need to:
1. Segment into chords (notes sounding simultaneously)
2. Reduce to pitch classes (octave-invariant)
3. Identify chord quality (major, minor, dim, aug, 7th, etc.)
4. Detect key center (or accept user override)
5. Map absolute chords to Roman numeral names

Striker, April 2026
"""

import math
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from collections import Counter, defaultdict

try:
    import mido
except ImportError:
    print("Install mido: pip3 install mido")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))

# ═══════════════════════════════════════════════════════════════════════
# CHORD TEMPLATES — pitch class sets for chord identification
# ═══════════════════════════════════════════════════════════════════════

NOTE_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

# Intervals from root for each chord type
CHORD_TEMPLATES = {
    '':     frozenset([0, 4, 7]),         # major
    'm':    frozenset([0, 3, 7]),         # minor
    'dim':  frozenset([0, 3, 6]),         # diminished
    'aug':  frozenset([0, 4, 8]),         # augmented
    '7':    frozenset([0, 4, 7, 10]),     # dominant 7
    'maj7': frozenset([0, 4, 7, 11]),     # major 7
    'm7':   frozenset([0, 3, 7, 10]),     # minor 7
    'dim7': frozenset([0, 3, 6, 9]),      # diminished 7
    'm7b5': frozenset([0, 3, 6, 10]),     # half-diminished
    'sus4': frozenset([0, 5, 7]),         # sus4
    'sus2': frozenset([0, 2, 7]),         # sus2
    'add9': frozenset([0, 2, 4, 7]),      # add9
}

# Scale degrees for major key (in semitones from tonic)
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]

# Roman numeral mapping: (scale_degree_semitones, quality) → name
# Built dynamically based on key


# ═══════════════════════════════════════════════════════════════════════
# MIDI PARSING
# ═══════════════════════════════════════════════════════════════════════

def extract_notes(midi_path: str, track: Optional[int] = None) -> List[Dict]:
    """
    Extract all note events from a MIDI file with absolute timing.
    Returns list of {pitch, start, end, velocity, channel}.
    """
    mid = mido.MidiFile(midi_path)
    ticks_per_beat = mid.ticks_per_beat
    
    notes = []
    
    tracks = [mid.tracks[track]] if track is not None else mid.tracks
    
    for tr in tracks:
        time = 0  # absolute ticks
        active = {}  # pitch -> {start, velocity, channel}
        
        for msg in tr:
            time += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                active[msg.note] = {
                    'start': time,
                    'velocity': msg.velocity,
                    'channel': msg.channel
                }
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active:
                    info = active.pop(msg.note)
                    notes.append({
                        'pitch': msg.note,
                        'start': info['start'],
                        'end': time,
                        'velocity': info['velocity'],
                        'channel': info['channel'],
                    })
    
    notes.sort(key=lambda n: (n['start'], n['pitch']))
    return notes


def segment_chords(notes: List[Dict], resolution_ticks: int = 480,
                   min_notes: int = 2) -> List[Dict]:
    """
    Segment notes into chord windows. Groups simultaneous notes.
    
    resolution_ticks: quantization grid (480 = quarter note at standard TPB)
    min_notes: minimum notes to count as a chord
    
    Returns list of {start_tick, pitches: [int], velocities: [int]}
    """
    if not notes:
        return []
    
    # Quantize start times to grid
    windows = defaultdict(list)
    for n in notes:
        quantized = round(n['start'] / resolution_ticks) * resolution_ticks
        windows[quantized].append(n)
    
    chords = []
    for tick in sorted(windows.keys()):
        group = windows[tick]
        if len(group) >= min_notes:
            pitches = sorted(set(n['pitch'] for n in group))
            velocities = [n['velocity'] for n in group]
            chords.append({
                'start_tick': tick,
                'pitches': pitches,
                'velocities': velocities,
            })
    
    return chords


def pitches_to_pitch_classes(pitches: List[int]) -> Set[int]:
    """Convert MIDI pitches to pitch classes (0-11)."""
    return set(p % 12 for p in pitches)


# ═══════════════════════════════════════════════════════════════════════
# CHORD IDENTIFICATION
# ═══════════════════════════════════════════════════════════════════════

def identify_chord(pitch_classes: Set[int]) -> Optional[Tuple[str, int]]:
    """
    Identify a chord from its pitch classes.
    Returns (quality_suffix, root_pc) or None.
    
    Tries every possible root and finds best template match.
    """
    if len(pitch_classes) < 2:
        return None
    
    pcs = frozenset(pitch_classes)
    best = None
    best_score = -1
    
    for root in range(12):
        intervals = frozenset((pc - root) % 12 for pc in pcs)
        
        for quality, template in CHORD_TEMPLATES.items():
            # How many template tones are present?
            match = len(intervals & template)
            # Penalize extra notes not in template
            extra = len(intervals - template)
            score = match / len(template) - 0.1 * extra
            
            # Prefer larger templates when tied (7th chords over triads)
            if match == len(template) and len(template) > 3:
                score += 0.05
            
            if score > best_score:
                best_score = score
                best = (quality, root)
    
    if best and best_score >= 0.5:
        return best
    return None


def chord_to_name(quality: str, root_pc: int) -> str:
    """Absolute chord name: e.g., 'C', 'Dm', 'F#7'"""
    return NOTE_NAMES[root_pc] + quality


# ═══════════════════════════════════════════════════════════════════════
# KEY DETECTION
# ═══════════════════════════════════════════════════════════════════════

# Krumhansl-Kessler key profiles
KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def detect_key(notes: List[Dict], method: str = 'krumhansl') -> Tuple[int, str]:
    """
    Detect the key of a piece from its notes.
    Returns (tonic_pc, mode) where mode is 'major' or 'minor'.
    
    Uses Krumhansl-Kessler key-finding algorithm:
    correlate pitch class distribution with key profiles.
    """
    # Build pitch class histogram weighted by duration
    histogram = [0.0] * 12
    for n in notes:
        pc = n['pitch'] % 12
        duration = max(n['end'] - n['start'], 1)
        histogram[pc] += duration
    
    total = sum(histogram)
    if total == 0:
        return (0, 'major')
    histogram = [h / total for h in histogram]
    
    best_key = (0, 'major')
    best_corr = -2
    
    for tonic in range(12):
        # Rotate histogram so tonic is at index 0
        rotated = [histogram[(tonic + i) % 12] for i in range(12)]
        
        for mode, profile in [('major', KK_MAJOR), ('minor', KK_MINOR)]:
            # Pearson correlation
            mean_r = sum(rotated) / 12
            mean_p = sum(profile) / 12
            
            num = sum((r - mean_r) * (p - mean_p) for r, p in zip(rotated, profile))
            den_r = math.sqrt(sum((r - mean_r) ** 2 for r in rotated))
            den_p = math.sqrt(sum((p - mean_p) ** 2 for p in profile))
            
            if den_r * den_p > 0:
                corr = num / (den_r * den_p)
            else:
                corr = 0
            
            if corr > best_corr:
                best_corr = corr
                best_key = (tonic, mode)
    
    return best_key


# ═══════════════════════════════════════════════════════════════════════
# ROMAN NUMERAL MAPPING
# ═══════════════════════════════════════════════════════════════════════

# Diatonic chords in major key: degree → (semitones_from_tonic, roman, quality)
MAJOR_DIATONIC = {
    0:  ('I', ''),
    2:  ('ii', 'm'),
    4:  ('iii', 'm'),
    5:  ('IV', ''),
    7:  ('V', ''),
    9:  ('vi', 'm'),
    11: ('viio', 'dim'),
}

# Diatonic chords in minor key
MINOR_DIATONIC = {
    0:  ('i', 'm'),
    2:  ('iio', 'dim'),
    3:  ('III', ''),
    5:  ('iv', 'm'),
    7:  ('v', 'm'),   # natural minor; V is also common (harmonic minor)
    8:  ('VI', ''),
    10: ('VII', ''),
}

# Chromatic chords (common borrowings)
CHROMATIC_NAMES = {
    # (interval_from_tonic, quality) → roman numeral
    (1, ''):   'bII',
    (1, 'm'):  'bii',
    (3, ''):   'bIII',
    (3, 'm'):  'biii',
    (6, ''):   '#IV',
    (6, 'dim'): '#IVo',
    (8, ''):   'bVI',
    (8, 'm'):  'bvi',
    (10, ''):  'bVII',
    (10, 'm'): 'bvii',
}


def chord_to_roman(root_pc: int, quality: str, tonic_pc: int, mode: str = 'major') -> str:
    """
    Convert an absolute chord (root + quality) to a Roman numeral
    relative to the given key.
    """
    interval = (root_pc - tonic_pc) % 12
    
    diatonic = MAJOR_DIATONIC if mode == 'major' else MINOR_DIATONIC
    
    # Check diatonic first
    if interval in diatonic:
        roman, expected_quality = diatonic[interval]
        # If quality matches, use the standard name
        if quality == expected_quality:
            return roman
        # Quality mismatch — common alterations
        if quality == '' and expected_quality == 'm':
            return roman.upper()  # e.g., III instead of iii
        if quality == 'm' and expected_quality == '':
            return roman.lower()  # e.g., iv instead of IV
        # 7th chords: append to the base roman
        if quality in ('7', 'maj7', 'm7', 'dim7', 'm7b5'):
            base = roman
            if quality == '7':
                return base + '7' if base[0].isupper() else base.upper() + '7'
            return base + quality
    
    # Chromatic chord
    key = (interval, quality.replace('7', '').replace('maj', '').replace('m7b5', 'dim'))
    if key in CHROMATIC_NAMES:
        name = CHROMATIC_NAMES[key]
        if '7' in quality:
            name += '7'
        return name
    
    # Fallback: absolute name with slash notation
    return f"{NOTE_NAMES[root_pc]}{quality}/{NOTE_NAMES[tonic_pc]}"


# ═══════════════════════════════════════════════════════════════════════
# VOICING EXTRACTION (for pipeline compatibility)
# ═══════════════════════════════════════════════════════════════════════

def midi_voicing_from_pitches(pitches: List[int], tonic_pc: int) -> List[int]:
    """
    Convert absolute MIDI pitches to tonic-relative semitones
    (matching the pipeline's voicing format).
    
    Pipeline voicings are semitones above the tonic (C=0 in key of C).
    """
    # Normalize: lowest note relative to nearest tonic below it
    base = min(pitches)
    base_octave_tonic = (base // 12) * 12 + tonic_pc
    if base_octave_tonic > base:
        base_octave_tonic -= 12
    
    return [p - base_octave_tonic for p in sorted(pitches)]


# ═══════════════════════════════════════════════════════════════════════
# MAIN INTERFACE
# ═══════════════════════════════════════════════════════════════════════

def parse_midi(midi_path: str,
               key: Optional[str] = None,
               resolution_ticks: Optional[int] = None,
               min_notes: int = 3,
               track: Optional[int] = None,
               deduplicate: bool = True) -> Dict:
    """
    Parse a MIDI file into chord progression data for the pipeline.
    
    Args:
        midi_path: path to .mid file
        key: override key detection, e.g. 'C major', 'A minor'
        resolution_ticks: quantization grid (None = auto from file)
        min_notes: minimum simultaneous notes for a chord
        track: specific track index (None = all tracks)
        deduplicate: remove consecutive identical chords
    
    Returns dict with:
        - chord_names: list of Roman numeral names
        - voicings: dict of {name: [semitones]} for custom voicings
        - key: detected/specified key
        - raw_chords: list of identified chords with timing
        - ready for harmonic_pipeline.analyze(chord_names, voicings)
    """
    mid = mido.MidiFile(midi_path)
    
    # Resolution
    if resolution_ticks is None:
        resolution_ticks = mid.ticks_per_beat  # quarter note
    
    # Extract notes
    notes = extract_notes(midi_path, track=track)
    if not notes:
        return {'error': 'No notes found', 'chord_names': [], 'voicings': {}}
    
    # Detect or parse key
    if key:
        parts = key.strip().split()
        tonic_name = parts[0]
        mode = parts[1] if len(parts) > 1 else 'major'
        tonic_pc = NOTE_NAMES.index(tonic_name) if tonic_name in NOTE_NAMES else 0
    else:
        tonic_pc, mode = detect_key(notes)
    
    key_name = f"{NOTE_NAMES[tonic_pc]} {mode}"
    
    # Segment into chords
    chords = segment_chords(notes, resolution_ticks=resolution_ticks, min_notes=min_notes)
    if not chords:
        return {'error': 'No chords found', 'chord_names': [], 'voicings': {},
                'key': key_name, 'notes_found': len(notes)}
    
    # Identify each chord
    raw_chords = []
    for ch in chords:
        pcs = pitches_to_pitch_classes(ch['pitches'])
        ident = identify_chord(pcs)
        if ident:
            quality, root = ident
            roman = chord_to_roman(root, quality, tonic_pc, mode)
            abs_name = chord_to_name(quality, root)
            voicing = midi_voicing_from_pitches(ch['pitches'], tonic_pc)
            raw_chords.append({
                'tick': ch['start_tick'],
                'pitches': ch['pitches'],
                'pitch_classes': sorted(pcs),
                'root': NOTE_NAMES[root],
                'quality': quality,
                'abs_name': abs_name,
                'roman': roman,
                'voicing': voicing,
            })
    
    if not raw_chords:
        return {'error': 'No chords identified', 'chord_names': [], 'voicings': {},
                'key': key_name, 'segments': len(chords)}
    
    # Deduplicate consecutive identical chords
    if deduplicate:
        deduped = [raw_chords[0]]
        for ch in raw_chords[1:]:
            if ch['roman'] != deduped[-1]['roman']:
                deduped.append(ch)
        raw_chords = deduped
    
    # Build chord names and custom voicings
    chord_names = []
    custom_voicings = {}
    
    for i, ch in enumerate(raw_chords):
        name = ch['roman']
        # If name already exists with different voicing, make unique
        if name in custom_voicings and custom_voicings[name] != ch['voicing']:
            name = f"{name}_{i}"
            ch['roman'] = name
        
        chord_names.append(name)
        custom_voicings[name] = ch['voicing']
    
    return {
        'chord_names': chord_names,
        'voicings': custom_voicings,
        'key': key_name,
        'key_confidence': None,  # TODO: return correlation score
        'tonic_pc': tonic_pc,
        'mode': mode,
        'raw_chords': raw_chords,
        'total_notes': len(notes),
        'total_segments': len(chords),
        'total_chords': len(raw_chords),
    }


def analyze_midi(midi_path: str, key: Optional[str] = None,
                 verbose: bool = True, **kwargs) -> Dict:
    """
    Full pipeline: MIDI file → harmonic analysis.
    
    This is the one-call interface. Give it a MIDI file, get back
    everything the pipeline knows about the harmony.
    """
    from harmonic_pipeline import analyze
    
    parsed = parse_midi(midi_path, key=key, **kwargs)
    
    if 'error' in parsed:
        if verbose:
            print(f"⚠️  {parsed['error']}")
        return parsed
    
    if verbose:
        print(f"🎹 MIDI: {Path(midi_path).name}")
        print(f"🎵 Key: {parsed['key']}")
        print(f"🎶 Chords: {len(parsed['chord_names'])} ({parsed['total_notes']} notes, {parsed['total_segments']} segments)")
        print(f"📝 Progression: {' → '.join(parsed['chord_names'])}")
        print()
    
    # Run the pipeline
    result = analyze(
        parsed['chord_names'],
        voicings_dict=parsed['voicings'],
        verbose=verbose
    )
    
    # Attach MIDI metadata
    result['midi'] = {
        'file': midi_path,
        'key': parsed['key'],
        'total_notes': parsed['total_notes'],
        'raw_chords': parsed['raw_chords'],
    }
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python midi_input.py <file.mid> [key]")
        print("  key: e.g., 'C major', 'A minor' (auto-detected if omitted)")
        print()
        print("Example: python midi_input.py twinkle.mid 'C major'")
        sys.exit(0)
    
    midi_file = sys.argv[1]
    key_override = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
    
    result = analyze_midi(midi_file, key=key_override, verbose=True)
    
    if 'classification' in result:
        print(f"\n🏷️  Classification: {result['classification']}")
    if 'narrative' in result:
        print(f"\n📖 {result['narrative']}")
