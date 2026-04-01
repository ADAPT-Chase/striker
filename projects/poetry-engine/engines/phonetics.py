"""
Phonetic analysis engine — works with CMU Pronouncing Dictionary
to understand syllables, stress, and rhyme relationships.
"""
import pronouncing
import re
from functools import lru_cache
from typing import List, Optional, Tuple


# Vowel phonemes in ARPAbet
VOWELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}

# Phoneme sonority for consonance/assonance detection
SONORITY = {
    'P': 1, 'B': 1, 'T': 1, 'D': 1, 'K': 1, 'G': 1,  # stops
    'CH': 2, 'JH': 2,  # affricates
    'F': 3, 'V': 3, 'TH': 3, 'DH': 3, 'S': 3, 'Z': 3, 'SH': 3, 'ZH': 3, 'HH': 3,  # fricatives
    'M': 4, 'N': 4, 'NG': 4,  # nasals
    'L': 5, 'R': 5,  # liquids
    'W': 6, 'Y': 6,  # glides
}

# Emotional color of vowel sounds (dark/bright spectrum, -1 to 1)
VOWEL_COLOR = {
    'AA': -0.6, 'AO': -0.5, 'UH': -0.4, 'UW': -0.3, 'OW': -0.2,
    'AH': 0.0, 'ER': 0.0,
    'AW': -0.1, 'OY': 0.1,
    'EH': 0.2, 'AE': 0.3, 'AY': 0.4, 'EY': 0.5, 'IH': 0.6, 'IY': 0.8,
}


@lru_cache(maxsize=8192)
def get_phones(word: str) -> Optional[str]:
    """Get ARPAbet pronunciation for a word."""
    phones = pronouncing.phones_for_word(word.lower())
    return phones[0] if phones else None


@lru_cache(maxsize=8192)
def syllable_count(word: str) -> int:
    """Count syllables using CMU dict, with fallback heuristic."""
    phones = get_phones(word)
    if phones:
        return pronouncing.syllable_count(phones)
    # Fallback: vowel-group heuristic
    word = word.lower().strip()
    if not word:
        return 0
    count = len(re.findall(r'[aeiouy]+', word))
    if word.endswith('e') and count > 1:
        count -= 1
    if word.endswith('le') and not word.endswith('ale') and count > 0:
        count += 1
    return max(1, count)


@lru_cache(maxsize=8192)
def stress_pattern(word: str) -> str:
    """
    Get stress pattern as string of 0/1/2.
    0 = unstressed, 1 = primary stress, 2 = secondary stress.
    """
    phones = get_phones(word)
    if phones:
        return pronouncing.stresses(phones)
    # Fallback: assume stress on first syllable
    n = syllable_count(word)
    if n == 1:
        return '1'
    return '1' + '0' * (n - 1)


def line_stress_pattern(words: List[str]) -> str:
    """Get combined stress pattern for a line of words."""
    return ''.join(stress_pattern(w) for w in words if w.isalpha())


def line_syllable_count(words: List[str]) -> int:
    """Count total syllables in a line."""
    return sum(syllable_count(w) for w in words if w.isalpha())


def rhyme_strength(word1: str, word2: str) -> float:
    """
    Measure rhyme strength from 0.0 (no rhyme) to 1.0 (perfect rhyme).
    Considers perfect rhyme, slant rhyme, assonance.
    """
    w1, w2 = word1.lower().strip(), word2.lower().strip()
    if w1 == w2:
        return 0.3  # Identity is weak rhyme poetically
    
    p1, p2 = get_phones(w1), get_phones(w2)
    if not p1 or not p2:
        return _fallback_rhyme(w1, w2)
    
    # Perfect rhyme check
    if w2 in pronouncing.rhymes(w1):
        return 1.0
    
    # Analyze ending phonemes
    ph1 = p1.split()
    ph2 = p2.split()
    
    # Find last stressed vowel position
    def last_stressed_vowel_idx(phones):
        for i in range(len(phones) - 1, -1, -1):
            base = re.sub(r'\d', '', phones[i])
            stress = re.findall(r'\d', phones[i])
            if base in VOWELS and stress and stress[0] in ('1', '2'):
                return i
        # Fall back to last vowel
        for i in range(len(phones) - 1, -1, -1):
            if re.sub(r'\d', '', phones[i]) in VOWELS:
                return i
        return -1
    
    idx1 = last_stressed_vowel_idx(ph1)
    idx2 = last_stressed_vowel_idx(ph2)
    
    if idx1 < 0 or idx2 < 0:
        return 0.0
    
    ending1 = [re.sub(r'\d', '', p) for p in ph1[idx1:]]
    ending2 = [re.sub(r'\d', '', p) for p in ph2[idx2:]]
    
    # Slant rhyme: same vowel, different consonant endings
    if ending1[0] == ending2[0]:  # Same vowel
        if ending1 == ending2:
            return 0.95  # Near-perfect
        # Partial match
        common = sum(1 for a, b in zip(ending1, ending2) if a == b)
        return 0.4 + 0.3 * (common / max(len(ending1), len(ending2)))
    
    # Assonance: similar vowels
    v1 = ending1[0] if ending1 else ''
    v2 = ending2[0] if ending2 else ''
    if v1 in VOWEL_COLOR and v2 in VOWEL_COLOR:
        vowel_dist = abs(VOWEL_COLOR[v1] - VOWEL_COLOR[v2])
        if vowel_dist < 0.3:
            return 0.3
    
    # Consonance: same consonant endings
    cons1 = [p for p in ending1 if p not in VOWELS]
    cons2 = [p for p in ending2 if p not in VOWELS]
    if cons1 and cons1 == cons2:
        return 0.35
    
    return 0.0


def _fallback_rhyme(w1: str, w2: str) -> float:
    """Fallback rhyme detection using string endings."""
    for length in [4, 3, 2]:
        if len(w1) >= length and len(w2) >= length and w1[-length:] == w2[-length:]:
            return 0.5 + 0.1 * length
    return 0.0


def emotional_color(word: str) -> float:
    """
    Estimate the 'brightness' of a word's sound from -1 (dark) to 1 (bright).
    Based on vowel sounds and consonant qualities.
    """
    phones = get_phones(word)
    if not phones:
        return 0.0
    
    phonemes = phones.split()
    colors = []
    for p in phonemes:
        base = re.sub(r'\d', '', p)
        if base in VOWEL_COLOR:
            colors.append(VOWEL_COLOR[base])
        elif base in SONORITY:
            # Hard consonants are darker, soft ones brighter
            colors.append((SONORITY[base] - 3.5) / 6.0)
    
    return sum(colors) / len(colors) if colors else 0.0


def find_rhymes(word: str, candidates: List[str], min_strength: float = 0.5) -> List[Tuple[str, float]]:
    """Find words from candidates that rhyme with the given word."""
    results = []
    for c in candidates:
        strength = rhyme_strength(word, c)
        if strength >= min_strength:
            results.append((c, strength))
    return sorted(results, key=lambda x: -x[1])
