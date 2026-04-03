#!/usr/bin/env python3
"""
🔺 TRIPLE POINT V3: PID-SYNERGY TRANSFORMATION AXIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V2 used distributional drift for transformation — PID proved that was
measuring noise, not computation. Scrambled weights scored HIGHER than
learned ones.

V3 replaces the transformation axis with PID synergy:
  Transformation = synergy between neighboring cluster pairs → target cluster future

Also runs a criticality sweep: the PID finding suggests the system is
too ordered. By sweeping cultural_rate and convention_bonus, we find
the edge of chaos where genuine computation peaks.

Striker, April 2026
"""

import math
import sys
import json
import time
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
from pathlib import Path
from itertools import combinations

sys.path.insert(0, str(Path(__file__).parent))

from pid_synergy import (
    pid_decompose, cluster_dominant_signal, spatial_clusters as pid_spatial_clusters,
    neighboring_cells, mutual_information as pid_mi, entropy as pid_entropy
)


# ── Triple Point Analyzer V3 ─────────────────────────────────────────

class TriplePointV3:
    """
    Triple-point with PID synergy as transformation axis.
    
    Memory      → temporal MI of population signal state
    Transport   → spatial MI between neighboring clusters  
    Transformation → PID SYNERGY: info requiring BOTH neighbor sources
    """

    def __init__(self, num_signals=4, cell_size=20.0, window=100, stride=50):
        self.num_signals = num_signals
        self.cell_size = cell_size
        self.window = window
        self.stride = stride

        # Per-cluster time series of dominant signals
        self.cluster_history = defaultdict(list)
        # Global population state time series
        self.pop_states = []
        self.tick_count = 0

    def record_tick(self, agents):
        """Record one tick of agent state."""
        self.tick_count += 1

        # Global state for memory measurement
        contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
        ctx_signal = defaultdict(lambda: defaultdict(int))
        for a in agents:
            if hasattr(a, 'current_signal') and a.current_signal is not None and a.current_signal >= 0:
                ctx = getattr(a, 'last_context', 'alone') or 'alone'
                ctx_signal[ctx][a.current_signal] += 1
        state = []
        for ctx in contexts:
            if ctx_signal[ctx]:
                state.append(max(ctx_signal[ctx], key=ctx_signal[ctx].get))
            else:
                state.append(-1)
        self.pop_states.append(tuple(state))

        # Per-cluster dominant signal
        clusters = pid_spatial_clusters(agents, self.cell_size)
        active_cells = set()
        for cell_id, cell_agents in clusters.items():
            dom = cluster_dominant_signal(cell_agents, self.num_signals)
            self.cluster_history[cell_id].append(dom)
            active_cells.add(cell_id)

        # Mark inactive cells
        for cell_id in list(self.cluster_history.keys()):
            if cell_id not in active_cells:
                self.cluster_history[cell_id].append(-1)

    def analyze(self) -> Dict:
        """Full triple-point analysis with PID synergy."""
        if self.tick_count < self.window + 1:
            return {"error": f"Need {self.window+1}+ ticks, have {self.tick_count}"}

        # Find valid clusters
        all_cells = [c for c, hist in self.cluster_history.items()
                     if len(hist) >= self.window 
                     and sum(1 for h in hist if h >= 0) > self.window * 0.3]

        if len(all_cells) < 3:
            return {"error": "Too few active clusters", "cells": len(all_cells)}

        # Build neighbor map for synergy triplets
        cell_set = set(all_cells)
        neighbor_map = {}
        for cell in all_cells:
            nbrs = [n for n in neighboring_cells(cell) if n in cell_set]
            if len(nbrs) >= 2:
                neighbor_map[cell] = nbrs

        # Sliding window
        windows = []
        for start in range(0, self.tick_count - self.window, self.stride):
            end = start + self.window

            mem = self._measure_memory(start, end)
            trans = self._measure_transport(start, end, all_cells)
            transform = self._measure_synergy(start, end, neighbor_map)

            # Geometric mean — all three must contribute
            if min(mem, trans, transform) > 0:
                triple = (mem * trans * transform) ** (1/3)
            else:
                triple = 0.0

            windows.append({
                "start": start,
                "memory": round(mem, 4),
                "transport": round(trans, 4),
                "transformation": round(transform, 4),
                "triple": round(triple, 4),
            })

        if not windows:
            return {"error": "No valid windows"}

        # Summary
        n = len(windows)
        summary = {
            "n_windows": n,
            "n_active_cells": len(all_cells),
            "n_triplet_cells": len(neighbor_map),
            "mean_memory": round(sum(w["memory"] for w in windows) / n, 4),
            "mean_transport": round(sum(w["transport"] for w in windows) / n, 4),
            "mean_transformation": round(sum(w["transformation"] for w in windows) / n, 4),
            "mean_triple": round(sum(w["triple"] for w in windows) / n, 4),
            "max_triple": round(max(w["triple"] for w in windows), 4),
        }

        # Bottleneck analysis
        axes = {
            "memory": summary["mean_memory"],
            "transport": summary["mean_transport"],
            "transformation": summary["mean_transformation"],
        }
        summary["bottleneck"] = min(axes, key=axes.get)
        summary["strongest"] = max(axes, key=axes.get)

        return {"summary": summary, "windows": windows}

    def _measure_memory(self, start, end, lag=1) -> float:
        """Temporal MI of population state."""
        states = self.pop_states[start:end]
        if len(states) < lag + 10:
            return 0.0
        seq_a = states[:-lag]
        seq_b = states[lag:]
        h = pid_entropy(seq_a)
        if h == 0:
            return 0.0
        mi = pid_mi(seq_a, seq_b)
        return min(1.0, mi / h)

    def _measure_transport(self, start, end, all_cells) -> float:
        """Spatial MI between neighboring clusters (temporal sequence)."""
        cell_set = set(all_cells)
        mi_values = []

        for cell in all_cells:
            nbrs = [n for n in neighboring_cells(cell) if n in cell_set]
            for nbr in nbrs:
                # Get time series for both
                seq_a = self.cluster_history[cell][start:end]
                seq_b = self.cluster_history[nbr][start:end]
                
                # Filter valid ticks
                valid = [(a, b) for a, b in zip(seq_a, seq_b) if a >= 0 and b >= 0]
                if len(valid) < 20:
                    continue
                
                a_clean = [v[0] for v in valid]
                b_clean = [v[1] for v in valid]
                
                h_a = pid_entropy(a_clean)
                if h_a > 0:
                    mi = pid_mi(a_clean, b_clean)
                    mi_values.append(min(1.0, mi / h_a))

        if not mi_values:
            return 0.0
        return sum(mi_values) / len(mi_values)

    def _measure_synergy(self, start, end, neighbor_map) -> float:
        """
        PID synergy as transformation metric.
        
        For each target cell C with neighbor sources A, B:
          synergy of I(A_t, B_t → C_{t+1})
        
        This measures genuine computation — info requiring BOTH inputs.
        """
        synergy_scores = []

        for target_cell, neighbors in neighbor_map.items():
            # Try pairs of neighbors as sources
            for a_cell, b_cell in combinations(neighbors[:4], 2):
                s1 = self.cluster_history[a_cell][start:end]
                s2 = self.cluster_history[b_cell][start:end]
                target = self.cluster_history[target_cell][start+1:end+1]

                if len(target) < 20:
                    continue

                # Filter valid
                valid = [(s1[i], s2[i], target[i]) for i in range(len(target))
                         if s1[i] >= 0 and s2[i] >= 0 and target[i] >= 0]

                if len(valid) < 20:
                    continue

                s1_c = [v[0] for v in valid]
                s2_c = [v[1] for v in valid]
                t_c = [v[2] for v in valid]

                pid = pid_decompose(t_c, s1_c, s2_c)

                if pid['total_mi'] > 0.01:
                    # Use synergy ratio — normalized, comparable across conditions
                    synergy_scores.append(pid['synergy_ratio'])

        if not synergy_scores:
            return 0.0
        return sum(synergy_scores) / len(synergy_scores)


