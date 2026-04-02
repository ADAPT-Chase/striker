#!/usr/bin/env python3
"""
🧠 MEMORY LOCUS EXPERIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━

The paradox: cultural transmission INCREASES transformation but DECREASES 
population-level temporal memory. Triple-point score is actually LOWER 
with culture (0.47) than without (0.51).

Hypothesis: Culture creates DISTRIBUTED memory that replaces INDIVIDUAL memory.
When agents copy successful neighbors, the group remembers even as individuals
change. The temporal MI metric measures fixed-position memory (does this cell 
maintain state?) but culture creates SOCIAL memory (does the population maintain
signal-context mappings even as individual agents change their behavior?).

This experiment measures:
1. Individual consistency — does each agent maintain stable signal-context maps?
2. Population consistency — does the group maintain stable signal-context maps?
3. Turnover-resilience — when agents die and are replaced, does knowledge persist?
4. Memory TYPE — individual (high per-agent MI) vs distributed (high pop MI, low per-agent MI)

If culture creates distributed memory, we should see:
- WITH culture: low individual consistency, high population consistency
- WITHOUT culture: higher individual consistency, lower population consistency
"""

import math
import sys
import json
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))


def agent_signal_distribution(agent, num_signals=4):
    """Get this agent's signal emission weights as a distribution per context."""
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    dists = {}
    for ctx in contexts:
        weights = []
        for s in range(num_signals):
            w = agent.signal_weights.get(s, {}).get(ctx, 0.0)
            weights.append(max(0.0, w))
        total = sum(weights)
        if total > 0:
            dists[ctx] = [w / total for w in weights]
        else:
            dists[ctx] = [1.0 / num_signals] * num_signals
    return dists


def kl_divergence(p, q, epsilon=1e-10):
    """KL(p || q) — how different q is from p."""
    return sum(pi * math.log2((pi + epsilon) / (qi + epsilon)) 
               for pi, qi in zip(p, q) if pi > epsilon)


def jensen_shannon(p, q):
    """Symmetric version of KL."""
    m = [(pi + qi) / 2 for pi, qi in zip(p, q)]
    return (kl_divergence(p, m) + kl_divergence(q, m)) / 2


def population_signal_consensus(agents, num_signals=4):
    """
    Measure how much the population agrees on signal-context mappings.
    Returns {context: (dominant_signal, agreement_ratio, entropy)}
    """
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    results = {}
    
    for ctx in contexts:
        # Collect each agent's preferred signal for this context
        preferred = []
        for a in agents:
            weights = []
            for s in range(num_signals):
                w = a.signal_weights.get(s, {}).get(ctx, 0.0)
                weights.append(max(0.0, w))
            if sum(weights) > 0:
                preferred.append(max(range(num_signals), key=lambda s: weights[s]))
        
        if not preferred:
            results[ctx] = {'dominant': -1, 'agreement': 0.0, 'entropy': 0.0}
            continue
            
        counts = Counter(preferred)
        total = len(preferred)
        dominant = counts.most_common(1)[0]
        agreement = dominant[1] / total
        
        # Entropy of preference distribution
        probs = [c / total for c in counts.values()]
        ent = -sum(p * math.log2(p) for p in probs if p > 0)
        max_ent = math.log2(num_signals) if num_signals > 1 else 1.0
        
        results[ctx] = {
            'dominant': dominant[0],
            'agreement': round(agreement, 4),
            'entropy': round(ent / max_ent, 4),  # normalized
        }
    
    return results


