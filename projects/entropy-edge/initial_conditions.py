#!/usr/bin/env python3
"""
Initial condition robustness for entropy-edge rules.

Question:
Does a rule only look computational because of the classic single-center seed,
or do its information metrics survive different starting conditions?

We compare a few famous rules across multiple seed families:
  - single: single live cell in center
  - pair: two adjacent live cells
  - random_sparse: Bernoulli(p=0.10)
  - random_balanced: Bernoulli(p=0.50)
  - random_dense: Bernoulli(p=0.90)
  - stripe: alternating 0101...

For each rule and seed family, we run several trials and measure:
  spatial entropy, temporal MI, AIS, computation score.
"""

import random
from collections import defaultdict

from automata import evolve, make_rule, single_seed
from temporal import temporal_mi_profile, active_information_storage, block_entropy


def pair_seed(width: int) -> list[int]:
    state = [0] * width
    center = width // 2
    state[center] = 1
    state[(center + 1) % width] = 1
    return state


def random_seed(width: int, p: float) -> list[int]:
    return [1 if random.random() < p else 0 for _ in range(width)]


def stripe_seed(width: int) -> list[int]:
    return [i % 2 for i in range(width)]


SEED_FAMILIES = {
    'single': lambda width: single_seed(width),
    'pair': pair_seed,
    'random_sparse': lambda width: random_seed(width, 0.10),
    'random_balanced': lambda width: random_seed(width, 0.50),
    'random_dense': lambda width: random_seed(width, 0.90),
    'stripe': stripe_seed,
}


def summarize(values: list[float]) -> tuple[float, float]:
    mean = sum(values) / len(values) if values else 0.0
    var = sum((v - mean) ** 2 for v in values) / len(values) if values else 0.0
    return mean, var ** 0.5


def analyze_rule_with_seed(rule_num: int, initial_state: list[int], steps: int = 150, block_size: int = 3) -> dict:
    rule = make_rule(rule_num)
    history = evolve(rule, initial_state, steps)

    blk_entropies = [block_entropy(row, block_size) for row in history]
    settled_blk = blk_entropies[len(blk_entropies) // 4:]
    spatial_entropy = sum(settled_blk) / len(settled_blk) if settled_blk else 0.0

    tmi = temporal_mi_profile(history, block_size)
    ais_values = active_information_storage(history, block_size)
    settled_ais = ais_values[len(ais_values) // 4:]
    ais = sum(settled_ais) / len(settled_ais) if settled_ais else 0.0

    score = 0.0 if spatial_entropy < 0.05 else tmi['mean'] * spatial_entropy * (1 + ais)

    return {
        'spatial_entropy': spatial_entropy,
        'temporal_mi': tmi['mean'],
        'ais': ais,
        'score': score,
    }


def run_experiment(width: int = 101, steps: int = 150, trials: int = 5) -> dict:
    rules = {
        110: 'Turing-complete edge',
        30: 'chaotic PRNG',
        90: 'Sierpinski fractal',
        54: 'complex chaos',
        184: 'traffic flow',
        0: 'dead rule',
    }

    results = defaultdict(dict)

    for rule_num in rules:
        for family_name, seed_fn in SEED_FAMILIES.items():
            metrics = defaultdict(list)
            family_trials = trials if 'random' in family_name else 1

            for trial in range(family_trials):
                random.seed(f"rule={rule_num}|family={family_name}|trial={trial}")
                initial_state = seed_fn(width)
                analysis = analyze_rule_with_seed(rule_num, initial_state, steps=steps)
                for key, value in analysis.items():
                    metrics[key].append(value)

            results[rule_num][family_name] = {
                key: {
                    'mean': summarize(values)[0],
                    'std': summarize(values)[1],
                }
                for key, values in metrics.items()
            }

    return {'rules': rules, 'results': results, 'width': width, 'steps': steps, 'trials': trials}


def render_report(payload: dict) -> str:
    rules = payload['rules']
    results = payload['results']
    lines = []
    lines.append('=' * 78)
    lines.append('  INITIAL CONDITION ROBUSTNESS — Does computation survive different seeds?')
    lines.append('=' * 78)
    lines.append('')

    for rule_num, label in rules.items():
        lines.append(f'Rule {rule_num} — {label}')
        lines.append('  Seed family       Score        Spatial H     TMI           AIS')
        lines.append('  ─────────────────────────────────────────────────────────────────')
        for family_name, metrics in results[rule_num].items():
            score = metrics['score']
            spatial = metrics['spatial_entropy']
            tmi = metrics['temporal_mi']
            ais = metrics['ais']
            lines.append(
                f"  {family_name:14s} "
                f"{score['mean']:6.3f}±{score['std']:<5.3f}   "
                f"{spatial['mean']:6.3f}±{spatial['std']:<5.3f}   "
                f"{tmi['mean']:6.3f}±{tmi['std']:<5.3f}   "
                f"{ais['mean']:6.3f}±{ais['std']:<5.3f}"
            )
        lines.append('')

    lines.append('Key pattern:')
    lines.append('  - Rules that only look rich under the single-seed ritual are brittle.')
    lines.append('  - Rules that stay high across sparse/dense/random starts are genuinely robust.')
    return '\n'.join(lines)


if __name__ == '__main__':
    payload = run_experiment()
    print(render_report(payload))