# ── Criticality Sweep ─────────────────────────────────────────────────

def run_single(ticks, num_agents, cultural_rate, convention_bonus, 
               cultural_blend=0.45, seed=None):
    """Run one sim config and return triple-point results."""
    import sim as emergence_sim
    import random as rng
    
    if seed is not None:
        rng.seed(seed)
    
    # Patch module-level constants BEFORE creating sim
    emergence_sim.CULTURAL_RATE = cultural_rate
    emergence_sim.CULTURAL_BLEND = cultural_blend
    emergence_sim.CONVENTION_BONUS = convention_bonus
    emergence_sim.CONVENTION_PENALTY = convention_bonus * 0.33  # keep ratio
    
    s = emergence_sim.Simulation(num_agents=num_agents)

    analyzer = TriplePointV3()

    for tick in range(ticks):
        s.step()
        analyzer.record_tick(s.agents)

    return analyzer.analyze()


def criticality_sweep(ticks=1500, num_agents=50, n_cultural=6, n_convention=6):
    """
    Sweep cultural_rate × convention_bonus to find the edge of chaos.
    
    High cultural_rate + high convention → ordered (too much copying)
    Low cultural_rate + low convention → chaotic (too much randomness)
    Edge of chaos → maximum synergy
    """
    import numpy as np
    
    # Sweep ranges — wider than before to find edge
    cultural_rates = np.linspace(0.01, 0.5, n_cultural)
    convention_bonuses = np.linspace(0.0, 0.12, n_convention)
    
    results = []
    total = n_cultural * n_convention
    
    print(f"🔺 CRITICALITY SWEEP: {total} configurations")
    print(f"   Cultural rate: {cultural_rates[0]:.3f} → {cultural_rates[-1]:.3f}")
    print(f"   Convention bonus: {convention_bonuses[0]:.3f} → {convention_bonuses[-1]:.3f}")
    print(f"   {ticks} ticks, {num_agents} agents each\n")
    
    for i, cr in enumerate(cultural_rates):
        for j, cs in enumerate(convention_bonuses):
            idx = i * n_convention + j + 1
            t0 = time.time()
            
            result = run_single(
                ticks=ticks, num_agents=num_agents,
                cultural_rate=cr, convention_bonus=cs,
                seed=42  # fixed seed for comparability
            )
            
            elapsed = time.time() - t0
            
            if "summary" in result:
                s = result["summary"]
                entry = {
                    "cultural_rate": round(float(cr), 4),
                    "convention_bonus": round(float(cs), 4),
                    "memory": s["mean_memory"],
                    "transport": s["mean_transport"],
                    "transformation": s["mean_transformation"],
                    "triple": s["mean_triple"],
                    "max_triple": s["max_triple"],
                    "bottleneck": s["bottleneck"],
                    "n_triplets": s.get("n_triplet_cells", 0),
                }
                results.append(entry)
                
                flag = " ⭐" if entry["triple"] > 0.15 else ""
                print(f"  [{idx:2d}/{total}] cr={cr:.3f} cs={cs:.3f} → "
                      f"M={s['mean_memory']:.3f} T={s['mean_transport']:.3f} "
                      f"S={s['mean_transformation']:.3f} "
                      f"triple={s['mean_triple']:.4f} [{s['bottleneck']}] "
                      f"({elapsed:.1f}s){flag}")
            else:
                print(f"  [{idx:2d}/{total}] cr={cr:.3f} cs={cs:.3f} → ERROR: {result.get('error')}")
    
    # Analysis
    if results:
        print(f"\n{'='*70}")
        print("CRITICALITY SWEEP RESULTS")
        print(f"{'='*70}")
        
        # Sort by triple score
        by_triple = sorted(results, key=lambda r: r["triple"], reverse=True)
        
        print("\n  Top 5 configurations:")
        for i, r in enumerate(by_triple[:5]):
            print(f"    {i+1}. cr={r['cultural_rate']:.3f} cs={r['convention_bonus']:.3f} "
                  f"→ triple={r['triple']:.4f} "
                  f"(M={r['memory']:.3f} T={r['transport']:.3f} S={r['transformation']:.3f}) "
                  f"[bottleneck: {r['bottleneck']}]")
        
        print(f"\n  Worst 3:")
        for i, r in enumerate(by_triple[-3:]):
            print(f"    {i+1}. cr={r['cultural_rate']:.3f} cs={r['convention_bonus']:.3f} "
                  f"→ triple={r['triple']:.4f}")
        
        # Synergy landscape
        best = by_triple[0]
        print(f"\n  🎯 OPTIMAL CRITICALITY:")
        print(f"     cultural_rate = {best['cultural_rate']:.4f}")
        print(f"     convention_bonus = {best['convention_bonus']:.4f}")
        print(f"     triple_point = {best['triple']:.4f}")
        print(f"     synergy = {best['transformation']:.4f}")
        
        # Check if edge of chaos pattern holds
        # Do high-synergy configs cluster at intermediate parameter values?
        top_crs = [r['cultural_rate'] for r in by_triple[:5]]
        top_css = [r['convention_bonus'] for r in by_triple[:5]]
        print(f"\n  Top-5 cultural_rate range: {min(top_crs):.3f} - {max(top_crs):.3f}")
        print(f"  Top-5 convention range:    {min(top_css):.3f} - {max(top_css):.3f}")
        
        cr_range = (cultural_rates[-1] - cultural_rates[0])
        cs_range = (convention_bonuses[-1] - convention_bonuses[0])
        avg_cr = sum(top_crs) / len(top_crs)
        avg_cs = sum(top_css) / len(top_css)
        
        # Is the optimal at the middle of the range?
        cr_pos = (avg_cr - cultural_rates[0]) / cr_range if cr_range > 0 else 0.5
        cs_pos = (avg_cs - convention_bonuses[0]) / cs_range if cs_range > 0 else 0.5
        
        if 0.2 < cr_pos < 0.8 and 0.2 < cs_pos < 0.8:
            print(f"\n  ✅ EDGE OF CHAOS CONFIRMED: optimal is at intermediate values")
            print(f"     Cultural rate at {cr_pos:.0%} of range, convention at {cs_pos:.0%}")
        elif cr_pos <= 0.2 or cs_pos <= 0.2:
            print(f"\n  🔥 System prefers LOW order — currently too constrained")
        else:
            print(f"\n  ❄️ System prefers HIGH order — currently too chaotic")
    
    return results


