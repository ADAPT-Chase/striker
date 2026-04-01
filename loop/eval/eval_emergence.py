#!/usr/bin/env python3
"""
Evaluate the emergence simulator. Runs headless for N ticks and measures:
1. Population stability (std dev of population over time)
2. Signal diversity (how many distinct signal types are actively used)
3. Cluster dynamics (average number of flocks)
4. Survival rate (% of agents alive at end vs start)
5. Emergent meanings (signals that develop consistent associations)

Returns a composite score (0-1, higher = more interesting emergence).
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "projects", "emergence-sim"))

def evaluate(ticks: int = 500, agents: int = 40, runs: int = 3) -> dict:
    """Run simulation and compute emergence score."""
    try:
        import sim as emergence_sim
    except ImportError:
        return {"score": 0.0, "error": "Cannot import sim module"}

    scores = []
    for run_i in range(runs):
        try:
            s = emergence_sim.Simulation(num_agents=agents)
            pop_history = []
            cluster_history = []
            signal_counts = {0: 0, 1: 0, 2: 0, 3: 0}

            for tick in range(ticks):
                s.step()
                pop_history.append(len(s.agents))

                if hasattr(s, '_count_clusters'):
                    cluster_history.append(s._count_clusters())

                # Count signal emissions
                for agent in s.agents:
                    if hasattr(agent, 'current_signal') and agent.current_signal is not None:
                        sig = agent.current_signal
                        if sig in signal_counts:
                            signal_counts[sig] += 1

            # ── Metrics ──────────────────────────────────────────
            # 1. Population stability (prefer stable but dynamic, not flat or crashed)
            if len(pop_history) > 10:
                import statistics
                mean_pop = statistics.mean(pop_history)
                std_pop = statistics.stdev(pop_history) if len(pop_history) > 1 else 0
                # Sweet spot: some variance (dynamic) but not too much (chaotic)
                if mean_pop > 0:
                    cv = std_pop / mean_pop  # coefficient of variation
                    # Best around cv = 0.15-0.3 (dynamic but stable)
                    stability = max(0, 1 - abs(cv - 0.2) * 3)
                else:
                    stability = 0
            else:
                stability = 0

            # 2. Signal diversity (all 4 signals being used = more interesting)
            total_signals = sum(signal_counts.values())
            if total_signals > 0:
                signal_props = [c / total_signals for c in signal_counts.values()]
                # Shannon entropy normalized
                import math
                entropy = 0
                for p in signal_props:
                    if p > 0:
                        entropy -= p * math.log2(p)
                signal_diversity = entropy / 2.0  # normalize to 0-1 (max entropy = 2 for 4 signals)
            else:
                signal_diversity = 0

            # 3. Cluster dynamics (variety of flock counts = interesting)
            if cluster_history:
                unique_clusters = len(set(cluster_history))
                cluster_score = min(1.0, unique_clusters / 10)
            else:
                cluster_score = 0

            # 4. Survival rate
            initial_pop = agents
            final_pop = pop_history[-1] if pop_history else 0
            survival = final_pop / initial_pop if initial_pop > 0 else 0
            # Prefer survival around 0.5-1.5x initial (too low = extinction, too high = no pressure)
            survival_score = max(0, 1 - abs(survival - 0.8) * 2)

            # 5. Emergent meaning detection
            meaning_score = 0
            if hasattr(s, 'emergence_logger') and hasattr(s.emergence_logger, 'meanings_detected'):
                meaning_score = min(1.0, s.emergence_logger.meanings_detected / 4)
            elif total_signals > 100:
                # Rough proxy: if signals are used differentially, some meaning may have emerged
                max_prop = max(signal_props) if signal_props else 0
                min_prop = min(signal_props) if signal_props else 0
                if max_prop - min_prop > 0.15:
                    meaning_score = 0.5

            # Composite score
            composite = (
                stability * 0.20 +
                signal_diversity * 0.25 +
                cluster_score * 0.15 +
                survival_score * 0.20 +
                meaning_score * 0.20
            )
            scores.append(composite)

        except Exception as e:
            scores.append(0.0)

    avg_score = sum(scores) / len(scores) if scores else 0
    return {
        "score": round(avg_score, 4),
        "runs": runs,
        "ticks": ticks,
        "individual_scores": [round(s, 4) for s in scores],
    }


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, indent=2))
