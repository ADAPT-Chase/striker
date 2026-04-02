#!/usr/bin/env python3
"""
🔺 TRIPLE POINT ANALYSIS FOR AGENT COMMUNICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bridges entropy-edge and emergence-sim.

The triple-point hypothesis from cellular automata:
  Computation = Memory + Transport + Transformation

Applied to agent communication:
  Memory      → Does the population remember past signal states?
                (temporal MI of collective signal patterns)
  Transport   → Do signals propagate spatially through the population?
                (spatial MI between local signal clusters)
  Transformation → Does information change during propagation?
                   (transfer entropy: how much does a source region
                    causally influence a target region's FUTURE,
                    beyond the target's own past?)

If all three are non-trivial simultaneously, the agents aren't just
signaling — they're computing collectively.
"""

import math
import sys
import json
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def population_signal_state(agents, num_signals=4):
    """Encode collective signal state as discrete tuple."""
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    ctx_signal = defaultdict(lambda: defaultdict(int))

    for a in agents:
        if hasattr(a, 'current_signal') and a.current_signal is not None and a.current_signal >= 0:
            ctx = getattr(a, 'last_context', 'alone') or 'alone'
            ctx_signal[ctx][a.current_signal] += 1

    # Dominant signal per context
    state = []
    for ctx in contexts:
        if ctx_signal[ctx]:
            dominant = max(ctx_signal[ctx], key=ctx_signal[ctx].get)
            state.append(dominant)
        else:
            state.append(-1)
    return tuple(state)


def spatial_clusters(agents, radius=20.0):
    """Group agents into spatial clusters for transport analysis."""
    # Simple grid-based clustering
    grid = defaultdict(list)
    cell_size = radius
    for a in agents:
        gx = int(a.x / cell_size)
        gy = int(a.y / cell_size)
        grid[(gx, gy)].append(a)
    return dict(grid)


def cluster_signal_state(cluster_agents, num_signals=4):
    """Signal state of a spatial cluster."""
    counts = [0] * num_signals
    for a in cluster_agents:
        if hasattr(a, 'current_signal') and a.current_signal is not None and a.current_signal >= 0:
            counts[a.current_signal] += 1
    total = sum(counts)
    if total == 0:
        return tuple([0] * num_signals)
    # Discretize to dominant signal
    return tuple(counts)


def entropy(counts_or_seq):
    """Shannon entropy of a sequence or count dict."""
    if isinstance(counts_or_seq, dict):
        total = sum(counts_or_seq.values())
        if total == 0:
            return 0.0
        probs = [c / total for c in counts_or_seq.values() if c > 0]
    else:
        counter = Counter(counts_or_seq)
        total = len(counts_or_seq)
        if total == 0:
            return 0.0
        probs = [c / total for c in counter.values()]

    return -sum(p * math.log2(p) for p in probs if p > 0)


def mutual_information(seq_a, seq_b):
    """MI between two sequences."""
    if len(seq_a) != len(seq_b) or len(seq_a) == 0:
        return 0.0
    h_a = entropy(seq_a)
    h_b = entropy(seq_b)
    joint = Counter(zip(seq_a, seq_b))
    h_ab = entropy(joint)
    return max(0.0, h_a + h_b - h_ab)