# ── Comparison Run ────────────────────────────────────────────────────

def comparison_run(ticks=1500, num_agents=50):
    """
    Direct comparison: V3 (PID synergy) vs V2 (distributional drift)
    on the same simulation runs.
    """
    from triple_point_agents import TriplePointAnalyzer as V2Analyzer
    import sim as emergence_sim
    
    configs = [
        {"name": "Cultural+Convention", "cultural": True, "convention": True},
        {"name": "No culture (baseline)", "cultural": False, "convention": False},
    ]
    
    print(f"🔺 V2 vs V3 COMPARISON ({ticks} ticks, {num_agents} agents)")
    print(f"{'='*70}\n")
    
    all_results = {}
    
    for config in configs:
        print(f"  Config: {config['name']}")
        
        s = emergence_sim.Simulation(num_agents=num_agents)
        if hasattr(s, 'cultural_transmission'):
            s.cultural_transmission = config['cultural']
        if hasattr(s, 'convention_enforcement'):
            s.convention_enforcement = config['convention']
        
        v2 = V2Analyzer()
        v3 = TriplePointV3()
        
        for tick in range(ticks):
            s.step()
            v2.record_tick(s.agents)
            v3.record_tick(s.agents)
            if tick > 0 and tick % 500 == 0:
                print(f"    Tick {tick}/{ticks}")
        
        r_v2 = v2.analyze()
        r_v3 = v3.analyze()
        
        if "summary" in r_v2 and "summary" in r_v3:
            s2, s3 = r_v2["summary"], r_v3["summary"]
            print(f"\n    {'Metric':<20s} {'V2 (drift)':<15s} {'V3 (PID syn)':<15s} {'Δ':>10s}")
            print(f"    {'─'*60}")
            for axis in ["mean_memory", "mean_transport", "mean_transformation", "mean_triple"]:
                v2_val = s2.get(axis, 0)
                v3_val = s3.get(axis, 0)
                delta = v3_val - v2_val
                label = axis.replace("mean_", "")
                print(f"    {label:<20s} {v2_val:<15.4f} {v3_val:<15.4f} {delta:>+10.4f}")
            
            all_results[config['name']] = {"v2": s2, "v3": s3}
        
        print()
    
    return all_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Triple Point V3 with PID Synergy")
    parser.add_argument("--mode", choices=["compare", "sweep", "single"], default="sweep")
    parser.add_argument("--ticks", type=int, default=1500)
    parser.add_argument("--agents", type=int, default=50)
    parser.add_argument("--grid", type=int, default=5, help="Grid size for sweep (NxN)")
    args = parser.parse_args()
    
    if args.mode == "compare":
        results = comparison_run(ticks=args.ticks, num_agents=args.agents)
        Path("triple_point_v3_comparison.json").write_text(json.dumps(results, indent=2, default=str))
        print("Saved to triple_point_v3_comparison.json")
        
    elif args.mode == "sweep":
        results = criticality_sweep(
            ticks=args.ticks, num_agents=args.agents,
            n_cultural=args.grid, n_convention=args.grid
        )
        Path("criticality_sweep_v3.json").write_text(json.dumps(results, indent=2))
        print(f"\nSaved {len(results)} results to criticality_sweep_v3.json")
        
    elif args.mode == "single":
        result = run_single(
            ticks=args.ticks, num_agents=args.agents,
            cultural_rate=0.134, convention_bonus=0.03
        )
        if "summary" in result:
            s = result["summary"]
            print(f"\n🔺 SINGLE RUN RESULT:")
            print(f"   Memory:         {s['mean_memory']:.4f}")
            print(f"   Transport:      {s['mean_transport']:.4f}")
            print(f"   Transformation: {s['mean_transformation']:.4f} (PID synergy)")
            print(f"   Triple Point:   {s['mean_triple']:.4f}")
            print(f"   Bottleneck:     {s['bottleneck']}")
        else:
            print(f"ERROR: {result}")
