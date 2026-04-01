"""
Rich word lexicon with semantic, emotional, and phonetic metadata.
Words are organized by part-of-speech, syllable count, stress pattern,
and emotional valence for constrained generation.
"""
import random
from typing import List, Optional, Dict, Set, Tuple
from engines.phonetics import syllable_count, stress_pattern, emotional_color, get_phones

# ─── CURATED VOCABULARY ──────────────────────────────────────────────
# These are carefully chosen for poetic quality — not random dictionary dumps.

NOUNS = {
    # Nature / Elements
    'concrete': [
        'moon', 'sun', 'star', 'rain', 'snow', 'wind', 'stone', 'river',
        'ocean', 'mountain', 'forest', 'meadow', 'garden', 'desert', 'island',
        'valley', 'cliff', 'shore', 'lake', 'stream', 'tide', 'wave',
        'storm', 'thunder', 'lightning', 'frost', 'dew', 'mist', 'fog',
        'dawn', 'dusk', 'twilight', 'midnight', 'morning', 'evening',
        'spring', 'summer', 'autumn', 'winter',
        'rose', 'lily', 'thorn', 'vine', 'oak', 'willow', 'birch', 'elm',
        'petal', 'blossom', 'seed', 'root', 'branch', 'leaf', 'bloom',
        'sparrow', 'hawk', 'crow', 'owl', 'dove', 'wren', 'heron',
        'wolf', 'deer', 'fox', 'moth', 'bee', 'spider', 'whale',
        'flame', 'ember', 'ash', 'smoke', 'coal', 'fire', 'candle',
        'glass', 'mirror', 'shadow', 'echo', 'dust', 'silk', 'iron',
        'bone', 'blood', 'breath', 'skin', 'hand', 'eye', 'heart',
        'door', 'window', 'wall', 'bridge', 'tower', 'cathedral', 'ruin',
        'road', 'path', 'threshold', 'harbor', 'lantern', 'bell', 'clock',
        'grave', 'cradle', 'crown', 'knife', 'thread', 'needle', 'loom',
    ],
    'abstract': [
        'love', 'grief', 'joy', 'rage', 'peace', 'war', 'hope', 'fear',
        'truth', 'beauty', 'silence', 'absence', 'presence', 'memory',
        'longing', 'desire', 'sorrow', 'wonder', 'mercy', 'grace',
        'freedom', 'justice', 'honor', 'faith', 'doubt', 'wisdom',
        'courage', 'patience', 'hunger', 'thirst', 'yearning', 'loss',
        'darkness', 'brightness', 'distance', 'solitude', 'reckoning',
        'forgiveness', 'surrender', 'departure', 'return', 'becoming',
        'devotion', 'oblivion', 'reverence', 'defiance', 'tenderness',
        'anguish', 'rapture', 'stillness', 'chaos', 'order',
        'dream', 'sleep', 'death', 'life', 'time', 'fate', 'chance',
        'promise', 'secret', 'riddle', 'burden', 'blessing',
    ],
}

VERBS = {
    'motion': [
        'walk', 'run', 'fall', 'rise', 'drift', 'float', 'sink',
        'fly', 'soar', 'dive', 'climb', 'crawl', 'leap', 'dance',
        'wander', 'stumble', 'stagger', 'glide', 'sweep', 'tumble',
        'arrive', 'depart', 'return', 'vanish', 'emerge', 'descend',
        'scatter', 'gather', 'spiral', 'flow', 'pour', 'spill',
        'tremble', 'shiver', 'shudder', 'quiver', 'sway', 'ripple',
    ],
    'perception': [
        'see', 'hear', 'feel', 'taste', 'touch', 'smell',
        'watch', 'listen', 'witness', 'notice', 'glimpse',
        'remember', 'forget', 'recognize', 'imagine', 'dream',
        'know', 'believe', 'wonder', 'doubt', 'understand',
    ],
    'transformation': [
        'burn', 'melt', 'freeze', 'shatter', 'crack', 'break',
        'bloom', 'wither', 'fade', 'grow', 'decay', 'dissolve',
        'unfold', 'unravel', 'weave', 'forge', 'carve', 'shape',
        'heal', 'wound', 'mend', 'tear', 'stitch', 'bind',
        'become', 'remain', 'endure', 'surrender', 'transform',
    ],
    'communication': [
        'speak', 'whisper', 'shout', 'sing', 'call', 'cry',
        'murmur', 'chant', 'pray', 'confess', 'promise', 'swear',
        'tell', 'name', 'ask', 'answer', 'echo', 'silence',
    ],
    'being': [
        'be', 'exist', 'live', 'die', 'breathe', 'sleep', 'wake',
        'wait', 'linger', 'persist', 'haunt', 'dwell', 'belong',
        'ache', 'burn', 'glow', 'shine', 'gleam', 'flicker',
    ],
}