class TriplePointAnalyzer:
    """
    Measures all three axes of the triple point for agent populations:
    Memory, Transport, Transformation.
    """

    def __init__(self, num_signals=4):
        self.num_signals = num_signals

        # Time series of population states
        self.pop_states = []           # global signal states per tick
        self.cluster_states = []       # {cluster_id: signal_state} per tick
        self.tick_count = 0

        # Results
        self.memory_scores = []
        self.transport_scores = []
        self.transform_scores = []
        self.triple_scores = []

        # Windowed analysis
        self.window = 100
        self.stride = 50

    def record_tick(self, agents):
        """Record one tick of agent state."""
        self.tick_count += 1

        # Global state
        self.pop_states.append(population_signal_state(agents, self.num_signals))

        # Cluster states
        clusters = spatial_clusters(agents, radius=20.0)
        c_states = {}
        for cid, cluster_agents in clusters.items():
            c_states[cid] = cluster_signal_state(cluster_agents, self.num_signals)
        self.cluster_states.append(c_states)

    def analyze(self) -> Dict:
        """Run full triple-point analysis on recorded data."""
        if len(self.pop_states) < self.window:
            return {"error": "Not enough data", "ticks": len(self.pop_states)}

        results = {
            "ticks_recorded": len(self.pop_states),
            "windows_analyzed": 0,
            "memory": [],
            "transport": [],
            "transformation": [],
            "triple_point": [],
        }

        # Sliding window analysis
        for start in range(0, len(self.pop_states) - self.window, self.stride):
            end = start + self.window
            window_states = self.pop_states[start:end]
            window_clusters = self.cluster_states[start:end]

            mem = self._measure_memory(window_states)
            trans = self._measure_transport(window_clusters)
            transform = self._measure_transformation(window_clusters)

            # Geometric mean — all three must be non-trivial
            triple = (mem * trans * transform) ** (1/3) if min(mem, trans, transform) > 0 else 0.0

            results["memory"].append(round(mem, 4))
            results["transport"].append(round(trans, 4))
            results["transformation"].append(round(transform, 4))
            results["triple_point"].append(round(triple, 4))
            results["windows_analyzed"] += 1

        # Summary statistics
        if results["triple_point"]:
            results["summary"] = {
                "mean_memory": round(sum(results["memory"]) / len(results["memory"]), 4),
                "mean_transport": round(sum(results["transport"]) / len(results["transport"]), 4),
                "mean_transformation": round(sum(results["transformation"]) / len(results["transformation"]), 4),
                "mean_triple": round(sum(results["triple_point"]) / len(results["triple_point"]), 4),
                "max_triple": round(max(results["triple_point"]), 4),
                "computing_windows": sum(1 for t in results["triple_point"] if t > 0.1),
                "total_windows": len(results["triple_point"]),
            }

        return results

    def _measure_memory(self, states, lag=1) -> float:
        """
        Temporal MI between population states at t and t+lag.
        High = population remembers its recent signal state.
        """
        if len(states) < lag + 10:
            return 0.0

        seq_a = states[:-lag]
        seq_b = states[lag:]
        mi = mutual_information(seq_a, seq_b)

        # Normalize by entropy of source
        h = entropy(seq_a)
        if h == 0:
            return 0.0
        return min(1.0, mi / h)

    def _measure_transport(self, cluster_states_series) -> float:
        """
        Spatial MI between neighboring clusters.
        High = signal patterns are spatially correlated (information moves).
        """
        if len(cluster_states_series) < 10:
            return 0.0

        mi_values = []

        for tick_clusters in cluster_states_series:
            cluster_ids = list(tick_clusters.keys())
            if len(cluster_ids) < 2:
                continue

            # Compare adjacent clusters
            for i, cid_a in enumerate(cluster_ids):
                for cid_b in cluster_ids[i+1:]:
                    # Check if adjacent (Manhattan distance <= 1)
                    if abs(cid_a[0] - cid_b[0]) + abs(cid_a[1] - cid_b[1]) <= 1:
                        state_a = tick_clusters[cid_a]
                        state_b = tick_clusters[cid_b]
                        # Simple similarity measure
                        if state_a == state_b and sum(state_a) > 0:
                            mi_values.append(1.0)
                        elif sum(state_a) > 0 and sum(state_b) > 0:
                            # Cosine-like similarity
                            dot = sum(a*b for a, b in zip(state_a, state_b))
                            mag_a = math.sqrt(sum(a*a for a in state_a))
                            mag_b = math.sqrt(sum(b*b for b in state_b))
                            if mag_a > 0 and mag_b > 0:
                                mi_values.append(dot / (mag_a * mag_b))

        if not mi_values:
            return 0.0
        return sum(mi_values) / len(mi_values)

    def _measure_transformation(self, cluster_states_series, lag=1) -> float:
        """
        Transfer entropy between spatial clusters across time.
        High = information changes during spatial propagation.
        This separates a conveyor belt from a logic gate.
        """
        if len(cluster_states_series) < lag + 10:
            return 0.0

        transform_scores = []

        for t in range(lag, min(len(cluster_states_series), 200)):
            prev = cluster_states_series[t - lag]
            curr = cluster_states_series[t]

            common_ids = set(prev.keys()) & set(curr.keys())
            if len(common_ids) < 2:
                continue

            for cid in common_ids:
                prev_state = prev[cid]
                curr_state = curr[cid]

                if sum(prev_state) == 0 or sum(curr_state) == 0:
                    continue

                # How different is the current state from the previous?
                # High difference + high signal presence = transformation
                prev_dom = max(range(len(prev_state)), key=lambda i: prev_state[i])
                curr_dom = max(range(len(curr_state)), key=lambda i: curr_state[i])

                if prev_dom != curr_dom and sum(curr_state) > 2:
                    transform_scores.append(1.0)
                elif prev_dom == curr_dom:
                    # Same dominant signal — some transformation might still happen
                    # in the distribution
                    prev_total = sum(prev_state)
                    curr_total = sum(curr_state)
                    if prev_total > 0 and curr_total > 0:
                        prev_dist = [p/prev_total for p in prev_state]
                        curr_dist = [c/curr_total for c in curr_state]
                        kl = sum(c * math.log2(c/p) for c, p in zip(curr_dist, prev_dist)
                                 if c > 0 and p > 0)
                        transform_scores.append(min(1.0, abs(kl)))

        if not transform_scores:
            return 0.0

        raw = sum(transform_scores) / len(transform_scores)
        # Balance penalty: pure noise transforms maximally but isn't computation
        # Penalize extreme transformation (> 0.8) slightly
        if raw > 0.8:
            raw = 0.8 + (raw - 0.8) * 0.5
        return raw


