#!/usr/bin/env python3
"""
🔺 TRIPLE POINT V2: PID SYNERGY AS TRANSFORMATION AXIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V1 used distributional drift for transformation. PID showed that was noise.
V2 uses PID synergy: genuine multi-source information integration.

Also adds criticality sweep — tuning order/chaos balance to find the
phase transition where computation peaks.

Triple Point = Memory × Transport × Synergy (geometric mean)
  Memory    = temporal MI of population signal states
  Transport = spatial MI between neighboring clusters  
  Synergy   = PID synergy: info requiring BOTH neighbor clusters to predict target

Striker — April 2026
"""

import math
import sys
import json
import time
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from itertools import combinations

sys.path.insert(0, str(Path(__file__).parent))

from pid_synergy import (
    pid_decompose, cluster_dominant_signal, spatial_clusters,
    neighboring_cells, entropy, mutual_information
)


def population_signal_state(agents, num_signals=4):
    """Encode collective signal state as discrete tuple."""
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    ctx_signal = defaultdict(lambda: defaultdict(int))

    for a in agents:
        if hasattr(a, 'current_signal') and a.current_signal is not None and a.current_signal >= 0:
            ctx = getattr(a, 'last_context', 'alone') or 'alone'
            ctx_signal[ctx][a.current_signal] += 1

    state = []
    for ctx in contexts:
        if ctx_signal[ctx]:
            dominant = max(ctx_signal[ctx], key=ctx_signal[ctx].get)
            state.append(dominant)
        else:
            state.append(-1)
    return tuple(state)