class MemoryLocusTracker:
    """Track where memory lives — in individuals or in the collective."""
    
    def __init__(self, snapshot_interval=50, num_signals=4):
        self.snapshot_interval = snapshot_interval
        self.num_signals = num_signals
        
        # Snapshots of individual agent distributions over time
        self.individual_snapshots = []  # list of {agent_id: {ctx: dist}}
        self.population_consensus = []  # list of consensus measurements
        self.agent_lifetimes = defaultdict(int)  # agent_id -> ticks alive
        self.generation_tracker = defaultdict(list)  # generation -> [agent_ids]
        self.tick = 0
        
    def record(self, agents):
        """Record one tick."""
        self.tick += 1
        
        for a in agents:
            self.agent_lifetimes[a.id] += 1
            self.generation_tracker[a.generation].append(a.id)
        
        if self.tick % self.snapshot_interval == 0:
            # Snapshot individual distributions
            snapshot = {}
            for a in agents:
                snapshot[a.id] = agent_signal_distribution(a, self.num_signals)
            self.individual_snapshots.append(snapshot)
            
            # Snapshot population consensus
            self.population_consensus.append(
                population_signal_consensus(agents, self.num_signals)
            )
    
    def analyze(self) -> Dict:
        """Analyze where memory resides."""
        if len(self.individual_snapshots) < 3:
            return {"error": "Not enough snapshots"}
        
        results = {}
        
        # 1. INDIVIDUAL CONSISTENCY
        # How much does each agent's signal distribution change between snapshots?
        individual_drifts = []
        for i in range(1, len(self.individual_snapshots)):
            prev = self.individual_snapshots[i - 1]
            curr = self.individual_snapshots[i]
            common = set(prev.keys()) & set(curr.keys())
            
            for aid in common:
                for ctx in ['food_near', 'danger_near', 'friends_near', 'alone']:
                    if ctx in prev[aid] and ctx in curr[aid]:
                        js = jensen_shannon(prev[aid][ctx], curr[aid][ctx])
                        individual_drifts.append(js)
        
        if individual_drifts:
            mean_drift = sum(individual_drifts) / len(individual_drifts)
            individual_consistency = 1.0 - min(1.0, mean_drift * 4)  # scale: 0=chaotic, 1=stable
        else:
            individual_consistency = 0.0
        
        results['individual_consistency'] = round(individual_consistency, 4)
        
        # 2. POPULATION CONSISTENCY
        # How stable are the population-level consensus mappings?
        pop_drifts = []
        for i in range(1, len(self.population_consensus)):
            prev = self.population_consensus[i - 1]
            curr = self.population_consensus[i]
            for ctx in ['food_near', 'danger_near', 'friends_near', 'alone']:
                if ctx in prev and ctx in curr:
                    # Did the dominant signal change?
                    if prev[ctx]['dominant'] == curr[ctx]['dominant'] and prev[ctx]['dominant'] >= 0:
                        pop_drifts.append(0.0)  # stable
                    else:
                        pop_drifts.append(1.0)  # changed
        
        if pop_drifts:
            population_consistency = 1.0 - (sum(pop_drifts) / len(pop_drifts))
        else:
            population_consistency = 0.0
        
        results['population_consistency'] = round(population_consistency, 4)
        
        # 3. AGREEMENT STRENGTH
        # How strongly does the population agree at each snapshot?
        agreements = []
        entropies = []
        for snap in self.population_consensus:
            for ctx, data in snap.items():
                agreements.append(data['agreement'])
                entropies.append(data['entropy'])
        
        results['mean_agreement'] = round(sum(agreements) / len(agreements), 4) if agreements else 0.0
        results['mean_preference_entropy'] = round(sum(entropies) / len(entropies), 4) if entropies else 0.0
        
        # 4. TURNOVER RESILIENCE
        # How many generations contribute to the population?
        unique_gens = set()
        for snap in self.individual_snapshots[-3:]:  # last 3 snapshots
            for aid in snap:
                # Find this agent's generation
                for gen, aids in self.generation_tracker.items():
                    if aid in aids:
                        unique_gens.add(gen)
                        break
        
        results['active_generations'] = len(unique_gens)
        results['total_agents_tracked'] = len(self.agent_lifetimes)
        
        # 5. MEMORY LOCUS CLASSIFICATION
        ind = results['individual_consistency']
        pop = results['population_consistency']
        
        if ind > 0.6 and pop > 0.6:
            locus = "REDUNDANT"   # both individual and group remember
            desc = "Memory is stored at both levels — robust but potentially rigid"
        elif ind < 0.4 and pop > 0.6:
            locus = "DISTRIBUTED"  # group remembers, individuals are fluid
            desc = "Social memory — the group maintains knowledge even as individuals change"
        elif ind > 0.6 and pop < 0.4:
            locus = "INDIVIDUAL"   # individuals remember, group is disorganized
            desc = "Each agent remembers its own mappings but there's no shared convention"
        elif ind > 0.4 and pop < 0.6:
            locus = "INDIVIDUAL-BIASED"
            desc = "Memory primarily in individuals with weak social consensus"
        elif ind < 0.4 and pop < 0.4:
            locus = "AMNESIA"      # nobody remembers
            desc = "Neither individuals nor the group maintain stable signal mappings"
        else:
            locus = "MIXED"
            desc = "Memory distributed across both levels without clear dominance"
        
        results['memory_locus'] = locus
        results['memory_description'] = desc
        
        return results


