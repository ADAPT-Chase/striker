#!/usr/bin/env python3
"""
R62 Deep Dive — The Surprise Triple-Point Champion

R62 topped the triple-point chart over R110. Is it genuinely computationally
interesting, or is the memory metric fooling us?

This script:
1. Analyzes R62's rule table structure
2. Evolves it from multiple initial conditions
3. Compares its spacetime patterns to R110
4. Checks for glider-like structures
5. Tests sensitivity to initial conditions (a hallmark of computational capability)
"""

import math
import json
from collections import Counter
from automata import make_rule, evolve, single_seed, render_mini, block_entropy, row_entropy

def rule_table_analysis(rule_num):
    """Analyze the structure of a rule's lookup table."""
    rule = make_rule(rule_num)
    bits = format(rule_num, '08b')
    
    # Count: how many neighborhoods map to 1?
    ones = sum(rule.values())
    
    # Symmetry: is the rule left-right symmetric?
    # A neighborhood abc maps to the mirror cba
    mirror_pairs = [('000','000'), ('001','100'), ('010','010'), ('011','110'),
                    ('100','001'), ('101','101'), ('110','011'), ('111','111')]
    symmetric = all(rule[a] == rule[b] for a, b in mirror_pairs)
    
    # Totalistic: does the rule depend only on the SUM of neighbors?
    # Group neighborhoods by sum
    sum_groups = {}
    for n, v in rule.items():
        s = sum(int(c) for c in n)
        if s not in sum_groups:
            sum_groups[s] = set()
        sum_groups[s].add(v)
    totalistic = all(len(vals) == 1 for vals in sum_groups.values())
    
    # Self-complement: is rule(complement(n)) = complement(rule(n))?
    complement_rule = make_rule(255 - rule_num)
    self_complement = all(
        rule[n] == (1 - complement_rule[n]) for n in rule
    )
    # Actually the standard definition: R and its complement give complementary outputs
    # rule_num XOR 255 gives the complement rule
    
    # Additive (XOR-based): does it behave like XOR of inputs?
    # Check if rule(a,b,c) = f(a) XOR f(b) XOR f(c) for some f
    
    return {
        'rule_number': rule_num,
        'binary': bits,
        'lookup': {n: rule[n] for n in sorted(rule.keys())},
        'ones_count': ones,
        'density': ones / 8,
        'symmetric': symmetric,
        'totalistic': totalistic,
        'self_complement': self_complement,
    }


def find_structures(history, min_period=1, max_period=8):
    """Look for repeating structures (still lifes, oscillators, gliders).
    
    A glider shows up as a repeating temporal pattern that shifts spatially.
    A still life is period-1 at fixed position.
    An oscillator is period-N at fixed position.
    """
    width = len(history[0])
    steps = len(history)
    
    structures = {
        'still_lifes': [],
        'oscillators': [],
        'gliders': [],
    }
    
    # Check for period-P repetition at each position
    for pos in range(width):
        column = [history[t][pos] for t in range(steps)]
        
        for period in range(min_period, max_period + 1):
            # Check if the column is periodic with this period (in the settled region)
            start = steps // 3  # skip transient
            is_periodic = True
            for t in range(start, steps - period):
                if column[t] != column[t + period]:
                    is_periodic = False
                    break
            
            if is_periodic and period == 1:
                # Check it's not trivially all-0 or all-1
                if len(set(column[start:])) > 1:
                    pass  # varying but period-1 — could be edge of structure
                # Still life component
                break
            elif is_periodic and period > 1:
                structures['oscillators'].append({
                    'position': pos,
                    'period': period,
                    'pattern': column[start:start+period]
                })
                break
    
    # Look for translated patterns (gliders)
    # Compare blocks of rows: does a pattern at position X, time T
    # reappear at position X+d, time T+p?
    settled_start = steps // 3
    block_h = 5  # height of pattern to match
    
    for t in range(settled_start, steps - block_h * 2):
        for dx in [-3, -2, -1, 1, 2, 3]:  # spatial displacement
            for dt in range(1, block_h + 1):  # temporal period
                if t + dt + block_h > steps:
                    continue
                    
                match = True
                for row_offset in range(block_h):
                    for col_offset in range(-2, 3):  # 5-cell wide block
                        pos1 = 20 + col_offset  # near center-left
                        pos2 = (pos1 + dx) % width
                        t1 = t + row_offset
                        t2 = t + dt + row_offset
                        
                        if t2 >= steps:
                            match = False
                            break
                        if history[t1][pos1] != history[t2][pos2]:
                            match = False
                            break
                    if not match:
                        break
                
                if match:
                    # Verify it's not trivial (all zeros)
                    block = [history[t + r][20 + c] 
                             for r in range(block_h) for c in range(-2, 3)]
                    if sum(block) > 2:  # non-trivial
                        structures['gliders'].append({
                            'time': t,
                            'displacement': dx,
                            'period': dt,
                            'speed': dx / dt
                        })
    
    # Deduplicate gliders by speed
    seen_speeds = set()
    unique_gliders = []
    for g in structures['gliders']:
        speed_key = round(g['speed'], 3)
        if speed_key not in seen_speeds:
            seen_speeds.add(speed_key)
            unique_gliders.append(g)
    structures['gliders'] = unique_gliders
    
    return structures