ADJECTIVES = {
    'sensory': [
        'bright', 'dark', 'warm', 'cold', 'soft', 'hard', 'rough',
        'smooth', 'sharp', 'dull', 'loud', 'quiet', 'sweet', 'bitter',
        'fragrant', 'heavy', 'light', 'thick', 'thin', 'vast',
        'deep', 'shallow', 'narrow', 'wide', 'tall', 'low',
        'crimson', 'silver', 'golden', 'azure', 'ivory', 'amber',
        'violet', 'scarlet', 'obsidian', 'pale', 'vivid', 'ashen',
    ],
    'emotional': [
        'lonely', 'tender', 'fierce', 'gentle', 'wild', 'calm',
        'restless', 'weary', 'eager', 'afraid', 'brave', 'proud',
        'humble', 'sacred', 'profane', 'holy', 'wicked', 'pure',
        'solemn', 'mournful', 'radiant', 'somber', 'luminous',
        'desolate', 'tranquil', 'reckless', 'patient', 'relentless',
    ],
    'temporal': [
        'ancient', 'young', 'old', 'new', 'eternal', 'fleeting',
        'endless', 'brief', 'sudden', 'slow', 'swift', 'lasting',
        'forgotten', 'remembered', 'lost', 'found', 'broken', 'whole',
        'first', 'last', 'final', 'silent', 'unspoken', 'unnamed',
    ],
}

ADVERBS = [
    'slowly', 'softly', 'gently', 'fiercely', 'quietly', 'deeply',
    'always', 'never', 'once', 'still', 'again', 'only',
    'here', 'there', 'now', 'then', 'somewhere', 'nowhere',
    'almost', 'barely', 'merely', 'wholly', 'partly',
]

PREPOSITIONS = [
    'in', 'on', 'by', 'with', 'through', 'beneath', 'above',
    'across', 'among', 'between', 'beyond', 'within', 'without',
    'against', 'along', 'beside', 'before', 'after', 'under', 'over',
    'toward', 'into', 'upon', 'around', 'behind', 'below',
]

CONJUNCTIONS = ['and', 'but', 'or', 'yet', 'for', 'nor', 'while', 'where', 'when', 'as', 'if', 'though']

PRONOUNS = ['I', 'you', 'we', 'they', 'she', 'he', 'it', 'one']

ARTICLES = ['the', 'a', 'an', 'this', 'that', 'each', 'every', 'no']

# ─── EMOTIONAL VALENCE MAP ────────────────────────────────────────────
# -1 = deeply negative, 0 = neutral, 1 = deeply positive
VALENCE = {
    # High positive
    'joy': 0.9, 'love': 0.8, 'hope': 0.7, 'beauty': 0.7, 'grace': 0.8,
    'bloom': 0.7, 'light': 0.6, 'bright': 0.6, 'dawn': 0.6, 'spring': 0.6,
    'sing': 0.7, 'dance': 0.7, 'golden': 0.5, 'warm': 0.5, 'gentle': 0.5,
    'tender': 0.5, 'blossom': 0.7, 'radiant': 0.7, 'luminous': 0.6,
    'mercy': 0.6, 'peace': 0.7, 'dream': 0.4, 'heal': 0.6,
    
    # Moderate positive
    'rise': 0.4, 'soar': 0.5, 'wonder': 0.4, 'shimmer': 0.3, 'star': 0.3,
    'garden': 0.3, 'meadow': 0.3, 'river': 0.2, 'silver': 0.2,
    
    # Neutral
    'stone': 0.0, 'dust': -0.1, 'glass': 0.0, 'mirror': 0.0, 'road': 0.0,
    'walk': 0.0, 'see': 0.0, 'know': 0.0, 'time': 0.0, 'door': 0.0,
    
    # Moderate negative
    'shadow': -0.3, 'storm': -0.3, 'winter': -0.3, 'cold': -0.3,
    'dark': -0.3, 'silence': -0.2, 'alone': -0.3, 'fade': -0.4,
    'wither': -0.4, 'fall': -0.3, 'dusk': -0.2, 'fog': -0.2,
    'weary': -0.4, 'restless': -0.3, 'wound': -0.5, 'ache': -0.4,
    
    # High negative
    'grief': -0.8, 'death': -0.7, 'loss': -0.7, 'sorrow': -0.8,
    'rage': -0.6, 'fear': -0.6, 'anguish': -0.9, 'darkness': -0.5,
    'shatter': -0.6, 'grave': -0.7, 'ruin': -0.6, 'decay': -0.6,
    'desolate': -0.7, 'oblivion': -0.6, 'wicked': -0.5, 'break': -0.5,
}


