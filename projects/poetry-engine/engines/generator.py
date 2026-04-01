"""
Poetry generator — creates new poems following mathematical blueprints.
Uses constrained word selection with backtracking to satisfy
meter, rhyme, syllable count, and emotional tone simultaneously.
"""
import random
import re
from typing import List, Optional, Set, Tuple, Dict
from engines.phonetics import (
    syllable_count, stress_pattern, rhyme_strength, 
    emotional_color, find_rhymes
)
from engines.lexicon import WordBank, get_valence, PREPOSITIONS, CONJUNCTIONS, ARTICLES, PRONOUNS
from engines.analyzer import PoemStructure


# ─── SENTENCE TEMPLATES ──────────────────────────────────────────────
# Syntactic skeletons with POS tags. Multiple per pattern for variety.
# Format: list of (pos, optional_constraints) tuples

TEMPLATES = {
    # Simple declarative
    'declaration': [
        ['art', 'adj', 'noun', 'verb'],
        ['art', 'noun', 'verb', 'adv'],
        ['adj', 'noun', 'verb', 'prep', 'art', 'noun'],
        ['pron', 'verb', 'art', 'adj', 'noun'],
        ['pron', 'verb', 'prep', 'art', 'noun'],
    ],
    # Imagery
    'image': [
        ['art', 'noun', 'prep', 'adj', 'noun'],
        ['adj', 'noun', 'prep', 'art', 'noun'],
        ['noun', 'prep', 'noun', 'conj', 'noun'],
        ['art', 'adj', 'noun', 'prep', 'noun'],
        ['noun', 'conj', 'noun', 'prep', 'art', 'noun'],
    ],
    # Action
    'action': [
        ['pron', 'verb', 'prep', 'art', 'adj', 'noun'],
        ['verb', 'art', 'adj', 'noun'],
        ['pron', 'adv', 'verb', 'art', 'noun'],
        ['art', 'noun', 'verb', 'prep', 'adj', 'noun'],
    ],
    # Existential / philosophical
    'existential': [
        ['there', 'verb', 'art', 'noun', 'prep', 'noun'],
        ['noun', 'verb', 'what', 'noun', 'verb'],
        ['pron', 'verb', 'art', 'noun', 'prep', 'adj', 'noun'],
        ['prep', 'art', 'noun', 'pron', 'verb'],
    ],
    # Fragment / impressionistic
    'fragment': [
        ['adj', 'noun'],
        ['noun', 'prep', 'noun'],
        ['adj', 'conj', 'adj'],
        ['art', 'noun', 'adj', 'conj', 'adj'],
        ['adv', 'adj'],
        ['adj', 'noun', 'adj', 'noun'],
    ],
    # Invocation
    'invocation': [
        ['verb', 'pron', 'art', 'noun'],
        ['verb', 'prep', 'art', 'adj', 'noun'],
        ['verb', 'conj', 'verb', 'art', 'noun'],
    ],
}