def sensitivity_test(rule_num, width=101, steps=100, num_perturbations=10):
    """Test sensitivity to initial conditions — Lyapunov-like analysis.
    
    Start from a base state, flip one random bit, measure how the 
    difference (Hamming distance) evolves over time.
    """
    import random
    random.seed(42)
    
    rule = make_rule(rule_num)
    base_state = single_seed(width)
    base_history = evolve(rule, base_state, steps)
    
    divergences = []
    
    for trial in range(num_perturbations):
        # Perturb one bit
        perturbed = base_state[:]
        flip_pos = random.randint(0, width - 1)
        perturbed[flip_pos] = 1 - perturbed[flip_pos]
        
        pert_history = evolve(rule, perturbed, steps)
        
        # Compute Hamming distance at each step
        hamming = []
        for t in range(steps + 1):
            h = sum(1 for a, b in zip(base_history[t], pert_history[t]) if a != b)
            hamming.append(h / width)  # Normalized
        
        divergences.append(hamming)
    
    # Average divergence profile
    avg_divergence = [
        sum(d[t] for d in divergences) / len(divergences)
        for t in range(steps + 1)
    ]
    
    # Key metrics
    final_divergence = avg_divergence[-1]
    max_divergence = max(avg_divergence)
    
    # Rate of initial divergence (first 20 steps)
    early = avg_divergence[:20]
    if early[-1] > early[0] and early[0] < 0.5:
        divergence_rate = (early[-1] - early[0]) / len(early)
    else:
        divergence_rate = 0.0
    
    return {
        'final_divergence': final_divergence,
        'max_divergence': max_divergence,
        'divergence_rate': divergence_rate,
        'profile': avg_divergence,
    }


