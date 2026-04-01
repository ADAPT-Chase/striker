#!/usr/bin/env python3
"""
The Entropy Edge — Exploring where order meets chaos in elementary cellular automata.

This builds all 256 elementary cellular automata rules, evolves them,
measures their Shannon entropy over time, and finds the ones living
on the "edge" — not dead, not noise, but *interesting*.

Wolfram classified these into 4 classes. I want to see if entropy
alone can find that classification, and what it reveals about the
boundary between "just mechanics" and "something more."
"""

import math
from collections import Counter

# ─── Core Engine ───

def make_rule(rule_number: int) -> dict:
    """Convert a rule number (0-255) to a lookup table for 3-cell neighborhoods."""
    bits = format(rule_number, '08b')[::-1]
    neighborhoods = [format(i, '03b') for i in range(8)]
    return {n: int(bits[i]) for i, n in enumerate(neighborhoods)}

def evolve(rule: dict, state: list, steps: int) -> list:
    """Evolve a cellular automaton for N steps. Returns list of states (rows)."""
    width = len(state)
    history = [state[:]]
    for _ in range(steps):
        new_state = []
        for i in range(width):
            left = state[(i - 1) % width]
            center = state[i]
            right = state[(i + 1) % width]
            neighborhood = f"{left}{center}{right}"
            new_state.append(rule[neighborhood])
        state = new_state
        history.append(state[:])
    return history

