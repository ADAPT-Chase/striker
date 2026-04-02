#!/usr/bin/env python3
"""
🧪 NONLINEAR TRANSFORMATION EXPERIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The transformation bottleneck exists because all agent interactions are LINEAR:
  - Cultural blending: mine * (1-α) + theirs * α  (convex combination)
  - Signal decision: weighted sum of per-context probs
  - Reinforcement: old + lr (additive)

Linear operations preserve information but cannot CREATE it.
Transformation requires NONLINEAR interaction — XOR-like rules where
combining two inputs produces something neither input contained.

This experiment tests 4 conditions:
  1. BASELINE — current linear sim (control)
  2. XOR_SIGNALS — agents who hear 2+ different signals emit a XOR combination
  3. CONDITIONAL_CONTEXT — signal choice is multiplicative (context × received)
  4. THRESHOLD_GATES — agents only emit when multiple conditions AND together

From the literature review: Lizier framework shows modification requires
NONLINEAR interaction rules. Linear averaging/thresholds mathematically
cannot produce information transformation.
"""

import math
import sys
import json
import random
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, Optional, Callable

sys.path.insert(0, str(Path(__file__).parent))

import sim as emergence_sim
from triple_point_agents import TriplePointAnalyzer


# ── Nonlinear Intervention Functions ──────────────────────────────────

def _get_agent_context(agent, sim):
    """Determine agent's current context (mirrors sim logic)."""
    food_near = False
    danger_near = False
    friends_count = 0
    
    for f in sim.food_sources:
        dx = abs(agent.x - f.x)
        dy = abs(agent.y - f.y)
        if dx < emergence_sim.FOOD_DETECT_RADIUS and dy < emergence_sim.FOOD_DETECT_RADIUS:
            food_near = True
            break
    
    if sim.predator:
        p = sim.predator
        dx = abs(agent.x - p.x)
        dy = abs(agent.y - p.y)
        if dx < 15 and dy < 15:
            danger_near = True
    
    for other, d in sim._grid.query_radius(agent.x, agent.y, emergence_sim.ALIGNMENT_RADIUS):
        if other is not agent:
            friends_count += 1
    
    if danger_near:
        return 'danger_near'
    elif food_near:
        return 'food_near'
    elif friends_count >= 3:
        return 'friends_near'
    else:
        return 'alone'


def xor_signal_intervention(sim):
    """XOR-like signal combination.
    
    When an agent hears 2+ DIFFERENT signals from neighbors, it emits a signal
    that's the XOR of the received signals (mod NUM_SIGNALS). This creates
    genuinely new information — the output signal wasn't in either input.
    """
    for agent in sim.agents:
        if agent.signal_cooldown > 0:
            continue
        
        # Collect signals from nearby agents
        received = []
        for other, d in sim._grid.query_radius(agent.x, agent.y, emergence_sim.SIGNAL_RANGE):
            if other is agent:
                continue
            if other.current_signal >= 0:
                received.append(other.current_signal)
        
        if len(received) < 2:
            continue
        
        # Need DIFFERENT signals (diversity triggers computation)
        unique = set(received)
        if len(unique) < 2:
            continue
        
        # XOR combination: first two distinct signals
        sigs = list(unique)[:2]
        xor_signal = (sigs[0] ^ sigs[1]) % emergence_sim.NUM_SIGNALS
        
        # React with this new signal
        if random.random() < 0.6:
            agent.current_signal = xor_signal
            agent.signal_cooldown = random.randint(2, 5)
            agent.signals_sent += 1
            agent.last_context = 'xor_combination'
            agent.energy -= emergence_sim.SIGNAL_COST
            sim.logger.track_signal(sim.tick, xor_signal, 'xor_combination')
            sim.signal_pulses.append((agent.x, agent.y, xor_signal, 3))