def get_valence(word: str) -> float:
    """Get emotional valence of a word."""
    return VALENCE.get(word.lower(), 0.0)


class WordBank:
    """Indexed word collection for constrained selection."""
    
    def __init__(self):
        self._all_words: Set[str] = set()
        self._by_syllables: Dict[int, List[str]] = {}
        self._by_stress: Dict[str, List[str]] = {}
        self._by_pos: Dict[str, List[str]] = {}
        self._build_index()
    
    def _build_index(self):
        """Build lookup indices for all words."""
        pos_map = {
            'noun': list(NOUNS['concrete']) + list(NOUNS['abstract']),
            'verb': sum(VERBS.values(), []),
            'adj': sum(ADJECTIVES.values(), []),
            'adv': ADVERBS,
            'prep': PREPOSITIONS,
            'conj': CONJUNCTIONS,
            'pron': PRONOUNS,
            'art': ARTICLES,
        }
        
        for pos, words in pos_map.items():
            self._by_pos[pos] = words
            for w in words:
                self._all_words.add(w)
                sc = syllable_count(w)
                sp = stress_pattern(w)
                self._by_syllables.setdefault(sc, []).append(w)
                self._by_stress.setdefault(sp, []).append(w)
    
    def find(self, pos: Optional[str] = None, syllables: Optional[int] = None,
             stress: Optional[str] = None, valence_range: Optional[Tuple[float, float]] = None,
             exclude: Optional[Set[str]] = None) -> List[str]:
        """Find words matching constraints."""
        candidates = list(self._all_words)
        
        if pos:
            pos_words = set(self._by_pos.get(pos, []))
            candidates = [w for w in candidates if w in pos_words]
        
        if syllables is not None:
            candidates = [w for w in candidates if syllable_count(w) == syllables]
        
        if stress:
            candidates = [w for w in candidates if stress_pattern(w) == stress]
        
        if valence_range:
            lo, hi = valence_range
            candidates = [w for w in candidates if lo <= get_valence(w) <= hi]
        
        if exclude:
            candidates = [w for w in candidates if w not in exclude]
        
        return candidates
    
    def pick(self, pos: Optional[str] = None, syllables: Optional[int] = None,
             stress: Optional[str] = None, valence_range: Optional[Tuple[float, float]] = None,
             exclude: Optional[Set[str]] = None) -> Optional[str]:
        """Pick a random word matching constraints."""
        matches = self.find(pos, syllables, stress, valence_range, exclude)
        return random.choice(matches) if matches else None
    
    def pick_rhyming(self, target: str, pos: Optional[str] = None,
                     exclude: Optional[Set[str]] = None) -> Optional[str]:
        """Pick a word that rhymes with target."""
        from engines.phonetics import find_rhymes
        candidates = self.find(pos=pos, exclude=exclude)
        rhymes = find_rhymes(target, candidates, min_strength=0.5)
        if rhymes:
            # Weighted random by rhyme strength
            words, strengths = zip(*rhymes)
            return random.choices(words, weights=strengths, k=1)[0]
        return None
    
    @property
    def all_nouns(self) -> List[str]:
        return self._by_pos.get('noun', [])
    
    @property
    def all_verbs(self) -> List[str]:
        return self._by_pos.get('verb', [])
    
    @property
    def all_adjectives(self) -> List[str]:
        return self._by_pos.get('adj', [])
