#!/usr/bin/env python3
"""
🧪 PID SYNERGY EXPERIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━

Run the emergence sim under different conditions and measure SYNERGY
using PID decomposition. This answers the critical question:

Is the transformation we measured REAL (genuine information creation
from combining multiple sources) or ARTIFACT (distributional drift
that looks like transformation but isn't computation)?

Conditions:
  1. BASELINE — standard linear sim
  2. CONDITIONAL_CTX — multiplicative gating (our best transformation condition)
  3. SCRAMBLED — random weight noise (high "transformation" from the old metric)

If CONDITIONAL_CTX shows higher SYNERGY than baseline and scrambled,
the transformation bottleneck is real and conditional context genuinely
breaks it. If scrambled shows equal or higher synergy, our old metric
was fooled by noise.

Striker, April 2026
"""

import sys
import json
import random
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent))

import sim as emergence_sim
from pid_synergy import PIDSynergyAnalyzer
from triple_point_agents import TriplePointAnalyzer
from nonlinear_experiment import conditional_context_intervention


def scramble_weights(sim):
    """Randomize all agent signal weights — creates noise diversity."""
    for agent in sim.agents:
        for s in range(emergence_sim.NUM_SIGNALS):
            for ctx in ['food_near', 'danger_near', 'friends_near', 'alone']:
                agent.signal_weights[s][ctx] = random.uniform(0, 1)


def run_condition(name, ticks=2000, num_agents=60, seed=42,
                  intervention_fn=None, scramble=False):
    """Run one condition with both triple-point and PID analyzers."""
    random.seed(seed)
    
    sim = emergence_sim.Simulation(num_agents=num_agents)
    triple_analyzer = TriplePointAnalyzer()
    pid_analyzer = PIDSynergyAnalyzer(cell_size=20.0)
    
    if scramble:
        scramble_weights(sim)
    
    for t in range(ticks):
        sim.step()
        
        if intervention_fn:
            intervention_fn(sim)
        
        # Scramble weights periodically to maintain noise
        if scramble and t % 200 == 0 and t > 0:
            scramble_weights(sim)
        
        triple_analyzer.record_tick(sim.agents)
        pid_analyzer.record_tick(sim.agents)
        
        if t % 500 == 0:
            print(f"  [{name}] Tick {t}/{ticks} — {len(sim.agents)} agents")
    
    triple_results = triple_analyzer.analyze()
    pid_results = pid_analyzer.analyze()
    
    return {
        'name': name,
        'triple': triple_results.get('summary', {}),
        'pid': pid_results.get('summary', {}),
        'pid_windows': pid_results.get('windows', []),
    }


