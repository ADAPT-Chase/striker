#!/usr/bin/env python3
"""
Test cultural transmission + convention enforcement against baseline.

Runs sim with and without the v4 mechanisms, measures NMI over time.
This is the real test: do these mechanisms stabilize the flickering language?
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random
from collections import defaultdict
from sim import Simulation, NUM_SIGNALS, SIGNAL_NAMES
from info_theory import SignalAnalyzer

def run_experiment(label, ticks=3000, cultural=True, convention=True, 
                   use_predator=False, use_seasons=True, seed=42):
    """Run sim and collect NMI metrics over time."""
    random.seed(seed)
    
    sim = Simulation(num_agents=50, use_predator=use_predator, use_seasons=use_seasons)
    analyzer = SignalAnalyzer()
    
    # Monkey-patch to disable mechanisms for baseline comparison
    if not cultural:
        sim._cultural_transmission = lambda: None
    if not convention:
        sim._convention_enforcement = lambda: None
    
    # Collect windowed NMI every 100 ticks
    results = {
        'label': label,
        'nmi_over_time': [],
        'window_nmi_over_time': [],
        'pop_over_time': [],
        'signal_specificity': [],
        'phase_transitions': 0,
        'max_sustained_nmi': 0,
        'sustained_above_threshold': 0,  # ticks with windowed NMI > 0.1
    }
    
    window_analyzer = SignalAnalyzer()
    window_start = 0
    window_size = 200
    
    prev_nmi = 0
    
    for t in range(ticks):
        sim.step()
        
        # Track all signals emitted this tick
        for a in sim.agents:
            if a.current_signal >= 0 and a.last_context:
                analyzer.observe(a.current_signal, a.last_context)
                window_analyzer.observe(a.current_signal, a.last_context)
        
        # Every 100 ticks, record metrics
        if t > 0 and t % 100 == 0:
            cum_metrics = analyzer.get_cumulative_metrics()
            results['nmi_over_time'].append((t, cum_metrics['nmi']))
            results['pop_over_time'].append((t, len(sim.agents)))
            
            # Windowed NMI
            w_metrics = window_analyzer.get_cumulative_metrics()
            w_nmi = w_metrics['nmi']
            results['window_nmi_over_time'].append((t, w_nmi))
            
            if w_nmi > 0.1:
                results['sustained_above_threshold'] += 100
            
            # Detect phase transitions (NMI jumps)
            if w_nmi > prev_nmi + 0.05 and w_nmi > 0.1:
                results['phase_transitions'] += 1
            
            results['max_sustained_nmi'] = max(results['max_sustained_nmi'], w_nmi)
            prev_nmi = w_nmi
            
            # Signal specificity from the analyzer
            spec = window_analyzer.signal_specificity()
            if spec:
                avg_spec = sum(v['specificity'] for v in spec.values()) / len(spec)
                results['signal_specificity'].append((t, avg_spec))
            
            # Reset window
            if t - window_start >= window_size:
                window_analyzer = SignalAnalyzer()
                window_start = t
    
    # Final cumulative
    final = analyzer.get_cumulative_metrics()
    results['final_nmi'] = final['nmi']
    results['final_mi'] = final['mutual_info']
    results['total_obs'] = final['total_obs']
    
    return results


def print_results(results_list):
    """Print comparative results."""
    print("\n" + "="*70)
    print("EMERGENCE SIM v4 — CULTURAL TRANSMISSION EXPERIMENT")
    print("="*70)
    
    for r in results_list:
        print(f"\n{'─'*50}")
        print(f"  {r['label']}")
        print(f"{'─'*50}")
        print(f"  Final cumulative NMI:     {r['final_nmi']:.4f}")
        print(f"  Final mutual info:        {r['final_mi']:.4f} bits")
        print(f"  Max windowed NMI:         {r['max_sustained_nmi']:.4f}")
        print(f"  Phase transitions:        {r['phase_transitions']}")
        print(f"  Ticks above NMI>0.1:      {r['sustained_above_threshold']}")
        print(f"  Total observations:       {r['total_obs']}")
        
        # NMI trajectory
        print(f"\n  NMI over time (windowed):")
        for t, nmi in r['window_nmi_over_time']:
            bar = '█' * int(nmi * 100)
            marker = ' ◀ LANGUAGE' if nmi > 0.15 else ''
            print(f"    t={t:>4}: {nmi:.3f} {bar}{marker}")
        
        # Signal specificity
        if r['signal_specificity']:
            print(f"\n  Signal specificity over time:")
            for t, spec in r['signal_specificity'][-5:]:
                bar = '█' * int(spec * 20)
                print(f"    t={t:>4}: {spec:.2f} {bar}")
    
    # Comparison
    if len(results_list) >= 2:
        print(f"\n{'='*50}")
        print("COMPARISON")
        print(f"{'='*50}")
        base = results_list[0]
        cult = results_list[1]
        nmi_ratio = cult['final_nmi'] / max(base['final_nmi'], 0.0001)
        sustain_ratio = cult['sustained_above_threshold'] / max(base['sustained_above_threshold'], 1)
        print(f"  NMI improvement:        {nmi_ratio:.1f}x")
        print(f"  Sustained NMI improvement: {sustain_ratio:.1f}x")
        print(f"  Phase transitions: {base['phase_transitions']} → {cult['phase_transitions']}")
        
        verdict = "YES" if cult['final_nmi'] > base['final_nmi'] * 1.5 else "MARGINAL" if cult['final_nmi'] > base['final_nmi'] * 1.1 else "NO"
        print(f"\n  DOES CULTURAL TRANSMISSION HELP? → {verdict}")


if __name__ == '__main__':
    print("Running baseline (no cultural transmission, no convention enforcement)...")
    baseline = run_experiment(
        "BASELINE (v3 — individual learning only)", 
        cultural=False, convention=False, ticks=3000, seed=42
    )
    
    print("Running v4 (cultural transmission + convention enforcement)...")
    v4 = run_experiment(
        "V4 (cultural transmission + convention pressure)", 
        cultural=True, convention=True, ticks=3000, seed=42
    )
    
    print("Running v4 with predator pressure...")
    v4_pred = run_experiment(
        "V4 + PREDATOR (cultural + convention + predation)", 
        cultural=True, convention=True, use_predator=True, ticks=3000, seed=42
    )
    
    print_results([baseline, v4, v4_pred])