class TriplePointV2:
    """
    Triple Point with PID Synergy as the transformation axis.
    
    This is the honest version. Synergy can't be faked by noise.
    """

    def __init__(self, num_signals=4, cell_size=20.0, window=100, stride=50):
        self.num_signals = num_signals
        self.cell_size = cell_size
        self.window = window
        self.stride = stride

        # Time series
        self.pop_states = []
        self.cluster_history = defaultdict(list)  # cell_id -> [dominant_signal]
        self.cluster_counts = defaultdict(list)   # cell_id -> [signal_count_tuples]
        self.tick_count = 0

    def record_tick(self, agents):
        """Record one tick of agent state."""
        self.tick_count += 1
        self.pop_states.append(population_signal_state(agents, self.num_signals))

        clusters = spatial_clusters(agents, self.cell_size)
        active_cells = set()

        for cell_id, cell_agents in clusters.items():
            dom = cluster_dominant_signal(cell_agents, self.num_signals)
            self.cluster_history[cell_id].append(dom)
            
            # Also store counts for transport metric
            counts = [0] * self.num_signals
            for a in cell_agents:
                if hasattr(a, 'current_signal') and a.current_signal is not None and a.current_signal >= 0:
                    counts[a.current_signal] += 1
            self.cluster_counts[cell_id].append(tuple(counts))
            active_cells.add(cell_id)

        for cell_id in list(self.cluster_history.keys()):
            if cell_id not in active_cells:
                self.cluster_history[cell_id].append(-1)
                self.cluster_counts[cell_id].append(tuple([0] * self.num_signals))

    def analyze(self) -> Dict:
        """Run full triple-point analysis with PID synergy."""
        if self.tick_count < self.window + 1:
            return {"error": f"Need {self.window+1}+ ticks, have {self.tick_count}"}

        # Find cells with enough data
        active_cells = [c for c, hist in self.cluster_history.items()
                       if len(hist) >= self.window 
                       and sum(1 for h in hist if h >= 0) > self.window * 0.3]

        if len(active_cells) < 3:
            return {"error": "Too few active clusters", "cells": len(active_cells)}

        # Build neighbor map
        cell_set = set(active_cells)
        neighbor_map = {}
        for cell in active_cells:
            nbrs = [n for n in neighboring_cells(cell) if n in cell_set]
            if len(nbrs) >= 2:
                neighbor_map[cell] = nbrs

        results = {
            "ticks_recorded": self.tick_count,
            "n_active_cells": len(active_cells),
            "n_triplet_cells": len(neighbor_map),
            "windows": [],
        }

        # Sliding window analysis
        for start in range(0, self.tick_count - self.window, self.stride):
            end = start + self.window
            window_states = self.pop_states[start:end]

            mem = self._measure_memory(window_states)
            trans = self._measure_transport(start, end, active_cells)
            synergy_result = self._measure_synergy(start, end, neighbor_map)
            syn = synergy_result['mean_synergy']

            # Geometric mean — all three must be non-trivial
            triple = (mem * trans * syn) ** (1/3) if min(mem, trans, syn) > 0 else 0.0

            results["windows"].append({
                "start": start,
                "memory": round(mem, 4),
                "transport": round(trans, 4),
                "synergy": round(syn, 4),
                "synergy_ratio": round(synergy_result.get('mean_ratio', 0), 4),
                "redundancy": round(synergy_result.get('mean_redundancy', 0), 4),
                "n_triplets": synergy_result.get('n_triplets', 0),
                "triple_point": round(triple, 4),
            })

        if results["windows"]:
            w = results["windows"]
            results["summary"] = {
                "mean_memory": round(sum(x["memory"] for x in w) / len(w), 4),
                "mean_transport": round(sum(x["transport"] for x in w) / len(w), 4),
                "mean_synergy": round(sum(x["synergy"] for x in w) / len(w), 4),
                "mean_synergy_ratio": round(sum(x["synergy_ratio"] for x in w) / len(w), 4),
                "mean_redundancy": round(sum(x["redundancy"] for x in w) / len(w), 4),
                "mean_triple": round(sum(x["triple_point"] for x in w) / len(w), 4),
                "max_triple": round(max(x["triple_point"] for x in w), 4),
                "computing_windows": sum(1 for x in w if x["triple_point"] > 0.1),
                "total_windows": len(w),
            }

        return results

    def _measure_memory(self, states, lag=1) -> float:
        """Temporal MI between population states at t and t+lag."""
        if len(states) < lag + 10:
            return 0.0
        seq_a = states[:-lag]
        seq_b = states[lag:]
        mi = mutual_information(seq_a, seq_b)
        h = entropy(seq_a)
        if h == 0:
            return 0.0
        return min(1.0, mi / h)

    def _measure_transport(self, start, end, active_cells) -> float:
        """Spatial MI between neighboring clusters using count vectors."""
        mi_values = []
        cell_set = set(active_cells)

        for t in range(start, end):
            for cell in active_cells:
                for nbr in neighboring_cells(cell):
                    if nbr in cell_set:
                        if t < len(self.cluster_counts.get(cell, [])) and t < len(self.cluster_counts.get(nbr, [])):
                            sa = self.cluster_counts[cell][t]
                            sb = self.cluster_counts[nbr][t]
                            sum_a = sum(sa)
                            sum_b = sum(sb)
                            if sum_a > 0 and sum_b > 0:
                                # Cosine similarity as transport proxy
                                dot = sum(a*b for a, b in zip(sa, sb))
                                mag_a = math.sqrt(sum(a*a for a in sa))
                                mag_b = math.sqrt(sum(b*b for b in sb))
                                if mag_a > 0 and mag_b > 0:
                                    mi_values.append(dot / (mag_a * mag_b))

        if not mi_values:
            return 0.0
        return sum(mi_values) / len(mi_values)

    def _measure_synergy(self, start, end, neighbor_map) -> Dict:
        """
        PID synergy between neighboring cluster triplets.
        
        For each target cell C with neighbors A, B:
          Source1 = A's dominant signal at time t
          Source2 = B's dominant signal at time t
          Target  = C's dominant signal at time t+1
        
        Synergy = info requiring BOTH sources. This is real computation.
        """
        all_synergies = []
        all_redundancies = []
        all_ratios = []

        for target_cell, neighbors in neighbor_map.items():
            for a_cell, b_cell in combinations(neighbors[:5], 2):
                # Build aligned sequences
                s1 = self.cluster_history[a_cell][start:end]
                s2 = self.cluster_history[b_cell][start:end]
                target = self.cluster_history[target_cell][start+1:end+1]

                if len(target) < 20:
                    continue

                # Filter invalid ticks
                valid = [(s1[i], s2[i], target[i]) for i in range(min(len(s1), len(s2), len(target)))
                         if s1[i] >= 0 and s2[i] >= 0 and target[i] >= 0]

                if len(valid) < 20:
                    continue

                s1_c = [v[0] for v in valid]
                s2_c = [v[1] for v in valid]
                t_c = [v[2] for v in valid]

                pid = pid_decompose(t_c, s1_c, s2_c)

                if pid['total_mi'] > 0.005:
                    all_synergies.append(pid['synergy'])
                    all_redundancies.append(pid['redundancy'])
                    all_ratios.append(pid['synergy_ratio'])

        if not all_synergies:
            return {'mean_synergy': 0.0, 'mean_redundancy': 0.0, 'mean_ratio': 0.0, 'n_triplets': 0}

        return {
            'mean_synergy': sum(all_synergies) / len(all_synergies),
            'mean_redundancy': sum(all_redundancies) / len(all_redundancies),
            'mean_ratio': sum(all_ratios) / len(all_ratios),
            'n_triplets': len(all_synergies),
        }


