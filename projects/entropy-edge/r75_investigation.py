#!/usr/bin/env python3
"""
R75/R89 Investigation — The Mystery Rules

R75 and R89 rank #1 and #3 on the triple point V2 metric.
They have IDENTICAL memory and transformation scores.
Are they equivalent rules? Are they genuinely computational?
Or has the metric found a new blind spot?

Rule 75 in binary: 01001011
Rule 89 in binary: 01011001

Let's find out what they do.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from automata import make_rule, evolve, single_seed, block_entropy, entropy_sparkline

def binary_rule(n):
    """Show the rule table."""
    bits = format(n, '08b')
    neighborhoods = ['111', '110', '101', '100', '011', '010', '001', '000']
    return {n: int(b) for n, b in zip(neighborhoods, bits)}

def render_spacetime(history, width=60):
    """Render spacetime diagram as text."""
    for t, row in enumerate(history):
        # Center and crop to width
        center = len(row) // 2
        start = max(0, center - width // 2)
        end = min(len(row), center + width // 2)
        line = ''.join('█' if row[i] else ' ' for i in range(start, end))
        print(f"  {t:3d}│{line}│")

def rule_equivalences(n):
    """Check if rule n is equivalent to another rule via reflection or complement."""
    bits = format(n, '08b')
    neighborhoods = ['111', '110', '101', '100', '011', '010', '001', '000']
    
    # Reflection: swap left/right in neighborhoods
    reflected = {}
    for nbr, out in zip(neighborhoods, bits):
        reflected_nbr = nbr[::-1]
        reflected[reflected_nbr] = int(out)
    # Convert back to rule number
    reflect_bits = ''.join(str(reflected[n]) for n in neighborhoods)
    reflect_rule = int(reflect_bits, 2)
    
    # Complement: flip all inputs and outputs
    complemented = {}
    for nbr, out in zip(neighborhoods, bits):
        comp_nbr = ''.join('1' if c == '0' else '0' for c in nbr)
        complemented[comp_nbr] = 1 - int(out)
    comp_bits = ''.join(str(complemented[n]) for n in neighborhoods)
    comp_rule = int(comp_bits, 2)
    
    # Reflection + Complement
    rc = {}
    for nbr, out in zip(neighborhoods, bits):
        rc_nbr = ''.join('1' if c == '0' else '0' for c in nbr[::-1])
        rc[rc_nbr] = 1 - int(out)
    rc_bits = ''.join(str(rc[n]) for n in neighborhoods)
    rc_rule = int(rc_bits, 2)
    
    return {
        'original': n,
        'reflected': reflect_rule,
        'complemented': comp_rule,
        'reflected_complemented': rc_rule,
    }

def density_response(rule_num, densities=[0.1, 0.3, 0.5, 0.7, 0.9], width=101, steps=100):
    """How does the rule respond to different initial densities?"""
    rule = make_rule(rule_num)
    results = []
    for d in densities:
        import random
        random.seed(42)
        state = [1 if random.random() < d else 0 for _ in range(width)]
        history = evolve(rule, state, steps)
        final_density = sum(history[-1]) / len(history[-1])
        # Entropy of last quarter
        entropies = [block_entropy(row, 3) for row in history[steps//4:]]
        avg_entropy = sum(entropies) / len(entropies)
        results.append({
            'initial_density': d,
            'final_density': final_density,
            'avg_entropy': avg_entropy,
        })
    return results

def sensitivity_test(rule_num, width=101, steps=100, num_trials=20):
    """How sensitive is the rule to single-bit perturbations?"""
    import random
    random.seed(42)
    rule = make_rule(rule_num)
    
    damages = []
    for trial in range(num_trials):
        state = [random.randint(0, 1) for _ in range(width)]
        perturbed = state[:]
        flip_pos = random.randint(0, width - 1)
        perturbed[flip_pos] = 1 - perturbed[flip_pos]
        
        hist_orig = evolve(rule, state, steps)
        hist_pert = evolve(rule, perturbed, steps)
        
        # Hamming distance at final timestep
        final_hamming = sum(a != b for a, b in zip(hist_orig[-1], hist_pert[-1])) / width
        damages.append(final_hamming)
    
    return {
        'mean_damage': sum(damages) / len(damages),
        'max_damage': max(damages),
        'min_damage': min(damages),
    }


def main():
    print("=" * 78)
    print("  R75/R89 INVESTIGATION — The Mystery Rules")
    print("=" * 78)
    
    # Rule tables
    for rn in [75, 89, 110, 30]:
        table = binary_rule(rn)
        bits = format(rn, '08b')
        print(f"\n  Rule {rn} (binary: {bits}):")
        print(f"    ", end="")
        for nbr, out in table.items():
            print(f"{nbr}→{out} ", end="")
        print()
    
    # Equivalences
    print(f"\n{'='*78}")
    print(f"  RULE EQUIVALENCES")
    print(f"{'='*78}\n")
    
    for rn in [75, 89, 110, 30]:
        eq = rule_equivalences(rn)
        print(f"  Rule {rn}: reflect={eq['reflected']}, complement={eq['complemented']}, "
              f"reflect+comp={eq['reflected_complemented']}")
    
    # Are R75 and R89 equivalent?
    eq75 = rule_equivalences(75)
    eq89 = rule_equivalences(89)
    if 89 in eq75.values():
        for name, val in eq75.items():
            if val == 89:
                print(f"\n  ✅ R75 and R89 ARE equivalent via {name}!")
    else:
        print(f"\n  R75 and R89 are NOT directly equivalent")
    
    # Spacetime diagrams
    print(f"\n{'='*78}")
    print(f"  SPACETIME DIAGRAMS (single seed)")
    print(f"{'='*78}")
    
    for rn in [75, 89, 110]:
        print(f"\n  ── Rule {rn} (single seed, 40 steps) ──\n")
        rule = make_rule(rn)
        state = single_seed(61)
        history = evolve(rule, state, 40)
        render_spacetime(history, width=61)
    
    # Random initial condition
    print(f"\n{'='*78}")
    print(f"  SPACETIME DIAGRAMS (random initial condition)")
    print(f"{'='*78}")
    
    import random
    random.seed(42)
    for rn in [75, 89, 110, 30]:
        print(f"\n  ── Rule {rn} (random IC, 40 steps) ──\n")
        rule = make_rule(rn)
        state = [random.randint(0, 1) for _ in range(61)]
        history = evolve(rule, state, 40)
        render_spacetime(history, width=61)
    
    # Entropy evolution
    print(f"\n{'='*78}")
    print(f"  ENTROPY EVOLUTION")
    print(f"{'='*78}\n")
    
    for rn in [75, 89, 110, 30, 62]:
        rule = make_rule(rn)
        state = single_seed(101)
        history = evolve(rule, state, 100)
        entropies = [block_entropy(row, 3) for row in history]
        sparkline = entropy_sparkline(entropies, 50)
        print(f"  R{rn:>3d}: {sparkline}")
    
    # Density response
    print(f"\n{'='*78}")
    print(f"  DENSITY RESPONSE")
    print(f"{'='*78}\n")
    
    print(f"  {'Rule':>4s}  {'Init ρ':>7s}  {'Final ρ':>8s}  {'Avg H':>6s}")
    print(f"  {'─'*4}  {'─'*7}  {'─'*8}  {'─'*6}")
    
    for rn in [75, 89, 110, 30, 62]:
        dr = density_response(rn)
        for d in dr:
            print(f"  R{rn:>3d}  {d['initial_density']:>7.1f}  {d['final_density']:>8.3f}  {d['avg_entropy']:>6.3f}")
        print()
    
    # Sensitivity
    print(f"\n{'='*78}")
    print(f"  PERTURBATION SENSITIVITY")
    print(f"{'='*78}\n")
    
    for rn in [75, 89, 110, 30, 62]:
        sens = sensitivity_test(rn)
        print(f"  R{rn:>3d}: mean_damage={sens['mean_damage']:.3f}  "
              f"max={sens['max_damage']:.3f}  min={sens['min_damage']:.3f}")
    
    # The key question: is R75 genuinely computational or just high on all metrics?
    print(f"\n{'='*78}")
    print(f"  THE ANALYSIS")
    print(f"{'='*78}\n")
    
    # R75 = XOR with extra structure
    # Binary: 01001011
    # 111→0, 110→1, 101→0, 100→0, 011→1, 010→0, 001→1, 000→1
    # This is: output = NOT(left XOR center XOR right) XOR center
    # Simplifying: output = left XOR right XOR center XOR 1 = NOT(left XOR center XOR right)
    # Wait, let me check...
    
    table75 = binary_rule(75)
    print(f"  Rule 75 truth table analysis:")
    print(f"  Input  Output  XOR(l,c,r)  Match?")
    for nbr, out in table75.items():
        l, c, r = int(nbr[0]), int(nbr[1]), int(nbr[2])
        xor_val = l ^ c ^ r
        not_xor = 1 - xor_val
        print(f"  {nbr}    {out}       {xor_val}         {'✓' if out == not_xor else '✗'}")
    
    # Check if R75 = NOT(XOR) = XNOR = Rule 150's complement
    print(f"\n  Rule 75 is {'NOT' if all(table75[nbr] == 1 - (int(nbr[0]) ^ int(nbr[1]) ^ int(nbr[2])) for nbr in table75) else 'not'} the XNOR rule")
    
    # Rule 90 is XOR, Rule 150 is XOR with center
    # Check R75 algebraically
    print(f"\n  Algebraic identity:")
    all_match = True
    for nbr, out in table75.items():
        l, c, r = int(nbr[0]), int(nbr[1]), int(nbr[2])
        # R75 = left XNOR right (ignoring center?)
        test1 = 1 - (l ^ r)  # XNOR of left and right
        test2 = 1 - (l ^ c ^ r)  # XNOR of all three
        test3 = (l & c) ^ (c & r) ^ (l ^ r)  # some other combination
        print(f"    {nbr} → {out}  |  XNOR(l,r)={test1}  XNOR(l,c,r)={test2}")
    
    print(f"\n  Rule 89 truth table analysis:")
    table89 = binary_rule(89)
    for nbr, out in table89.items():
        l, c, r = int(nbr[0]), int(nbr[1]), int(nbr[2])
        xor_val = l ^ c ^ r
        print(f"  {nbr}    {out}       XOR={xor_val}")


if __name__ == '__main__':
    main()