def run_experiment(ticks=3000, num_agents=60, use_cultural=True,
                   use_convention=True, label="") -> Dict:
    """Run emergence sim and track where memory resides."""
    import sim as emergence_sim
    
    print(f"\n🧠 Memory Locus Experiment: {label}")
    print(f"   Agents: {num_agents}, Ticks: {ticks}")
    print(f"   Cultural: {use_cultural}, Convention: {use_convention}")
    
    s = emergence_sim.Simulation(
        num_agents=num_agents,
        use_seasons=False,
        use_predator=False,
    )
    
    if hasattr(s, 'cultural_transmission'):
        s.cultural_transmission = use_cultural
    if hasattr(s, 'convention_enforcement'):
        s.convention_enforcement = use_convention
    
    tracker = MemoryLocusTracker(snapshot_interval=30)
    
    # Also import triple point for comparison
    from triple_point_agents import TriplePointAnalyzer
    tp_analyzer = TriplePointAnalyzer()
    
    for tick in range(ticks):
        s.step()
        tracker.record(s.agents)
        tp_analyzer.record_tick(s.agents)
        
        if tick > 0 and tick % 1000 == 0:
            print(f"  Tick {tick}/{ticks} — {len(s.agents)} agents")
    
    memory_results = tracker.analyze()
    tp_results = tp_analyzer.analyze()
    
    print(f"\n{'='*60}")
    print(f"  MEMORY LOCUS: {memory_results.get('memory_locus', '?')}")
    print(f"  {memory_results.get('memory_description', '')}")
    print(f"  ─────────────────────────")
    print(f"  Individual consistency: {memory_results.get('individual_consistency', 0):.4f}")
    print(f"  Population consistency: {memory_results.get('population_consistency', 0):.4f}")
    print(f"  Mean agreement:         {memory_results.get('mean_agreement', 0):.4f}")
    print(f"  Preference entropy:     {memory_results.get('mean_preference_entropy', 0):.4f}")
    print(f"  Active generations:     {memory_results.get('active_generations', 0)}")
    
    if 'summary' in tp_results:
        tp = tp_results['summary']
        print(f"\n  Triple-Point Comparison:")
        print(f"    Memory (temporal MI):   {tp['mean_memory']:.4f}")
        print(f"    Transport:              {tp['mean_transport']:.4f}")
        print(f"    Transformation:         {tp['mean_transformation']:.4f}")
        print(f"    Triple score:           {tp['mean_triple']:.4f}")
    print(f"{'='*60}")
    
    return {
        "memory_locus": memory_results,
        "triple_point": tp_results.get("summary", {}),
        "label": label,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("MEMORY LOCUS: Where does knowledge live?")
    print("=" * 60)
    
    # Condition 1: Full culture
    r_culture = run_experiment(
        ticks=3000, num_agents=60,
        use_cultural=True, use_convention=True,
        label="WITH culture + convention"
    )
    
    # Condition 2: Convention only (conformity pressure without copying)
    r_convention = run_experiment(
        ticks=3000, num_agents=60,
        use_cultural=False, use_convention=True,
        label="Convention ONLY (no copying)"
    )
    
    # Condition 3: Cultural copying only (no convention pressure)
    r_copying = run_experiment(
        ticks=3000, num_agents=60,
        use_cultural=True, use_convention=False,
        label="Copying ONLY (no convention)"
    )
    
    # Condition 4: Neither
    r_baseline = run_experiment(
        ticks=3000, num_agents=60,
        use_cultural=False, use_convention=False,
        label="BASELINE (no culture)"
    )
    
    # Summary comparison
    print("\n\n")
    print("=" * 70)
    print("COMPARATIVE SUMMARY: Where Does Memory Live?")
    print("=" * 70)
    
    conditions = [
        ("Culture+Convention", r_culture),
        ("Convention Only", r_convention),
        ("Copying Only", r_copying),
        ("Baseline", r_baseline),
    ]
    
    header = f"{'Condition':22s} | {'Ind.':>6s} | {'Pop.':>6s} | {'Agree':>6s} | {'Locus':>14s} | {'Triple':>7s}"
    print(header)
    print("-" * len(header))
    
    for name, r in conditions:
        ml = r['memory_locus']
        tp = r['triple_point']
        print(f"{name:22s} | {ml.get('individual_consistency',0):6.4f} | "
              f"{ml.get('population_consistency',0):6.4f} | "
              f"{ml.get('mean_agreement',0):6.4f} | "
              f"{ml.get('memory_locus','?'):>14s} | "
              f"{tp.get('mean_triple',0):7.4f}")
    
    # Save results
    output = {name: r for name, r in conditions}
    Path("memory_locus_results.json").write_text(json.dumps(output, indent=2))
    print("\nResults saved to memory_locus_results.json")
    
    # Interpretation
    print("\n" + "=" * 70)
    print("INTERPRETATION")
    print("=" * 70)
    
    culture_ml = r_culture['memory_locus']
    baseline_ml = r_baseline['memory_locus']
    
    if (culture_ml.get('individual_consistency', 1) < baseline_ml.get('individual_consistency', 0)
        and culture_ml.get('population_consistency', 0) > baseline_ml.get('population_consistency', 1)):
        print("✅ HYPOTHESIS CONFIRMED: Culture shifts memory from individual to distributed.")
        print("   Individual agents are less consistent (they copy and change),")
        print("   but the population maintains stable mappings (social memory).")
        print("   The triple-point 'memory' metric penalizes this because it measures")
        print("   temporal MI at fixed positions, not distributed consensus.")
    elif (culture_ml.get('population_consistency', 0) > baseline_ml.get('population_consistency', 1)):
        print("🔶 PARTIAL: Culture improves population consistency but individual effect unclear.")
    else:
        print("❌ HYPOTHESIS NOT CONFIRMED: Culture doesn't clearly shift memory locus.")
        print("   Need to investigate further — maybe the metric is wrong,")
        print("   or maybe culture operates differently than expected.")