def conditional_context_intervention(sim):
    """Multiplicative context × signal interaction.
    
    Instead of: P(emit s) = weight[s][context]  (linear)
    Use:        P(emit s) = weight[s][context] * gate(received_signals)
    
    The gate is XOR-like: if dominant received signal DIFFERS from candidate,
    boost probability. Same → suppress. Creates genuinely new outputs.
    """
    for agent in sim.agents:
        if agent.signal_cooldown > 0:
            continue
        
        # Get received signal distribution
        received_counts = Counter()
        for other, d in sim._grid.query_radius(agent.x, agent.y, emergence_sim.SIGNAL_RANGE):
            if other is agent:
                continue
            if other.current_signal >= 0:
                received_counts[other.current_signal] += 1
        
        if not received_counts:
            continue
        
        context = _get_agent_context(agent, sim)
        dominant_received = received_counts.most_common(1)[0][0]
        total_received = sum(received_counts.values())
        
        # Nonlinear: multiply context weight by XOR-like gate
        probs = []
        for s in range(emergence_sim.NUM_SIGNALS):
            base = agent.signal_weights[s].get(context, 0)
            
            # Gate: boost if DIFFERENT from dominant, suppress if same
            if s != dominant_received:
                gate = 1.0 + 0.5 * (received_counts.get(dominant_received, 0) / max(total_received, 1))
            else:
                gate = 0.4  # suppress same-as-received
            
            probs.append(base * gate)
        
        total = sum(probs)
        if total < 0.3:
            continue
        
        # Pick signal
        r = random.uniform(0, total)
        cumulative = 0
        for s in range(emergence_sim.NUM_SIGNALS):
            cumulative += probs[s]
            if r <= cumulative:
                agent.current_signal = s
                agent.signal_cooldown = random.randint(3, 8)
                agent.signals_sent += 1
                agent.last_context = context
                agent.energy -= emergence_sim.SIGNAL_COST
                sim.logger.track_signal(sim.tick, s, context)
                sim.signal_pulses.append((agent.x, agent.y, s, 3))
                break


def threshold_gate_intervention(sim):
    """AND-like threshold gates — nonlinear step functions.
    
    Agents only emit when MULTIPLE conditions fire simultaneously:
    - Social threshold: 2+ received signals
    - Context threshold: strong learned weight (>0.4)
    - Energy threshold: adequate energy (>2.0)
    
    Below threshold: silent. Above: decisive.
    This creates sharp nonlinear boundaries in signal space.
    """
    for agent in sim.agents:
        if agent.signal_cooldown > 0:
            continue
        
        # Count received signals
        received_count = 0
        for other, d in sim._grid.query_radius(agent.x, agent.y, emergence_sim.SIGNAL_RANGE):
            if other is agent:
                continue
            if other.current_signal >= 0:
                received_count += 1
        
        context = _get_agent_context(agent, sim)
        
        # Gate 1: social threshold
        social_gate = received_count >= 2
        
        # Gate 2: strong learned context-signal association
        best_signal = -1
        best_weight = 0
        for s in range(emergence_sim.NUM_SIGNALS):
            w = agent.signal_weights[s].get(context, 0)
            if w > best_weight:
                best_weight = w
                best_signal = s
        context_gate = best_weight > 0.4
        
        # Gate 3: energy
        energy_gate = agent.energy > 2.0
        
        # AND: all three must fire
        if social_gate and context_gate and energy_gate and best_signal >= 0:
            agent.current_signal = best_signal
            agent.signal_cooldown = random.randint(2, 6)
            agent.signals_sent += 1
            agent.last_context = context
            agent.energy -= emergence_sim.SIGNAL_COST
            sim.logger.track_signal(sim.tick, best_signal, context)
            sim.signal_pulses.append((agent.x, agent.y, best_signal, 3))


def combined_nonlinear_intervention(sim):
    """Best of all worlds: XOR + conditional + threshold combined.
    
    Each agent independently gets ONE of the three rules applied
    based on their position in the population (creates heterogeneity).
    """
    for i, agent in enumerate(sim.agents):
        role = i % 3
        if role == 0:
            # This agent uses XOR logic
            pass  # handled by calling xor for subset
        elif role == 1:
            pass  # conditional
        else:
            pass  # threshold
    
    # Actually, just apply all three — agents affected by whichever fires first
    xor_signal_intervention(sim)
    conditional_context_intervention(sim)
    threshold_gate_intervention(sim)


# ── Experiment Runner ──────────────────────────────────────────────────