def density_scan(rule_num, width=101, steps=100, densities=None):
    """Evolve from random initial conditions at different densities.
    
    Computational rules should show different behavior at different densities.
    Simple rules converge to the same attractor regardless.
    """
    import random
    random.seed(42)
    
    if densities is None:
        densities = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    
    rule = make_rule(rule_num)
    results = []
    
    for d in densities:
        state = [1 if random.random() < d else 0 for _ in range(width)]
        history = evolve(rule, state, steps)
        
        # Measure settled entropy
        settled = history[steps//2:]
        row_ents = [row_entropy(r) for r in settled]
        blk_ents = [block_entropy(r) for r in settled]
        
        results.append({
            'density': d,
            'final_row_entropy': row_ents[-1],
            'mean_block_entropy': sum(blk_ents) / len(blk_ents),
            'block_entropy_std': (sum((e - sum(blk_ents)/len(blk_ents))**2 
                                 for e in blk_ents) / len(blk_ents)) ** 0.5,
        })
    
    return results


def main():
    print("=" * 78)
    print("  R62 DEEP DIVE — The Surprise Triple-Point Champion")
    print("=" * 78)
    
    # ─── Rule Table Analysis ───
    print("\n── RULE TABLE STRUCTURE ──\n")
    
    rules_to_compare = [62, 110, 30, 54, 67]
    
    for r in rules_to_compare:
        info = rule_table_analysis(r)
        print(f"  R{r:>3d}  binary={info['binary']}  "
              f"density={info['density']:.3f}  "
              f"sym={'Y' if info['symmetric'] else 'N'}  "
              f"tot={'Y' if info['totalistic'] else 'N'}  "
              f"comp={'Y' if info['self_complement'] else 'N'}")
    
    # Show R62's full lookup table
    r62_info = rule_table_analysis(62)
    print(f"\n  R62 lookup table:")
    print(f"  neighborhood:  000 001 010 011 100 101 110 111")
    print(f"  output:         {'   '.join(str(r62_info['lookup'][n]) for n in sorted(r62_info['lookup']))}")
    
    r110_info = rule_table_analysis(110)
    print(f"\n  R110 lookup table:")
    print(f"  neighborhood:  000 001 010 011 100 101 110 111")
    print(f"  output:         {'   '.join(str(r110_info['lookup'][n]) for n in sorted(r110_info['lookup']))}")
    
    # ─── Visual Evolution ───
    print("\n\n── SPACETIME PATTERNS ──")
    print("(Single seed, 80 cells, 60 steps)\n")
    
    for r in [62, 110]:
        rule = make_rule(r)
        state = single_seed(81)
        history = evolve(rule, state, 60)
        
        print(f"─── Rule {r} ───")
        # Center crop
        center = len(history[0]) // 2
        half = 30
        cropped = [row[center-half:center+half+1] for row in history]
        print(render_mini(cropped))
        print()
    
    # ─── Random initial conditions ───
    print("\n── FROM RANDOM INITIAL CONDITIONS (density=0.5) ──\n")
    
    import random
    random.seed(42)
    
    for r in [62, 110, 30]:
        rule = make_rule(r)
        state = [1 if random.random() < 0.5 else 0 for _ in range(81)]
        history = evolve(rule, state, 60)
        
        print(f"─── Rule {r} ───")
        print(render_mini([row for row in history[-40:]]))
        print()
    
    # ─── Sensitivity Test ───
    print("\n── SENSITIVITY TO PERTURBATION ──")
    print("(Flip 1 bit in initial state, measure divergence)\n")
    
    for r in rules_to_compare:
        sens = sensitivity_test(r)
        sparkline_chars = '▁▂▃▄▅▆▇█'
        profile = sens['profile']
        # Mini sparkline
        step = max(1, len(profile) // 30)
        sampled = profile[::step][:30]
        mn, mx = min(sampled), max(sampled)
        rng = mx - mn if mx > mn else 1
        spark = ''.join(sparkline_chars[min(7, int((v-mn)/rng * 7))] for v in sampled)
        
        print(f"  R{r:>3d}: final={sens['final_divergence']:.4f}  "
              f"max={sens['max_divergence']:.4f}  "
              f"rate={sens['divergence_rate']:.5f}  {spark}")
    
    # ─── Density Response ───
    print("\n\n── DENSITY RESPONSE ──")
    print("(How does settled behavior change with initial density?)\n")
    
    for r in [62, 110, 30, 67]:
        density_results = density_scan(r)
        entropies = [d['mean_block_entropy'] for d in density_results]
        
        # Is the response varied or flat?
        ent_range = max(entropies) - min(entropies)
        ent_mean = sum(entropies) / len(entropies)
        
        # Sparkline
        mn, mx = min(entropies), max(entropies)
        rng = mx - mn if mx > mn else 1
        spark = ''.join('▁▂▃▄▅▆▇█'[min(7, int((v-mn)/rng * 7))] 
                       for v in entropies)
        
        print(f"  R{r:>3d}: mean_blk_ent={ent_mean:.3f}  range={ent_range:.3f}  {spark}")
        print(f"         densities: " + 
              "  ".join(f"{d['density']:.1f}→{d['mean_block_entropy']:.2f}" 
                       for d in density_results[::2]))
    
    # ─── Structure Search ───
    print("\n\n── SEARCHING FOR STRUCTURES (gliders, oscillators) ──\n")
    
    for r in [62, 110]:
        rule = make_rule(r)
        state = single_seed(201)
        history = evolve(rule, state, 200)
        
        structures = find_structures(history)
        n_osc = len(structures['oscillators'])
        n_glide = len(structures['gliders'])
        
        print(f"  R{r:>3d}: oscillators={n_osc}  gliders={n_glide}")
        if structures['gliders']:
            for g in structures['gliders'][:5]:
                print(f"         glider: speed={g['speed']:.2f} (dx={g['displacement']}, period={g['period']})")
        if structures['oscillators']:
            periods = Counter(o['period'] for o in structures['oscillators'])
            print(f"         oscillator periods: {dict(periods)}")
    
    # ─── The Verdict ───
    print("\n" + "=" * 78)
    print("  THE VERDICT ON R62")
    print("=" * 78)
    
    sens_62 = sensitivity_test(62)
    sens_110 = sensitivity_test(110)
    dens_62 = density_scan(62)
    dens_110 = density_scan(110)
    
    ent_range_62 = max(d['mean_block_entropy'] for d in dens_62) - min(d['mean_block_entropy'] for d in dens_62)
    ent_range_110 = max(d['mean_block_entropy'] for d in dens_110) - min(d['mean_block_entropy'] for d in dens_110)
    
    print(f"\n  Sensitivity (final divergence):  R62={sens_62['final_divergence']:.4f}  R110={sens_110['final_divergence']:.4f}")
    print(f"  Density response (entropy range): R62={ent_range_62:.4f}  R110={ent_range_110:.4f}")
    
    # Interpretation
    if sens_62['final_divergence'] < 0.01:
        print("\n  → R62 is NOT sensitive to perturbation. Small changes die out.")
        print("    This is characteristic of Class I/II (ordered), not Class IV (complex).")
    elif sens_62['final_divergence'] > 0.3:
        print("\n  → R62 IS highly sensitive — chaotic. Class III territory.")
    else:
        print("\n  → R62 shows MODERATE sensitivity — interesting. Could be edge-of-chaos.")
    
    if ent_range_62 < 0.1:
        print("  → R62's behavior is INSENSITIVE to initial density — stereotyped.")
    else:
        print("  → R62 responds differently to different densities — diverse dynamics.")
    
    print()
    print("  Conclusion: ", end="")
    
    if (sens_62['final_divergence'] < 0.05 and ent_range_62 < 0.2):
        print("R62 is likely a false positive. High memory score comes from")
        print("  regular/periodic structure, not genuine computational capability.")
        print("  The memory metric is measuring PREDICTABILITY, not information retention.")
        print("  This confirms the Day 011 hypothesis: the memory metric needs fixing")
        print("  for glider-based rules like R110.")
    elif sens_62['final_divergence'] > 0.2:
        print("R62 is genuinely interesting! Shows real sensitivity and complexity.")
        print("  May be an understudied computational rule worth investigating further.")
    else:
        print("R62 is somewhere in between — not trivially periodic, not fully complex.")
        print("  More investigation needed.")


if __name__ == '__main__':
    main()