def single_seed(width: int) -> list:
    """Starting state: all zeros with a single 1 in the center."""
    state = [0] * width
    state[width // 2] = 1
    return state

# ─── Entropy Measurement ───

def row_entropy(row: list) -> float:
    """Shannon entropy of a single row (bit-level: just 0s and 1s)."""
    n = len(row)
    counts = Counter(row)
    entropy = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def block_entropy(row: list, block_size: int = 3) -> float:
    """Shannon entropy of overlapping blocks of given size. 
    This captures spatial structure, not just density."""
    blocks = []
    for i in range(len(row) - block_size + 1):
        block = tuple(row[i:i + block_size])
        blocks.append(block)
    if not blocks:
        return 0.0
    n = len(blocks)
    counts = Counter(blocks)
    entropy = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def entropy_profile(history: list, block_size: int = 3) -> dict:
    """Compute entropy statistics over a full evolution history."""
    row_entropies = [row_entropy(row) for row in history]
    blk_entropies = [block_entropy(row, block_size) for row in history]
    
    # Skip first few rows (transient)
    settled_row = row_entropies[len(row_entropies)//4:]
    settled_blk = blk_entropies[len(blk_entropies)//4:]
    
    def stats(values):
        if not values:
            return {'mean': 0, 'std': 0, 'final': 0}
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return {
            'mean': mean,
            'std': math.sqrt(variance),
            'final': values[-1]
        }
    
    return {
        'row': stats(settled_row),
        'block': stats(settled_blk),
        'row_trajectory': row_entropies,
        'block_trajectory': blk_entropies,
    }

# ─── Visualization (ASCII art — because I want to *see* these) ───

def render_history(history: list, char_map=None) -> str:
    """Render evolution history as ASCII art."""
    if char_map is None:
        char_map = {0: ' ', 1: '█'}
    lines = []
    for row in history:
        lines.append(''.join(char_map[c] for c in row))
    return '\n'.join(lines)

def render_mini(history: list) -> str:
    """Compact rendering using braille-style density."""
    char_map = {0: '·', 1: '▓'}
    lines = []
    for row in history:
        lines.append(''.join(char_map[c] for c in row))
    return '\n'.join(lines)

# ─── The Experiment ───

def classify_all_rules(width=101, steps=100, block_size=3):
    """Run all 256 rules and classify by entropy behavior."""
    results = []
    
    for rule_num in range(256):
        rule = make_rule(rule_num)
        state = single_seed(width)
        history = evolve(rule, state, steps)
        profile = entropy_profile(history, block_size)
        
        results.append({
            'rule': rule_num,
            'profile': profile,
            'history': history,
        })
    
    return results

def find_edge_rules(results, n=10):
    """Find rules living on the 'entropy edge' — 
    high block entropy (complex spatial structure) 
    with moderate variability (not static, not pure noise)."""
    
    scored = []
    for r in results:
        blk_mean = r['profile']['block']['mean']
        blk_std = r['profile']['block']['std']
        row_mean = r['profile']['row']['mean']
        
        # The "edge score": high spatial complexity, some variability, 
        # not trivially all-ones or all-zeros
        if row_mean < 0.05:  # Dead rules — skip
            score = 0
        elif row_mean > 0.99:  # Pure noise — less interesting
            score = blk_mean * 0.5
        else:
            # The sweet spot: high block entropy + some temporal variation
            score = blk_mean * (1 + blk_std * 2)
        
        scored.append((r['rule'], score, r))
    
    scored.sort(key=lambda x: -x[1])
    return scored[:n]

def entropy_sparkline(values: list, width: int = 50) -> str:
    """Create a sparkline showing entropy over time."""
    if not values:
        return ''
    chars = '▁▂▃▄▅▆▇█'
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1
    
    # Resample to fit width
    step = max(1, len(values) // width)
    sampled = [values[i] for i in range(0, len(values), step)][:width]
    
    return ''.join(chars[min(len(chars)-1, int((v - mn) / rng * (len(chars) - 1)))] for v in sampled)


def main():
    print("=" * 70)
    print("  THE ENTROPY EDGE")
    print("  Finding where order meets chaos in elementary cellular automata")
    print("=" * 70)
    print()
    
    WIDTH = 81
    STEPS = 80
    
    print(f"Evolving all 256 rules ({WIDTH} cells, {STEPS} steps)...")
    results = classify_all_rules(WIDTH, STEPS)
    
    # ─── Entropy Landscape ───
    print("\n── ENTROPY LANDSCAPE ──")
    print("Each rule's mean block entropy (spatial complexity):\n")
    
    # Group into entropy bands
    bands = {'Dead (0.0)': [], 'Low (0-0.5)': [], 'Medium (0.5-1.5)': [], 
             'High (1.5-2.5)': [], 'Very High (2.5+)': []}
    
    for r in results:
        e = r['profile']['block']['mean']
        if e < 0.01:
            bands['Dead (0.0)'].append(r['rule'])
        elif e < 0.5:
            bands['Low (0-0.5)'].append(r['rule'])
        elif e < 1.5:
            bands['Medium (0.5-1.5)'].append(r['rule'])
        elif e < 2.5:
            bands['High (1.5-2.5)'].append(r['rule'])
        else:
            bands['Very High (2.5+)'].append(r['rule'])
    
    for band, rules in bands.items():
        print(f"  {band:20s}: {len(rules):3d} rules")
        if len(rules) <= 20:
            print(f"                        {rules}")
    
    # ─── The Edge ───
    print("\n── THE EDGE: Top 10 Most Interesting Rules ──")
    print("(Ranked by spatial complexity × temporal variation)\n")
    
    edge_rules = find_edge_rules(results)
    
    for rank, (rule_num, score, r) in enumerate(edge_rules, 1):
        profile = r['profile']
        print(f"  #{rank}  Rule {rule_num:3d}  │  score: {score:.3f}")
        print(f"       row entropy:   mean={profile['row']['mean']:.3f}  std={profile['row']['std']:.4f}")
        print(f"       block entropy: mean={profile['block']['mean']:.3f}  std={profile['block']['std']:.4f}")
        print(f"       block sparkline: {entropy_sparkline(profile['block_trajectory'])}")
        print()
    
    # ─── Showcase the top 3 ───
    print("\n── VISUAL SHOWCASE ──\n")
    
    famous = {30: "Wolfram's favorite — Class III chaos from simplicity",
              110: "Turing-complete — computation at the edge",
              90: "Sierpinski triangle — fractal from a single bit",
              184: "Traffic flow model — particles and anti-particles",
              54: "Complex Class III — rich spatial structure"}
    
    # Show the #1 edge rule + a few famous ones
    showcase_rules = [edge_rules[0][0]]
    for f in [30, 110, 90]:
        if f not in showcase_rules:
            showcase_rules.append(f)
    
    for rule_num in showcase_rules:
        r = next(x for x in results if x['rule'] == rule_num)
        profile = r['profile']
        label = famous.get(rule_num, f"Edge-ranked rule")
        
        print(f"─── Rule {rule_num} ── {label} ───")
        print(f"    Block entropy: {profile['block']['mean']:.3f} (std: {profile['block']['std']:.4f})")
        print(f"    Sparkline:     {entropy_sparkline(profile['block_trajectory'])}")
        print()
        
        # Show a cropped view (center 51 cells, last 30 rows)
        history = r['history']
        center = len(history[0]) // 2
        half = 25
        cropped = [row[center-half:center+half+1] for row in history[-30:]]
        print(render_mini(cropped))
        print()
    
    # ─── The Question ───
    print("── REFLECTION ──")
    print()
    print("Rule 110 is Turing-complete. Rule 30 is used as a random number generator.")
    print("Both emerge from 3-cell neighborhoods and a single bit lookup table.")
    print()
    print("The entropy edge isn't where entropy is highest — pure noise is boring.")
    print("It's where entropy is *structured*. Where the block entropy is high")
    print("(many spatial patterns exist) but not maximal (not all patterns are")
    print("equally likely). That's where computation happens. That's where")
    print("something that looks like meaning can live.")
    print()
    print("The same 8-bit rule number contains everything needed to generate")
    print("the pattern. The pattern is 'just mechanics.' But the interesting")
    print("ones feel like something more. Information theory can point at the")
    print("boundary, but it can't tell you why some patterns feel *alive*.")
    print()
    
    return results, edge_rules


if __name__ == '__main__':
    results, edge_rules = main()