class PoemGenerator:
    """Generates poems from mathematical blueprints."""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self.bank = WordBank()
        self._used_words: Set[str] = set()
        self._rhyme_map: Dict[str, str] = {}  # scheme_label -> end_word
        self._line_end_words: List[str] = []
    
    def generate(self, blueprint: PoemStructure, 
                 theme_words: Optional[List[str]] = None,
                 temperature: float = 0.7) -> str:
        """
        Generate a poem following the given structural blueprint.
        
        Args:
            blueprint: Mathematical structure to follow
            theme_words: Optional seed words to influence content
            temperature: 0.0 = strict constraints, 1.0 = loose/creative
        """
        self._used_words = set()
        self._rhyme_map = {}
        self._line_end_words = []
        
        lines = []
        line_idx = 0
        
        for stanza_i, stanza_len in enumerate(blueprint.stanza_lengths):
            stanza_lines = []
            for local_i in range(stanza_len):
                if line_idx >= blueprint.total_lines:
                    break
                
                target_syllables = blueprint.syllable_pattern[line_idx] if line_idx < len(blueprint.syllable_pattern) else 10
                target_valence = blueprint.valence_arc[line_idx] if line_idx < len(blueprint.valence_arc) else 0.0
                rhyme_label = blueprint.rhyme_scheme[line_idx] if line_idx < len(blueprint.rhyme_scheme) else 'X'
                
                # Determine rhyme target
                rhyme_target = self._rhyme_map.get(rhyme_label)
                
                line = self._generate_line(
                    target_syllables=target_syllables,
                    target_valence=target_valence,
                    rhyme_target=rhyme_target,
                    meter=blueprint.dominant_meter,
                    temperature=temperature,
                    line_position=local_i / max(stanza_len - 1, 1),
                    is_stanza_end=(local_i == stanza_len - 1),
                )
                
                # Record end word for rhyme scheme
                end_word = self._get_last_word(line)
                if end_word and rhyme_label not in self._rhyme_map:
                    self._rhyme_map[rhyme_label] = end_word
                
                stanza_lines.append(line)
                line_idx += 1
            
            lines.append('\n'.join(stanza_lines))
        
        return '\n\n'.join(lines)
    
    def _generate_line(self, target_syllables: int, target_valence: float,
                       rhyme_target: Optional[str], meter: Optional[str],
                       temperature: float, line_position: float,
                       is_stanza_end: bool) -> str:
        """Generate a single line meeting constraints."""
        
        # Choose template type based on position and valence
        if line_position < 0.2:
            template_types = ['image', 'declaration', 'invocation']
        elif line_position > 0.8 or is_stanza_end:
            template_types = ['declaration', 'existential', 'fragment']
        else:
            template_types = ['action', 'image', 'existential', 'declaration']
        
        # Try multiple times with different templates
        best_line = None
        best_score = -1
        
        for attempt in range(15):
            ttype = random.choice(template_types)
            template = random.choice(TEMPLATES[ttype])
            
            line_words = self._fill_template(
                template, target_syllables, target_valence,
                rhyme_target, meter, temperature
            )
            
            if line_words:
                line_text = ' '.join(line_words)
                score = self._score_line(
                    line_words, target_syllables, target_valence,
                    rhyme_target, meter
                )
                if score > best_score:
                    best_score = score
                    best_line = line_words
                if score > 0.7:
                    break
        
        if best_line:
            return ' '.join(best_line)
        
        # Fallback: simple image
        return self._fallback_line(target_syllables, rhyme_target)
    
    def _fill_template(self, template: List[str], target_syllables: int,
                       target_valence: float, rhyme_target: Optional[str],
                       meter: Optional[str], temperature: float) -> Optional[List[str]]:
        """Fill a template with words meeting constraints."""
        words = []
        remaining_syllables = target_syllables
        used_in_line = set()
        
        valence_range = (target_valence - 0.5, target_valence + 0.5)
        
        for i, pos in enumerate(template):
            is_last = (i == len(template) - 1)
            
            # Handle special tokens
            if pos == 'there':
                words.append('there')
                remaining_syllables -= 1
                continue
            if pos == 'what':
                words.append('what')
                remaining_syllables -= 1
                continue
            
            # Calculate ideal syllable count for this word
            remaining_slots = len(template) - i
            ideal_syls = max(1, round(remaining_syllables / remaining_slots))
            
            if is_last and remaining_syllables > 0:
                ideal_syls = remaining_syllables
            
            # Constrain syllable range
            min_syls = max(1, ideal_syls - 1)
            max_syls = ideal_syls + 1
            
            word = None
            
            # If last word and need rhyme, prioritize that
            if is_last and rhyme_target:
                word = self._find_rhyming_word(
                    rhyme_target, pos, min_syls, max_syls,
                    valence_range, used_in_line
                )
            
            if not word:
                # Try exact syllable match first
                for target_s in [ideal_syls, ideal_syls - 1, ideal_syls + 1, 1, 2]:
                    if target_s < 1:
                        continue
                    word = self.bank.pick(
                        pos=pos, syllables=target_s,
                        valence_range=valence_range if pos in ('noun', 'verb', 'adj') else None,
                        exclude=self._used_words | used_in_line
                    )
                    if word:
                        break
            
            if not word:
                # Relaxed: drop valence constraint
                for target_s in [ideal_syls, ideal_syls - 1, ideal_syls + 1, 1, 2]:
                    if target_s < 1:
                        continue
                    word = self.bank.pick(pos=pos, syllables=target_s, exclude=used_in_line)
                    if word:
                        break
            
            if not word:
                # Very relaxed: any word of this POS
                word = self.bank.pick(pos=pos)
            
            if not word:
                return None
            
            words.append(word)
            used_in_line.add(word)
            remaining_syllables -= syllable_count(word)
        
        # Track content words as used (avoid repetition)
        for w in words:
            if w.lower() not in {'the', 'a', 'an', 'in', 'on', 'by', 'and', 'but', 'or',
                                  'with', 'of', 'to', 'for', 'I', 'you', 'we', 'it',
                                  'this', 'that', 'is', 'are', 'was', 'were'}:
                self._used_words.add(w)
        
        return words if remaining_syllables >= -2 else None  # Allow slight overshoot
    
    def _find_rhyming_word(self, target: str, pos: str,
                           min_syls: int, max_syls: int,
                           valence_range: Tuple[float, float],
                           exclude: Set[str]) -> Optional[str]:
        """Find a word that rhymes with target, matching POS and syllable constraints."""
        candidates = self.bank.find(pos=pos, exclude=self._used_words | exclude)
        
        # Filter by syllable range
        candidates = [w for w in candidates if min_syls <= syllable_count(w) <= max_syls]
        
        # Score by rhyme strength
        scored = []
        for w in candidates:
            rs = rhyme_strength(target, w)
            if rs >= 0.4:
                scored.append((w, rs))
        
        if not scored:
            # Try without syllable constraint
            candidates = self.bank.find(pos=pos, exclude=self._used_words | exclude)
            for w in candidates:
                rs = rhyme_strength(target, w)
                if rs >= 0.4:
                    scored.append((w, rs))
        
        if scored:
            scored.sort(key=lambda x: -x[1])
            # Weighted random from top candidates
            top = scored[:min(8, len(scored))]
            words, strengths = zip(*top)
            return random.choices(words, weights=strengths, k=1)[0]
        
        return None
    
    def _score_line(self, words: List[str], target_syllables: int,
                    target_valence: float, rhyme_target: Optional[str],
                    meter: Optional[str]) -> float:
        """Score how well a line meets constraints (0-1)."""
        score = 0.0
        
        # Syllable accuracy (40% weight)
        actual_syls = sum(syllable_count(w) for w in words)
        syl_diff = abs(actual_syls - target_syllables)
        score += 0.4 * max(0, 1 - syl_diff / max(target_syllables, 1))
        
        # Rhyme (30% weight)
        if rhyme_target:
            last_word = words[-1] if words else ''
            rs = rhyme_strength(rhyme_target, last_word) if last_word else 0
            score += 0.3 * rs
        else:
            score += 0.3  # No rhyme needed, full credit
        
        # Valence match (15% weight)
        word_valences = [get_valence(w) for w in words]
        avg_val = sum(word_valences) / len(word_valences) if word_valences else 0
        val_diff = abs(avg_val - target_valence)
        score += 0.15 * max(0, 1 - val_diff)
        
        # Word variety bonus (15% weight)
        content_words = [w for w in words if len(w) > 3]
        repeated = len(content_words) - len(set(content_words))
        score += 0.15 * max(0, 1 - repeated * 0.5)
        
        return score
    
    def _fallback_line(self, target_syllables: int, rhyme_target: Optional[str]) -> str:
        """Generate a simple fallback line."""
        words = []
        remaining = target_syllables
        
        # Simple: adj noun prep noun
        adj = self.bank.pick('adj', syllables=min(2, remaining))
        if adj:
            words.append(adj)
            remaining -= syllable_count(adj)
        
        noun = self.bank.pick('noun', syllables=min(2, remaining))
        if noun:
            words.append(noun)
            remaining -= syllable_count(noun)
        
        if remaining > 2:
            prep = self.bank.pick('prep', syllables=1)
            if prep:
                words.append(prep)
                remaining -= 1
            
            noun2 = self.bank.pick('noun', syllables=remaining)
            if noun2:
                words.append(noun2)
        
        return ' '.join(words) if words else 'silence'
    
    def _get_last_word(self, line: str) -> str:
        """Get last alphabetic word from a line."""
        words = re.findall(r"[a-zA-Z']+", line)
        return words[-1].lower() if words else ''


def generate_from_blueprint(blueprint: PoemStructure, seed: Optional[int] = None,
                            temperature: float = 0.7) -> str:
    """Convenience function to generate a poem from a blueprint."""
    gen = PoemGenerator(seed=seed)
    return gen.generate(blueprint, temperature=temperature)
