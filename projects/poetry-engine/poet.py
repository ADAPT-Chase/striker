#!/usr/bin/env python3
"""
Poetry Engine — generates poetry by analyzing mathematical structure
of meter, rhyme, stress patterns, and emotional tone.

Usage:
    python3 poet.py                    # Generate free verse
    python3 poet.py --form sonnet      # Generate a sonnet
    python3 poet.py --form haiku       # Generate a haiku
    python3 poet.py --form villanelle  # Generate a villanelle
    python3 poet.py --form limerick    # Generate a limerick
    python3 poet.py --form ghazal      # Generate a ghazal
    python3 poet.py --tone dark        # Set emotional tone
    python3 poet.py --theme night      # Set theme
    python3 poet.py --count 3          # Generate multiple poems
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from engines.generator import PoemGenerator
from engines import forms

FORM_MAP = {
    'sonnet': forms.sonnet_blueprint,
    'haiku': forms.haiku_blueprint,
    'villanelle': forms.villanelle_blueprint,
    'ballad': forms.ballad_blueprint,
    'free': forms.free_verse_blueprint,
    'ghazal': forms.ghazal_blueprint,
}

def main():
    parser = argparse.ArgumentParser(description="Poetry Engine — mathematical poetry generation")
    parser.add_argument("--form", default="free", choices=list(FORM_MAP.keys()),
                       help="Poetic form to generate")
    parser.add_argument("--tone", default=None, 
                       help="Emotional tone (dark, bright, melancholy, fierce, tender, cosmic)")
    parser.add_argument("--theme", default=None,
                       help="Theme seed word")
    parser.add_argument("--count", type=int, default=1,
                       help="Number of poems to generate")
    parser.add_argument("--seed", type=int, default=None,
                       help="Random seed for reproducibility")
    
    args = parser.parse_args()
    
    gen = PoemGenerator(seed=args.seed)
    
    for i in range(args.count):
        if i > 0:
            print("\n" + "—" * 40 + "\n")
        
        blueprint_fn = FORM_MAP[args.form]
        structure = blueprint_fn()
        theme_words = [args.theme] if args.theme else None
        temp = 0.5 if args.tone == 'dark' else 0.8 if args.tone == 'bright' else 0.7
        poem = gen.generate(blueprint=structure, theme_words=theme_words, temperature=temp)
        print(poem)

if __name__ == "__main__":
    main()
