"""
Pre-defined poetic forms as mathematical blueprints.
These can be used directly or derived from analyzed poems.
"""
from engines.analyzer import PoemStructure


def sonnet_blueprint(variant='shakespearean') -> PoemStructure:
    """
    Shakespearean sonnet: 14 lines of iambic pentameter.
    Rhyme: ABAB CDCD EFEF GG
    """
    if variant == 'shakespearean':
        rhyme = list('ABABCDCDEFEFGG')
        stanzas = [4, 4, 4, 2]
    elif variant == 'petrarchan':
        rhyme = list('ABBAABBACDECDE')
        stanzas = [8, 6]
    else:
        rhyme = list('ABABCDCDEFEFGG')
        stanzas = [4, 4, 4, 2]
    
    return PoemStructure(
        stanza_lengths=stanzas,
        syllable_pattern=[10] * 14,
        stress_patterns=['0101010101'] * 14,
        rhyme_scheme=rhyme,
        valence_arc=[0.2, 0.1, 0.3, 0.0,   # quatrain 1: neutral/warm
                     -0.1, -0.2, -0.1, -0.3, # quatrain 2: darkening
                     -0.2, 0.0, 0.1, 0.2,    # quatrain 3: turn
                     0.3, 0.4],               # couplet: resolution
        color_arc=[0.1] * 14,
        dominant_meter='iambic',
        foot_count=5,
        total_lines=14,
    )


def villanelle_blueprint() -> PoemStructure:
    """
    Villanelle: 19 lines, 5 tercets + 1 quatrain.
    Rhyme: ABA ABA ABA ABA ABA ABAA
    Refrains on lines 1, 6, 12, 18 and 3, 9, 15, 19.
    """
    # Simplified: focus on the ABA rhyme pattern
    rhyme = list('ABA') * 5 + list('ABAA')
    stanzas = [3, 3, 3, 3, 3, 4]
    
    return PoemStructure(
        stanza_lengths=stanzas,
        syllable_pattern=[10] * 19,
        stress_patterns=['0101010101'] * 19,
        rhyme_scheme=rhyme,
        valence_arc=[0.0, -0.1, 0.0,
                     -0.1, -0.2, 0.0,
                     -0.2, -0.3, 0.0,
                     -0.3, -0.4, 0.0,
                     -0.2, -0.1, 0.0,
                     0.1, 0.0, 0.2, 0.1],
        color_arc=[0.0] * 19,
        dominant_meter='iambic',
        foot_count=5,
        total_lines=19,
    )


def haiku_blueprint() -> PoemStructure:
    """Haiku: 5-7-5 syllables, no rhyme required."""
    return PoemStructure(
        stanza_lengths=[3],
        syllable_pattern=[5, 7, 5],
        stress_patterns=['10100', '1010010', '10100'],
        rhyme_scheme=['A', 'B', 'C'],
        valence_arc=[0.0, 0.0, 0.1],
        color_arc=[0.0, 0.0, 0.0],
        dominant_meter=None,
        foot_count=None,
        total_lines=3,
    )


def free_verse_blueprint(lines: int = 12, stanza_size: int = 4) -> PoemStructure:
    """
    Free verse with organic syllable variation and no strict rhyme.
    Uses golden ratio-ish syllable expansion/contraction.
    """
    import random
    
    # Organic syllable pattern: breathe in and out
    syllables = []
    base = 7
    for i in range(lines):
        phase = (i / lines) * 3.14159 * 2  # Full wave
        import math
        variation = int(math.sin(phase) * 4)
        syllables.append(base + variation + random.randint(-1, 1))
    
    num_stanzas = max(1, lines // stanza_size)
    stanza_lengths = [stanza_size] * (num_stanzas - 1)
    stanza_lengths.append(lines - sum(stanza_lengths))
    
    # Emotional arc: start neutral, descend, rise to resolution
    valence = []
    for i in range(lines):
        t = i / (lines - 1) if lines > 1 else 0
        # Parabolic arc: starts 0, dips to -0.4, rises to 0.3
        v = -1.6 * (t - 0.6) ** 2 + 0.3
        valence.append(round(v, 2))
    
    return PoemStructure(
        stanza_lengths=stanza_lengths,
        syllable_pattern=syllables,
        stress_patterns=[''] * lines,  # Free stress
        rhyme_scheme=[chr(65 + i % 26) for i in range(lines)],  # No rhyme
        valence_arc=valence,
        color_arc=[0.0] * lines,
        dominant_meter=None,
        foot_count=None,
        total_lines=lines,
    )


def ballad_blueprint(stanzas: int = 4) -> PoemStructure:
    """
    Ballad: alternating 8/6 syllable lines, ABAB or ABCB rhyme.
    """
    lines = stanzas * 4
    syllable_pattern = []
    rhyme_scheme = []
    
    for s in range(stanzas):
        syllable_pattern.extend([8, 6, 8, 6])
        base = chr(65 + s * 2)
        next_char = chr(66 + s * 2)
        rhyme_scheme.extend([base, next_char, base, next_char])
    
    valence = []
    for i in range(lines):
        stanza_progress = (i % 4) / 3
        overall_progress = i / (lines - 1) if lines > 1 else 0
        v = -0.2 * overall_progress + 0.1 * (1 - stanza_progress)
        valence.append(round(v, 2))
    
    return PoemStructure(
        stanza_lengths=[4] * stanzas,
        syllable_pattern=syllable_pattern,
        stress_patterns=['01010101', '010101', '01010101', '010101'] * stanzas,
        rhyme_scheme=rhyme_scheme,
        valence_arc=valence,
        color_arc=[0.0] * lines,
        dominant_meter='iambic',
        foot_count=4,
        total_lines=lines,
    )


def ghazal_blueprint(couplets: int = 5) -> PoemStructure:
    """
    Ghazal: series of couplets, AA BA CA DA EA pattern.
    Each couplet's second line ends with the same word/rhyme.
    Syllables: typically 10-14 per line.
    """
    lines = couplets * 2
    syllable_pattern = [12] * lines
    
    # AA BA CA DA EA - second line always rhymes with first couplet
    rhyme_scheme = []
    for i in range(couplets):
        if i == 0:
            rhyme_scheme.extend(['A', 'A'])
        else:
            rhyme_scheme.extend([chr(65 + i), 'A'])
    
    valence = []
    for i in range(lines):
        # Ghazals often carry longing
        v = -0.2 + 0.1 * ((i % 2) == 1)  # Slightly brighter on second lines
        valence.append(v)
    
    return PoemStructure(
        stanza_lengths=[2] * couplets,
        syllable_pattern=syllable_pattern,
        stress_patterns=[''] * lines,
        rhyme_scheme=rhyme_scheme,
        valence_arc=valence,
        color_arc=[0.0] * lines,
        dominant_meter=None,
        foot_count=None,
        total_lines=lines,
    )