def run_single(ticks=2000, num_agents=60, cultural_rate=0.15,
               convention_strength=0.05, blend_rate=0.3,
               use_cultural=True, use_convention=True, 
               use_seasons=False, use_predator=False,
               label="experiment") -> Dict:
    """Run one sim config and return triple-point results."""
    import sim as emergence_sim

    s = emergence_sim.Simulation(
        num_agents=num_agents,
        use_seasons=use_seasons,
        use_predator=use_predator,
    )

    if hasattr(s, 'cultural_transmission'):
        s.cultural_transmission = use_cultural
    if hasattr(s, 'convention_enforcement'):
        s.convention_enforcement = use_convention
    if hasattr(s, 'cultural_rate'):
        s.cultural_rate = cultural_rate
    if hasattr(s, 'convention_strength'):
        s.convention_strength = convention_strength
    if hasattr(s, 'blend_rate'):
        s.blend_rate = blend_rate

    analyzer = TriplePointV2()

    for tick in range(ticks):
        s.step()
        analyzer.record_tick(s.agents)

    results = analyzer.analyze()
    results['config'] = {
        'label': label,
        'ticks': ticks,
        'num_agents': num_agents,
        'cultural_rate': cultural_rate,
        'convention_strength': convention_strength,
        'blend_rate': blend_rate,
        'use_cultural': use_cultural,
        'use_convention': use_convention,
    }

    return results


def criticality_sweep():
    """
    Sweep cultural_rate and convention_strength to find the edge of chaos.
    
    Hypothesis: computation peaks at a critical point between order and chaos.
    - Too much convention → ordered, low synergy (copying dominates)
    - Too little convention → chaotic, low memory (noise dominates)
    - Sweet spot → high synergy AND memory simultaneously = computation
    """
    print("🔺 CRITICALITY SWEEP: Finding the Edge of Chaos")
    print("=" * 70)
    
    # Sweep parameters
    cultural_rates = [0.0, 0.05, 0.10, 0.15, 0.25, 0.40]
    convention_strengths = [0.0, 0.02, 0.05, 0.10, 0.20]
    
    results = []
    total = len(cultural_rates) * len(convention_strengths)
    done = 0
    
    for cr in cultural_rates:
        for cs in convention_strengths:
            done += 1
            label = f"cr={cr:.2f}_cs={cs:.2f}"
            print(f"\n[{done}/{total}] {label}")
            
            t0 = time.time()
            r = run_single(
                ticks=1500,  # Shorter for sweep
                num_agents=50,
                cultural_rate=cr,
                convention_strength=cs,
                use_cultural=(cr > 0),
                use_convention=(cs > 0),
                label=label,
            )
            elapsed = time.time() - t0
            
            if "summary" in r:
                s = r["summary"]
                print(f"  Memory={s['mean_memory']:.3f}  Transport={s['mean_transport']:.3f}  "
                      f"Synergy={s['mean_synergy']:.4f}  Triple={s['mean_triple']:.4f}  "
                      f"SynRatio={s['mean_synergy_ratio']:.3f}  ({elapsed:.1f}s)")
                
                results.append({
                    'cultural_rate': cr,
                    'convention_strength': cs,
                    'label': label,
                    **s,
                    'elapsed': round(elapsed, 1),
                })
            else:
                print(f"  ERROR: {r.get('error', 'unknown')}")
                results.append({
                    'cultural_rate': cr,
                    'convention_strength': cs,
                    'label': label,
                    'error': r.get('error', 'unknown'),
                })
    
    # Find the peak
    valid = [r for r in results if 'mean_triple' in r]
    if valid:
        best = max(valid, key=lambda x: x['mean_triple'])
        worst = min(valid, key=lambda x: x['mean_triple'])
        best_syn = max(valid, key=lambda x: x['mean_synergy'])
        
        print("\n" + "=" * 70)
        print("🔺 CRITICALITY SWEEP RESULTS")
        print("=" * 70)
        print(f"\n  BEST TRIPLE POINT: {best['label']}")
        print(f"    Triple={best['mean_triple']:.4f}  Mem={best['mean_memory']:.3f}  "
              f"Trans={best['mean_transport']:.3f}  Syn={best['mean_synergy']:.4f}")
        
        print(f"\n  HIGHEST SYNERGY: {best_syn['label']}")
        print(f"    Synergy={best_syn['mean_synergy']:.4f}  SynRatio={best_syn['mean_synergy_ratio']:.3f}")
        
        print(f"\n  LOWEST TRIPLE: {worst['label']}")
        print(f"    Triple={worst['mean_triple']:.4f}")
        
        # Phase diagram
        print(f"\n  PHASE DIAGRAM (Triple Point):")
        print(f"  {'':10s}", end="")
        for cs in convention_strengths:
            print(f"  cs={cs:.2f}", end="")
        print()
        
        for cr in cultural_rates:
            print(f"  cr={cr:.2f}", end="")
            for cs in convention_strengths:
                match = [r for r in valid if r['cultural_rate'] == cr and r['convention_strength'] == cs]
                if match:
                    tp = match[0]['mean_triple']
                    # Visual intensity
                    if tp > 0.3:
                        marker = "███"
                    elif tp > 0.2:
                        marker = "▓▓▓"
                    elif tp > 0.1:
                        marker = "▒▒▒"
                    elif tp > 0.05:
                        marker = "░░░"
                    else:
                        marker = "   "
                    print(f"  {marker}{tp:.2f}", end="")
                else:
                    print(f"  {'ERR':>7s}", end="")
            print()
        
        # Synergy phase diagram
        print(f"\n  PHASE DIAGRAM (PID Synergy):")
        print(f"  {'':10s}", end="")
        for cs in convention_strengths:
            print(f"  cs={cs:.2f}", end="")
        print()
        
        for cr in cultural_rates:
            print(f"  cr={cr:.2f}", end="")
            for cs in convention_strengths:
                match = [r for r in valid if r['cultural_rate'] == cr and r['convention_strength'] == cs]
                if match:
                    syn = match[0]['mean_synergy']
                    print(f"  {syn:.4f}", end="")
                else:
                    print(f"  {'ERR':>7s}", end="")
            print()
    
    return results