def main():
    print("=" * 70)
    print("🧪 PID SYNERGY EXPERIMENT")
    print("   Question: Is transformation REAL or ARTIFACT?")
    print("=" * 70)
    
    conditions = [
        ("BASELINE", {'intervention_fn': None, 'scramble': False}),
        ("CONDITIONAL_CTX", {'intervention_fn': conditional_context_intervention, 'scramble': False}),
        ("SCRAMBLED", {'intervention_fn': None, 'scramble': True}),
    ]
    
    all_results = []
    
    for name, kwargs in conditions:
        print(f"\n{'─' * 60}")
        print(f"  Running: {name}")
        print(f"{'─' * 60}")
        
        # Average over 3 seeds
        seed_results = []
        for seed_offset in range(3):
            result = run_condition(name, seed=42 + seed_offset, **kwargs)
            seed_results.append(result)
        
        # Average PID metrics across seeds
        pid_summaries = [r['pid'] for r in seed_results if r['pid']]
        triple_summaries = [r['triple'] for r in seed_results if r['triple']]
        
        avg_result = {
            'name': name,
            'seeds': len(seed_results),
        }
        
        if pid_summaries:
            for key in ['mean_synergy', 'mean_redundancy', 'mean_synergy_ratio', 'max_synergy']:
                vals = [p.get(key, 0) for p in pid_summaries]
                avg_result[f'pid_{key}'] = round(sum(vals) / len(vals), 4) if vals else 0
            avg_result['pid_synergy_trend'] = round(
                sum(p.get('synergy_trend', 0) for p in pid_summaries) / len(pid_summaries), 6)
        
        if triple_summaries:
            for key in ['mean_memory', 'mean_transport', 'mean_transformation', 'mean_triple']:
                vals = [t.get(key, 0) for t in triple_summaries]
                avg_result[f'triple_{key}'] = round(sum(vals) / len(vals), 4) if vals else 0
        
        all_results.append(avg_result)
        
        print(f"\n  Results for {name}:")
        if pid_summaries:
            print(f"    PID Synergy:     {avg_result.get('pid_mean_synergy', '?')}")
            print(f"    PID Redundancy:  {avg_result.get('pid_mean_redundancy', '?')}")
            print(f"    Synergy Ratio:   {avg_result.get('pid_mean_synergy_ratio', '?')}")
            print(f"    Synergy Trend:   {avg_result.get('pid_synergy_trend', '?')}")
        if triple_summaries:
            print(f"    Triple Memory:   {avg_result.get('triple_mean_memory', '?')}")
            print(f"    Triple Transport:{avg_result.get('triple_mean_transport', '?')}")
            print(f"    Triple Transform:{avg_result.get('triple_mean_transformation', '?')}")
            print(f"    Triple Score:    {avg_result.get('triple_mean_triple', '?')}")
    
    # Summary comparison
    print(f"\n\n{'=' * 70}")
    print("COMPARISON: PID SYNERGY vs OLD TRANSFORMATION METRIC")
    print("=" * 70)
    
    headers = ['Condition', 'PID_Syn', 'PID_Red', 'Syn_Ratio', 'Old_Trans', 'Triple']
    print(f"{'Condition':<18} {'PID_Syn':>8} {'PID_Red':>8} {'Syn_Ratio':>10} {'Old_Trans':>10} {'Triple':>8}")
    print("─" * 70)
    
    for r in all_results:
        print(f"{r['name']:<18} "
              f"{r.get('pid_mean_synergy', 0):>8.4f} "
              f"{r.get('pid_mean_redundancy', 0):>8.4f} "
              f"{r.get('pid_mean_synergy_ratio', 0):>10.4f} "
              f"{r.get('triple_mean_transformation', 0):>10.4f} "
              f"{r.get('triple_mean_triple', 0):>8.4f}")
    
    # The verdict
    baseline = next(r for r in all_results if r['name'] == 'BASELINE')
    conditional = next(r for r in all_results if r['name'] == 'CONDITIONAL_CTX')
    scrambled = next(r for r in all_results if r['name'] == 'SCRAMBLED')
    
    b_syn = baseline.get('pid_mean_synergy_ratio', 0)
    c_syn = conditional.get('pid_mean_synergy_ratio', 0)
    s_syn = scrambled.get('pid_mean_synergy_ratio', 0)
    
    print(f"\n\n📊 VERDICT:")
    print(f"─" * 50)
    
    if c_syn > b_syn and c_syn > s_syn:
        print(f"  ✅ CONDITIONAL CONTEXT shows REAL synergy")
        print(f"     Conditional: {c_syn:.4f} > Baseline: {b_syn:.4f} > Scrambled: {s_syn:.4f}")
        print(f"     Transformation is GENUINE computation, not artifact.")
        verdict = "REAL"
    elif s_syn >= c_syn:
        print(f"  ⚠️  SCRAMBLED matches or beats CONDITIONAL")
        print(f"     Scrambled: {s_syn:.4f} >= Conditional: {c_syn:.4f}")
        print(f"     Old metric was detecting NOISE, not computation.")
        verdict = "ARTIFACT"
    elif c_syn > b_syn:
        print(f"  🔶 Conditional > Baseline but need more investigation")
        print(f"     Conditional: {c_syn:.4f} > Baseline: {b_syn:.4f}")
        verdict = "PARTIAL"
    else:
        print(f"  ❌ No synergy improvement detected")
        verdict = "NONE"
    
    # Save results
    output = {
        'experiment': 'pid_synergy_validation',
        'question': 'Is transformation metric measuring real synergy or distributional drift?',
        'verdict': verdict,
        'conditions': all_results,
    }
    
    with open('pid_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nResults saved to pid_results.json")
    return output


if __name__ == '__main__':
    main()