def run_condition(name: str, intervention_fn: Optional[Callable] = None, 
                  num_agents: int = 60, ticks: int = 2000, seeds: int = 3) -> Dict:
    """Run one experimental condition, averaged over seeds."""
    
    all_summaries = []
    
    for seed in range(seeds):
        random.seed(42 + seed)
        
        sim = emergence_sim.Simulation(num_agents=num_agents)
        analyzer = TriplePointAnalyzer()
        
        for t in range(ticks):
            sim.step()
            
            # Apply nonlinear intervention AFTER normal step
            if intervention_fn is not None:
                intervention_fn(sim)
            
            analyzer.record_tick(sim.agents)
            
            if t % 500 == 0:
                print(f"  [seed {seed}] Tick {t}/{ticks} — {len(sim.agents)} agents")
        
        results = analyzer.analyze()
        
        if 'summary' in results:
            all_summaries.append(results['summary'])
            print(f"  [seed {seed}] Triple: {results['summary']['mean_triple']:.4f}, "
                  f"Transform: {results['summary']['mean_transformation']:.4f}")
        else:
            print(f"  [seed {seed}] Analysis failed: {results.get('error', 'unknown')}")
    
    # Average across seeds
    if not all_summaries:
        return {'name': name, 'memory': 0, 'transport': 0, 'transformation': 0, 'triple_point': 0}
    
    avg = {
        'name': name,
        'seeds': seeds,
        'memory': sum(s['mean_memory'] for s in all_summaries) / len(all_summaries),
        'transport': sum(s['mean_transport'] for s in all_summaries) / len(all_summaries),
        'transformation': sum(s['mean_transformation'] for s in all_summaries) / len(all_summaries),
        'triple_point': sum(s['mean_triple'] for s in all_summaries) / len(all_summaries),
        'max_triple': max(s['max_triple'] for s in all_summaries),
    }
    
    return avg


def main():
    print("=" * 70)
    print("🧪 NONLINEAR TRANSFORMATION EXPERIMENT")
    print("   Testing: can nonlinear interaction rules break the")
    print("   transformation bottleneck (currently ~0.45-0.55)?")
    print("=" * 70)
    
    conditions = [
        ("BASELINE", None),
        ("XOR_SIGNALS", xor_signal_intervention),
        ("CONDITIONAL_CTX", conditional_context_intervention),
        ("THRESHOLD_GATES", threshold_gate_intervention),
        ("COMBINED", combined_nonlinear_intervention),
    ]
    
    results = []
    
    for name, fn in conditions:
        print(f"\n{'─' * 60}")
        print(f"  Running: {name}")
        print(f"{'─' * 60}")
        
        result = run_condition(name, intervention_fn=fn, seeds=3)
        results.append(result)
        
        print(f"\n  → Memory:         {result['memory']:.4f}")
        print(f"  → Transport:      {result['transport']:.4f}")
        print(f"  → Transformation: {result['transformation']:.4f}")
        print(f"  → Triple-point:   {result['triple_point']:.4f}")
    
    # Summary table
    print("\n\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Condition':<20} {'Memory':>8} {'Transport':>10} {'Transform':>10} {'Triple':>8} {'Max':>8}")
    print("─" * 70)
    
    for r in results:
        print(f"{r['name']:<20} {r['memory']:>8.4f} {r['transport']:>10.4f} "
              f"{r['transformation']:>10.4f} {r['triple_point']:>8.4f} {r.get('max_triple', 0):>8.4f}")
    
    # Analysis vs baseline
    baseline = results[0]
    print(f"\n\n📊 DELTA vs BASELINE ({baseline['name']}):")
    print("─" * 50)
    for r in results[1:]:
        t_diff = r['transformation'] - baseline['transformation']
        tp_diff = r['triple_point'] - baseline['triple_point']
        m_diff = r['memory'] - baseline['memory']
        t_dir = "↑" if t_diff > 0 else "↓"
        tp_dir = "↑" if tp_diff > 0 else "↓"
        print(f"  {r['name']}:")
        print(f"    Transform: {t_diff:+.4f} {t_dir}  |  Memory: {m_diff:+.4f}  |  Triple: {tp_diff:+.4f} {tp_dir}")
    
    # Save results
    output = {
        'experiment': 'nonlinear_transformation',
        'hypothesis': 'Nonlinear interaction rules break the transformation bottleneck',
        'conditions': [
            {k: v for k, v in r.items()} for r in results
        ],
    }
    
    with open('nonlinear_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n\nResults saved to nonlinear_results.json")
    return results


if __name__ == '__main__':
    main()
