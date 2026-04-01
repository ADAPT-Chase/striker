#!/usr/bin/env python3
"""
Damage spreading / perturbation analysis for elementary cellular automata.

Information metrics alone were too flattering to chaos-heavy rules. This script asks
another question: if I flip one bit in the initial state, how far does the disturbance spread?

Interpretation:
  - dead/frozen rules: perturbation dies out
  - chaotic rules: perturbation saturates quickly across the lattice
  - edge/computational rules: perturbation persists and spreads, but submaximally
"""

from automata import make_rule, evolve, single_seed, entropy_sparkline


def flip_center_bit(state: list[int]) -> list[int]:
    new_state = state[:]
    center = len(state) // 2
    new_state[center] = 1 - new_state[center]
    return new_state


def hamming_distance(a: list[int], b: list[int]) -> int:
    return sum(x != y for x, y in zip(a, b))


def damage_profile(rule_num: int, width: int = 121, steps: int = 120) -> dict:
    base = single_seed(width)
    perturbed = flip_center_bit(base)

    history_a = evolve(make_rule(rule_num), base, steps)
    history_b = evolve(make_rule(rule_num), perturbed, steps)

    distances = [hamming_distance(row_a, row_b) / width for row_a, row_b in zip(history_a, history_b)]
    settled = distances[len(distances) // 4:]
    mean_damage = sum(settled) / len(settled) if settled else 0.0
    peak_damage = max(distances) if distances else 0.0
    final_damage = distances[-1] if distances else 0.0
    spread_steps = sum(1 for d in distances if d > 0.10)

    if mean_damage < 0.02:
        regime = 'frozen'
    elif mean_damage < 0.20:
        regime = 'edge-like'
    else:
        regime = 'chaotic'

    return {
        'rule': rule_num,
        'mean_damage': mean_damage,
        'peak_damage': peak_damage,
        'final_damage': final_damage,
        'spread_steps': spread_steps,
        'trajectory': distances,
        'regime': regime,
    }


def main():
    rules = {
        0: 'death',
        30: 'chaotic PRNG',
        54: 'complex chaos',
        90: 'Sierpinski fractal',
        110: 'Turing-complete edge',
        184: 'traffic flow',
    }

    print('=' * 78)
    print('  PERTURBATION ANALYSIS — How a one-bit difference spreads through the rule')
    print('=' * 78)
    print()
    print('  Rule  Label                 Mean    Peak    Final   >10% steps  Regime      Damage sparkline')
    print('  ──────────────────────────────────────────────────────────────────────────────────────────────')

    for rule_num, label in rules.items():
        result = damage_profile(rule_num)
        spark = entropy_sparkline(result['trajectory'], width=36)
        print(
            f"  {rule_num:>4d}  {label:20s} "
            f"{result['mean_damage']:.3f}   {result['peak_damage']:.3f}   {result['final_damage']:.3f}"
            f"   {result['spread_steps']:>4d}       {result['regime']:10s}  {spark}"
        )

    print()
    print('Reading guide:')
    print('  frozen   = disturbance collapses')
    print('  edge-like = disturbance survives without saturating the whole lattice')
    print('  chaotic  = disturbance rapidly infects a large fraction of cells')


if __name__ == '__main__':
    main()
