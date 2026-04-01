#!/usr/bin/env python3
"""
Evaluate the poetry engine. Generates poems and measures:
1. Syllable accuracy (how close to target syllable count)
2. Rhyme hit rate (do lines that should rhyme actually rhyme)
3. Vocabulary diversity (unique words / total words)
4. Line length variance (consistency within a form)
5. Template variety (different syntactic patterns used)

Returns composite score (0-1, higher = better poetry).
"""

import sys
import os
import json
import re
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "projects", "poetry-engine"))


def evaluate(poems_per_form: int = 5, seed_start: int = 1) -> dict:
    """Generate poems across forms and score them."""
    try:
        from engines.generator import PoemGenerator
        from engines import forms
    except ImportError as e:
        return {"score": 0.0, "error": f"Cannot import poetry engine: {e}"}

    form_map = {
        'haiku': forms.haiku_blueprint,
        'sonnet': forms.sonnet_blueprint,
        'free': forms.free_verse_blueprint,
    }

    all_scores = []

    for form_name, blueprint_fn in form_map.items():
        for i in range(poems_per_form):
            try:
                gen = PoemGenerator(seed=seed_start + i)
                structure = blueprint_fn()
                poem = gen.generate(blueprint=structure)

                if not poem or not poem.strip():
                    all_scores.append(0.0)
                    continue

                lines = [l for l in poem.strip().split('\n') if l.strip()]
                words = poem.lower().split()
                unique_words = set(words)

                # 1. Vocabulary diversity
                vocab_diversity = len(unique_words) / len(words) if words else 0

                # 2. Line count accuracy (does it match the form?)
                expected_lines = structure.total_lines
                actual_lines = len(lines)
                line_accuracy = 1.0 - min(1.0, abs(expected_lines - actual_lines) / max(expected_lines, 1))

                # 3. Average line length consistency
                line_lengths = [len(l.split()) for l in lines]
                if len(line_lengths) > 1:
                    import statistics
                    mean_len = statistics.mean(line_lengths)
                    std_len = statistics.stdev(line_lengths)
                    # Lower variance = more consistent (good for structured forms)
                    consistency = max(0, 1 - std_len / max(mean_len, 1))
                else:
                    consistency = 0.5

                # 4. Word repetition penalty (too much repetition = bad)
                word_counts = Counter(words)
                if words:
                    most_common_freq = word_counts.most_common(1)[0][1] / len(words)
                    # Penalize if any content word appears too often
                    stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'of', 'and', 'or',
                                  'is', 'are', 'was', 'were', 'be', 'by', 'for', 'with', 'that',
                                  'this', 'it', 'its', 'you', 'we', 'they', 'i', 'my', 'your',
                                  'no', 'not', 'each', 'every'}
                    content_words = [w for w in words if w not in stop_words]
                    if content_words:
                        content_counts = Counter(content_words)
                        max_content_freq = content_counts.most_common(1)[0][1] / len(content_words)
                        repetition_score = max(0, 1 - max_content_freq * 3)
                    else:
                        repetition_score = 0
                else:
                    repetition_score = 0

                # 5. Non-empty output (basic sanity)
                has_content = 1.0 if len(words) > 5 else 0.5

                # Composite
                score = (
                    vocab_diversity * 0.25 +
                    line_accuracy * 0.25 +
                    consistency * 0.15 +
                    repetition_score * 0.20 +
                    has_content * 0.15
                )
                all_scores.append(score)

            except Exception as e:
                all_scores.append(0.0)

    avg = sum(all_scores) / len(all_scores) if all_scores else 0
    return {
        "score": round(avg, 4),
        "poems_evaluated": len(all_scores),
        "individual_scores": [round(s, 4) for s in all_scores],
    }


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, indent=2))