def comparison_experiment():
    """
    V1 vs V2: Run the same conditions and compare.
    Shows how replacing distributional drift with PID synergy changes the picture.
    """
    print("🔺 V2 COMPARISON: Old Transformation vs PID Synergy")
    print("=" * 70)
    
    conditions = [
        {"label": "baseline", "use_cultural": False, "use_convention": False,
         "cultural_rate": 0.0, "convention_strength": 0.0},
        {"label": "culture_only", "use_cultural": True, "use_convention": False,
         "cultural_rate": 0.15, "convention_strength": 0.0},
        {"label": "convention_only", "use_cultural": False, "use_convention": True,
         "cultural_rate": 0.0, "convention_strength": 0.05},
        {"label": "culture+convention", "use_cultural": True, "use_convention": True,
         "cultural_rate": 0.15, "convention_strength": 0.05},
        {"label": "high_culture", "use_cultural": True, "use_convention": True,
         "cultural_rate": 0.30, "convention_strength": 0.10},
    ]
    
    all_results = []
    
    for cond in conditions:
        label = cond.pop("label")
        print(f"\n{'─'*60}")
        print(f"  Running: {label}")
        
        t0 = time.time()
        r = run_single(ticks=2000, num_agents=60, label=label, **cond)
        elapsed = time.time() - t0
        
        if "summary" in r:
            s = r["summary"]
            print(f"  Memory:    {s['mean_memory']:.4f}")
            print(f"  Transport: {s['mean_transport']:.4f}")
            print(f"  Synergy:   {s['mean_synergy']:.4f} (ratio: {s['mean_synergy_ratio']:.3f})")
            print(f"  Redundancy:{s['mean_redundancy']:.4f}")
            print(f"  Triple:    {s['mean_triple']:.4f} (max: {s['max_triple']:.4f})")
            print(f"  Computing: {s['computing_windows']}/{s['total_windows']} windows")
            print(f"  Time:      {elapsed:.1f}s")
            
            all_results.append({"label": label, **s, "elapsed": round(elapsed, 1)})
        else:
            print(f"  ERROR: {r.get('error')}")
    
    # Summary table
    if all_results:
        print("\n\n" + "=" * 70)
        print("SUMMARY TABLE")
        print("=" * 70)
        print(f"{'Condition':<22s} {'Memory':>8s} {'Transport':>10s} {'Synergy':>8s} {'SynRatio':>9s} {'Triple':>8s}")
        print("─" * 70)
        for r in all_results:
            print(f"{r['label']:<22s} {r['mean_memory']:>8.4f} {r['mean_transport']:>10.4f} "
                  f"{r['mean_synergy']:>8.4f} {r['mean_synergy_ratio']:>9.3f} {r['mean_triple']:>8.4f}")
    
    return all_results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["compare", "sweep", "single"], default="compare")
    parser.add_argument("--ticks", type=int, default=2000)
    args = parser.parse_args()
    
    if args.mode == "compare":
        results = comparison_experiment()
        Path("triple_point_v2_comparison.json").write_text(json.dumps(results, indent=2))
        print("\nSaved to triple_point_v2_comparison.json")
    
    elif args.mode == "sweep":
        results = criticality_sweep()
        Path("criticality_sweep_results.json").write_text(json.dumps(results, indent=2))
        print("\nSaved to criticality_sweep_results.json")
    
    elif args.mode == "single":
        r = run_single(ticks=args.ticks, label="single_run")
        if "summary" in r:
            s = r["summary"]
            print(f"\nTriple Point: {s['mean_triple']:.4f}")
            print(f"  Memory:    {s['mean_memory']:.4f}")
            print(f"  Transport: {s['mean_transport']:.4f}")
            print(f"  Synergy:   {s['mean_synergy']:.4f}")
