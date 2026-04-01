"""
Poem analyzer — extracts mathematical structure from existing poems:
meter, rhyme scheme, stanza structure, syllable patterns, tonal arc.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from engines.phonetics import (
    syllable_count, stress_pattern, line_stress_pattern,
    line_syllable_count, rhyme_strength, emotional_color
)
from engines.lexicon import get_valence


@dataclass
class LineAnalysis:
    text: str
    words: List[str]
    syllables: int
    stress: str
    last_word: str
    valence: float  # Average emotional valence
    color: float    # Average phonetic brightness


@dataclass
class PoemStructure:
    """Complete mathematical blueprint of a poem."""
    # Stanza structure
    stanza_lengths: List[int]           # Lines per stanza
    syllable_pattern: List[int]         # Syllables per line
    stress_patterns: List[str]          # Stress per line
    
    # Rhyme
    rhyme_scheme: List[str]             # e.g., ['A', 'B', 'A', 'B']
    
    # Emotional arc
    valence_arc: List[float]            # Emotional trajectory per line
    color_arc: List[float]              # Phonetic brightness trajectory
    
    # Meter
    dominant_meter: Optional[str]       # 'iambic', 'trochaic', etc.
    foot_count: Optional[int]           # Feet per line (e.g., 5 for pentameter)
    
    # Meta
    total_lines: int
    line_analyses: List[LineAnalysis] = field(default_factory=list)


def tokenize_line(line: str) -> List[str]:
    """Extract words from a line."""
    return [w for w in re.findall(r"[a-zA-Z']+", line) if w]


def detect_meter(stress: str) -> Tuple[Optional[str], Optional[int]]:
    """Detect meter type and foot count from stress pattern."""
    if len(stress) < 2:
        return None, None
    
    # Check for common patterns
    meters = {
        'iambic': '01',
        'trochaic': '10',
        'anapestic': '001',
        'dactylic': '100',
        'spondaic': '11',
        'pyrrhic': '00',
    }
    
    best_meter = None
    best_score = 0
    best_feet = 0
    
    for name, foot in meters.items():
        foot_len = len(foot)
        feet = len(stress) // foot_len
        if feet == 0:
            continue
        
        matches = 0
        total = 0
        for i in range(feet):
            for j in range(foot_len):
                idx = i * foot_len + j
                if idx < len(stress):
                    total += 1
                    # Treat '2' (secondary stress) as '1' for meter
                    s = '1' if stress[idx] in ('1', '2') else '0'
                    if s == foot[j]:
                        matches += 1
        
        score = matches / total if total > 0 else 0
        if score > best_score and score > 0.6:
            best_score = score
            best_meter = name
            best_feet = feet
    
    return best_meter, best_feet


def detect_rhyme_scheme(lines: List[LineAnalysis], threshold: float = 0.5) -> List[str]:
    """Detect rhyme scheme from analyzed lines."""
    scheme = []
    label_map = {}
    next_label = 'A'
    
    for i, line in enumerate(lines):
        if not line.last_word:
            scheme.append('X')
            continue
        
        found = False
        for j in range(i):
            if j < len(lines) and lines[j].last_word:
                strength = rhyme_strength(line.last_word, lines[j].last_word)
                if strength >= threshold:
                    scheme.append(scheme[j])
                    found = True
                    break
        
        if not found:
            scheme.append(next_label)
            next_label = chr(ord(next_label) + 1)
            if next_label > 'Z':
                next_label = 'A'
    
    return scheme


def analyze_poem(text: str) -> PoemStructure:
    """Fully analyze a poem's mathematical structure."""
    # Split into stanzas and lines
    stanzas = [s.strip() for s in text.strip().split('\n\n') if s.strip()]
    
    all_lines = []
    stanza_lengths = []
    
    for stanza in stanzas:
        lines = [l.strip() for l in stanza.split('\n') if l.strip()]
        stanza_lengths.append(len(lines))
        
        for line_text in lines:
            words = tokenize_line(line_text)
            if not words:
                continue
            
            syls = line_syllable_count(words)
            stress = line_stress_pattern(words)
            last_word = words[-1] if words else ''
            
            # Calculate emotional valence
            valences = [get_valence(w) for w in words]
            avg_valence = sum(valences) / len(valences) if valences else 0.0
            
            # Calculate phonetic color
            colors = [emotional_color(w) for w in words]
            avg_color = sum(colors) / len(colors) if colors else 0.0
            
            all_lines.append(LineAnalysis(
                text=line_text,
                words=words,
                syllables=syls,
                stress=stress,
                last_word=last_word,
                valence=avg_valence,
                color=avg_color,
            ))
    
    # Detect rhyme scheme
    rhyme_scheme = detect_rhyme_scheme(all_lines)
    
    # Detect dominant meter
    all_stress = ''.join(la.stress for la in all_lines)
    dominant_meter, foot_count = detect_meter(all_stress)
    
    return PoemStructure(
        stanza_lengths=stanza_lengths,
        syllable_pattern=[la.syllables for la in all_lines],
        stress_patterns=[la.stress for la in all_lines],
        rhyme_scheme=rhyme_scheme,
        valence_arc=[la.valence for la in all_lines],
        color_arc=[la.color for la in all_lines],
        dominant_meter=dominant_meter,
        foot_count=foot_count,
        total_lines=len(all_lines),
        line_analyses=all_lines,
    )


def structure_summary(structure: PoemStructure) -> str:
    """Human-readable summary of poem structure."""
    lines = []
    lines.append(f"Lines: {structure.total_lines}")
    lines.append(f"Stanzas: {len(structure.stanza_lengths)} ({structure.stanza_lengths})")
    lines.append(f"Syllables/line: {structure.syllable_pattern}")
    lines.append(f"Rhyme scheme: {''.join(structure.rhyme_scheme)}")
    if structure.dominant_meter:
        lines.append(f"Meter: {structure.dominant_meter} ({structure.foot_count} feet)")
    
    avg_valence = sum(structure.valence_arc) / len(structure.valence_arc) if structure.valence_arc else 0
    lines.append(f"Avg valence: {avg_valence:.2f} ({'positive' if avg_valence > 0.1 else 'negative' if avg_valence < -0.1 else 'neutral'})")
    
    return '\n'.join(lines)