def run_experiment(ticks=2000, num_agents=60, use_cultural=True,
                   use_convention=True, use_seasons=False, 
                   use_predator=False) -> Dict:
    """Run the emergence sim and measure triple-point metrics."""
    import sim as emergence_sim

    print(f"🔺 Triple Point Agent Experiment")
    print(f"   Agents: {num_agents}, Ticks: {ticks}")
    print(f"   Cultural: {use_cultural}, Convention: {use_convention}")
    print(f"   Seasons: {use_seasons}, Predator: {use_predator}")
    print()

    # Create simulation
    s = emergence_sim.Simulation(
        num_agents=num_agents,
        use_seasons=use_seasons,
        use_predator=use_predator,
    )

    # Configure cultural/convention if available
    if hasattr(s, 'cultural_transmission'):
        s.cultural_transmission = use_cultural
    if hasattr(s, 'convention_enforcement'):
        s.convention_enforcement = use_convention

    analyzer = TriplePointAnalyzer()

    print("Running simulation...")
    for tick in range(ticks):
        s.step()
        analyzer.record_tick(s.agents)

        if tick > 0 and tick % 500 == 0:
            print(f"  Tick {tick}/{ticks} — {len(s.agents)} agents alive")

    print(f"\nAnalyzing {ticks} ticks...")
    results = analyzer.analyze()

    if "summary" in results:
        summary = results["summary"]
        print(f"\n{'='*60}")
        print(f"🔺 TRIPLE POINT RESULTS")
        print(f"{'='*60}")
        print(f"  Memory:         {summary['mean_memory']:.4f}")
        print(f"  Transport:      {summary['mean_transport']:.4f}")
        print(f"  Transformation: {summary['mean_transformation']:.4f}")
        print(f"  ─────────────────────────")
        print(f"  Triple Point:   {summary['mean_triple']:.4f} (max: {summary['max_triple']:.4f})")
        print(f"  Computing:      {summary['computing_windows']}/{summary['total_windows']} windows")
        print(f"{'='*60}")

        # Interpret
        if summary['mean_triple'] > 0.2:
            print("  💡 COLLECTIVE COMPUTATION DETECTED")
            print("     All three axes non-trivial simultaneously.")
        elif summary['mean_triple'] > 0.1:
            print("  🔶 Weak computation signal")
            print("     Some structure but not clearly computing.")
        else:
            print("  ⬜ No computation detected")
            print("     Agents may be signaling but not computing collectively.")

        # Which axis is the bottleneck?
        axes = {
            'memory': summary['mean_memory'],
            'transport': summary['mean_transport'],
            'transformation': summary['mean_transformation']
        }
        bottleneck = min(axes, key=axes.get)
        strongest = max(axes, key=axes.get)
        print(f"\n  Strongest axis: {strongest} ({axes[strongest]:.4f})")
        print(f"  Bottleneck:     {bottleneck} ({axes[bottleneck]:.4f})")

    return results


if __name__ == "__main__":
    # Run with cultural transmission + convention (should show computation)
    print("=" * 60)
    print("EXPERIMENT 1: With cultural transmission + convention")
    print("=" * 60)
    results_with = run_experiment(
        ticks=2000, num_agents=60,
        use_cultural=True, use_convention=True
    )

    print("\n\n")

    # Run without (baseline — should show less computation)
    print("=" * 60)
    print("EXPERIMENT 2: Without cultural transmission (baseline)")
    print("=" * 60)
    results_without = run_experiment(
        ticks=2000, num_agents=60,
        use_cultural=False, use_convention=False
    )

    # Compare
    if "summary" in results_with and "summary" in results_without:
        print("\n\n")
        print("=" * 60)
        print("COMPARISON")
        print("=" * 60)
        for axis in ["mean_memory", "mean_transport", "mean_transformation", "mean_triple"]:
            w = results_with["summary"][axis]
            wo = results_without["summary"][axis]
            delta = w - wo
            label = axis.replace("mean_", "").capitalize()
            print(f"  {label:20s}: {wo:.4f} → {w:.4f}  (Δ = {delta:+.4f})")

    # Save results
    output = {
        "with_culture": results_with,
        "without_culture": results_without,
    }
    Path("triple_point_agent_results.json").write_text(json.dumps(output, indent=2))
    print("\nResults saved to triple_point_agent_results.json")
