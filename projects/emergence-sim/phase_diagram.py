#!/usr/bin/env python3
"""
🌡️ PHASE DIAGRAM: Environmental Pressure vs. Collective Computation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The day-006 insight: too little pressure → no language, too much → extinction,
just right → computation. This is Langton's lambda for collective behavior.

This experiment sweeps across a pressure gradient and measures:
  • Computation score (TMI × StateEntropy × (1 + AIS))
  • NMI (signal-context mutual information)
  • Population survival rate
  • Signal differentiation (do different signals mean different things?)

The "pressure" dial combines:
  • Winter severity (energy drain multiplier)
  • Season food scarcity
  • Season length (shorter = more volatile)

Output: a phase diagram showing where computation lives.
"""

import sys
import os
import math
import json
import time
from collections import Counter, defaultdict
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim import (Simulation, SEASON_FOOD_RATES, SEASON_FOOD_CAPS, 
                 SEASON_DRAIN_MULT, SEASON_LENGTH, SIGNAL_NAMES, NUM_SIGNALS,
                 WIDTH, HEIGHT)
from collective_computation import CollectiveComputationTracker


def run_trial(pressure_level, ticks=2500, num_agents=60, trial_id=0):
    """
    Run one trial at a given pressure level.
    
    Pressure level 0.0 = paradise (no seasons effectively)
    Pressure level 1.0 = standard seasons
    Pressure level 2.0+ = harsh (brutal winters, scarce food)
    
    We parameterize pressure as a single scalar that scales:
      - Winter drain multiplier: base 4.0 → 4.0 * pressure
      - Winter food cap: base 3 → max(1, 3 / pressure)
      - Autumn drain: scales with pressure too
      - Spring bounty: inversely scales (less generous at high pressure)
    """
    sim = Simulation(num_agents=num_agents, use_predator=False, use_seasons=True)
    
    # Override season parameters based on pressure level
    # Pressure 0 = uniform abundance, Pressure 1 = standard, Pressure 2+ = brutal
    p = max(0.01, pressure_level)
    
    # Food spawn rates per season [spring, summer, autumn, winter]
    # At p=0: all seasons are spring-like
    # At p=1: standard values
    # At p=2: even spring is scarce
    base_rates = [0.22, 0.12, 0.04, 0.008]
    base_caps = [18, 12, 6, 3]
    base_drain = [0.5, 1.0, 2.0, 4.0]
    
    # Interpolate: at p=0, all values → spring values; at p=1, standard; at p>1, amplified
    if p <= 1.0:
        # Blend toward uniform (spring) as p→0
        blend = p  # 0=all spring, 1=standard
        adjusted_rates = [base_rates[0] * (1 - blend) + base_rates[i] * blend for i in range(4)]
        adjusted_caps = [int(base_caps[0] * (1 - blend) + base_caps[i] * blend) for i in range(4)]
        adjusted_drain = [base_drain[0] * (1 - blend) + base_drain[i] * blend for i in range(4)]
    else:
        # Beyond standard: amplify the contrast
        excess = p - 1.0
        adjusted_rates = [max(0.001, base_rates[i] * (1 - excess * 0.3)) for i in range(4)]
        adjusted_caps = [max(1, int(base_caps[i] * (1 - excess * 0.25))) for i in range(4)]
        adjusted_drain = [base_drain[i] * (1 + excess * 0.8) for i in range(4)]
    
    # Monkey-patch the sim's season parameters
    # We need to patch the module-level constants that step() reads
    import sim as sim_module
    orig_rates = sim_module.SEASON_FOOD_RATES
    orig_caps = sim_module.SEASON_FOOD_CAPS
    orig_drain = sim_module.SEASON_DRAIN_MULT
    
    sim_module.SEASON_FOOD_RATES = adjusted_rates
    sim_module.SEASON_FOOD_CAPS = adjusted_caps
    sim_module.SEASON_DRAIN_MULT = adjusted_drain
    
    tracker = CollectiveComputationTracker(NUM_SIGNALS)
    
    # Track survival and population over time
    pop_timeline = []
    extinction_tick = None
    
    try:
        for t in range(ticks):
            sim.step()
            
            if len(sim.agents) == 0:
                extinction_tick = sim.tick
                break
            
            # Record every 2nd tick (save memory, still fine-grained)
            if t % 2 == 0:
                nmi = None
                if sim.logger.info_analyzer:
                    m = sim.logger.info_analyzer.get_cumulative_metrics()
                    if m['total_obs'] > 20:
                        nmi = m['nmi']
                tracker.record(sim.tick, sim.agents, nmi)
            
            if t % 100 == 0:
                pop_timeline.append((sim.tick, len(sim.agents)))
    finally:
        # Restore original constants
        sim_module.SEASON_FOOD_RATES = orig_rates
        sim_module.SEASON_FOOD_CAPS = orig_caps
        sim_module.SEASON_DRAIN_MULT = orig_drain
    
    # Compute results
    if len(tracker.vector_history) < 30:
        # Not enough data (probably early extinction)
        return {
            'pressure': pressure_level,
            'trial': trial_id,
            'survived': False,
            'extinction_tick': extinction_tick,
            'computation_score': 0,
            'temporal_mi': 0,
            'ais': 0,
            'state_entropy': 0,
            'nmi': 0,
            'n_states': 0,
            'final_pop': 0,
            'avg_pop': 0,
            'signal_differentiation': 0,
            'max_generation': sim.max_generation,
        }
    
    cs = tracker.computation_score()
    
    # Measure signal differentiation: do different signals map to different contexts?
    sig_ctx = defaultdict(lambda: Counter())
    if sim.logger.info_analyzer:
        # Use the raw observation data
        for sig in range(NUM_SIGNALS):
            for ctx, count in sim.logger.signal_context_history[sig].items():
                sig_ctx[sig][ctx] = count
    
    # Signal differentiation = how different are the context distributions across signals
    # High = each signal has its own meaning. Low = all signals mean the same thing.
    differentiation = 0
    if sig_ctx:
        contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
        sig_profiles = []
        for s in range(NUM_SIGNALS):
            total = sum(sig_ctx[s].values())
            if total > 5:
                profile = tuple(sig_ctx[s].get(c, 0) / total for c in contexts)
                sig_profiles.append(profile)
        
        if len(sig_profiles) >= 2:
            # Average pairwise distance between signal profiles
            dists = []
            for i in range(len(sig_profiles)):
                for j in range(i+1, len(sig_profiles)):
                    d = math.sqrt(sum((a - b)**2 for a, b in zip(sig_profiles[i], sig_profiles[j])))
                    dists.append(d)
            differentiation = sum(dists) / len(dists) if dists else 0
    
    avg_pop = sum(p for _, p in pop_timeline) / len(pop_timeline) if pop_timeline else 0
    
    return {
        'pressure': pressure_level,
        'trial': trial_id,
        'survived': extinction_tick is None,
        'extinction_tick': extinction_tick,
        'computation_score': cs['score'],
        'temporal_mi': cs['temporal_mi'],
        'ais': cs['ais'],
        'state_entropy': cs['state_entropy'],
        'nmi': cs['nmi'] if cs['nmi'] else 0,
        'n_states': cs['n_states'],
        'final_pop': len(sim.agents),
        'avg_pop': avg_pop,
        'signal_differentiation': differentiation,
        'max_generation': sim.max_generation,
    }


def run_phase_sweep(pressure_levels=None, trials_per_level=3, ticks=2500, num_agents=60):
    """Sweep across pressure levels and collect results."""
    if pressure_levels is None:
        # 12 levels from paradise to hell
        pressure_levels = [0.0, 0.15, 0.3, 0.5, 0.7, 0.85, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
    
    results = []
    total = len(pressure_levels) * trials_per_level
    done = 0
    
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║  PHASE DIAGRAM: Environmental Pressure vs Computation      ║")
    print(f"║  {len(pressure_levels)} pressure levels × {trials_per_level} trials = {total} runs @ {ticks} ticks each   ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print()
    
    for p in pressure_levels:
        level_results = []
        for trial in range(trials_per_level):
            done += 1
            t0 = time.time()
            result = run_trial(p, ticks=ticks, num_agents=num_agents, trial_id=trial)
            elapsed = time.time() - t0
            level_results.append(result)
            results.append(result)
            
            status = "✓" if result['survived'] else f"✗ (died@{result['extinction_tick']})"
            print(f"  [{done:>2}/{total}] p={p:.2f} t{trial} | {status:>15} | "
                  f"score={result['computation_score']:.4f} | "
                  f"NMI={result['nmi']:.3f} | "
                  f"diff={result['signal_differentiation']:.3f} | "
                  f"{elapsed:.1f}s")
        
        # Average for this level
        survived = sum(1 for r in level_results if r['survived'])
        avg_score = sum(r['computation_score'] for r in level_results) / trials_per_level
        avg_nmi = sum(r['nmi'] for r in level_results) / trials_per_level
        print(f"  ── p={p:.2f} avg: score={avg_score:.4f}, NMI={avg_nmi:.3f}, "
              f"survived={survived}/{trials_per_level} ──")
        print()
    
    return results


def render_phase_diagram(results, pressure_levels=None):
    """Render an ASCII phase diagram from results."""
    if pressure_levels is None:
        pressure_levels = sorted(set(r['pressure'] for r in results))
    
    # Aggregate by pressure level
    aggregated = {}
    for p in pressure_levels:
        level_results = [r for r in results if r['pressure'] == p]
        aggregated[p] = {
            'computation_score': sum(r['computation_score'] for r in level_results) / len(level_results),
            'nmi': sum(r['nmi'] for r in level_results) / len(level_results),
            'survival_rate': sum(1 for r in level_results if r['survived']) / len(level_results),
            'avg_pop': sum(r['avg_pop'] for r in level_results) / len(level_results),
            'signal_diff': sum(r['signal_differentiation'] for r in level_results) / len(level_results),
            'temporal_mi': sum(r['temporal_mi'] for r in level_results) / len(level_results),
            'ais': sum(r['ais'] for r in level_results) / len(level_results),
            'max_gen': max(r['max_generation'] for r in level_results),
        }
    
    lines = []
    lines.append("")
    lines.append("=" * 72)
    lines.append("  PHASE DIAGRAM: The Goldilocks Zone of Collective Computation")
    lines.append("  Environmental Pressure → Computation Score")
    lines.append("=" * 72)
    lines.append("")
    
    # Find max score for scaling
    max_score = max(a['computation_score'] for a in aggregated.values())
    max_score = max(max_score, 0.01)
    
    # Bar chart
    bar_width = 40
    lines.append("  Pressure │ Computation Score")
    lines.append("  ─────────┼" + "─" * (bar_width + 15))
    
    sparkchars = ' ░▒▓█'
    
    for p in pressure_levels:
        a = aggregated[p]
        score = a['computation_score']
        bar_len = int((score / max_score) * bar_width)
        
        # Color the bar based on survival
        if a['survival_rate'] == 0:
            bar = '✗' * max(1, bar_len)  # dead
            label = "EXTINCT"
        elif score < 0.1:
            bar = '░' * max(1, bar_len)
            label = f"{score:.3f}"
        elif score < 0.5:
            bar = '▒' * max(1, bar_len)
            label = f"{score:.3f}"
        elif score < 1.0:
            bar = '▓' * max(1, bar_len)
            label = f"{score:.3f}"
        else:
            bar = '█' * max(1, bar_len)
            label = f"{score:.3f}"
        
        lines.append(f"  {p:>7.2f} │ {bar} {label}")
    
    lines.append(f"  ─────────┼" + "─" * (bar_width + 15))
    lines.append(f"           │ ░=proto  ▒=emerging  ▓=computing  █=rich  ✗=extinct")
    lines.append("")
    
    # NMI chart  
    max_nmi = max(a['nmi'] for a in aggregated.values())
    max_nmi = max(max_nmi, 0.01)
    
    lines.append("  Pressure │ Signal-Context Correlation (NMI)")
    lines.append("  ─────────┼" + "─" * (bar_width + 15))
    
    for p in pressure_levels:
        a = aggregated[p]
        nmi = a['nmi']
        bar_len = int((nmi / max_nmi) * bar_width)
        bar = '▓' * max(0, bar_len) if a['survival_rate'] > 0 else '✗'
        lines.append(f"  {p:>7.2f} │ {bar} {nmi:.3f}")
    
    lines.append("")
    
    # Signal differentiation chart
    max_diff = max(a['signal_diff'] for a in aggregated.values())
    max_diff = max(max_diff, 0.01)
    
    lines.append("  Pressure │ Signal Differentiation (unique meanings)")
    lines.append("  ─────────┼" + "─" * (bar_width + 15))
    
    for p in pressure_levels:
        a = aggregated[p]
        diff = a['signal_diff']
        bar_len = int((diff / max_diff) * bar_width)
        bar = '▓' * max(0, bar_len) if a['survival_rate'] > 0 else '✗'
        lines.append(f"  {p:>7.2f} │ {bar} {diff:.3f}")
    
    lines.append("")
    
    # Summary table
    lines.append("  ┌─────────┬──────────┬─────────┬─────────┬─────────┬──────────┬─────────┐")
    lines.append("  │Pressure │  Score   │   TMI   │   AIS   │   NMI   │ Sig.Diff │Survival │")
    lines.append("  ├─────────┼──────────┼─────────┼─────────┼─────────┼──────────┼─────────┤")
    
    for p in pressure_levels:
        a = aggregated[p]
        surv = f"{a['survival_rate']:.0%}"
        lines.append(
            f"  │  {p:>5.2f}  │ {a['computation_score']:>8.4f} │ {a['temporal_mi']:>7.3f} │"
            f" {a['ais']:>7.3f} │ {a['nmi']:>7.3f} │ {a['signal_diff']:>8.3f} │ {surv:>7s} │"
        )
    
    lines.append("  └─────────┴──────────┴─────────┴─────────┴─────────┴──────────┴─────────┘")
    lines.append("")
    
    # Find the peak
    peak_p = max(pressure_levels, key=lambda p: aggregated[p]['computation_score'])
    peak_score = aggregated[peak_p]['computation_score']
    
    lines.append(f"  PEAK COMPUTATION: pressure={peak_p:.2f}, score={peak_score:.4f}")
    lines.append("")
    
    # Interpretation
    lines.append("  ── INTERPRETATION ──")
    lines.append("")
    
    # Identify zones
    low_zone = [p for p in pressure_levels if aggregated[p]['computation_score'] < 0.1 and aggregated[p]['survival_rate'] > 0]
    comp_zone = [p for p in pressure_levels if aggregated[p]['computation_score'] >= 0.1]
    dead_zone = [p for p in pressure_levels if aggregated[p]['survival_rate'] == 0]
    
    if low_zone:
        lines.append(f"  ORDER zone (p={min(low_zone):.2f}-{max(low_zone):.2f}):")
        lines.append(f"    Too little pressure. Agents survive easily but don't differentiate")
        lines.append(f"    their signals. No need to communicate → no language → no computation.")
        lines.append("")
    
    if comp_zone:
        lines.append(f"  COMPUTATION zone (p={min(comp_zone):.2f}-{max(comp_zone):.2f}):")
        lines.append(f"    The Goldilocks zone. Enough pressure to force signal specialization,")
        lines.append(f"    enough stability for conventions to propagate. Language lives here.")
        lines.append("")
    
    if dead_zone:
        lines.append(f"  CHAOS/DEATH zone (p={min(dead_zone):.2f}+):")
        lines.append(f"    Too much pressure. Populations collapse before conventions stabilize.")
        lines.append(f"    Like Rule 30: complexity without structure. Information is destroyed.")
        lines.append("")
    
    lines.append("  This is Langton's lambda for collective behavior:")
    lines.append("    λ too low  → frozen order (Rule 0)")
    lines.append("    λ optimal  → computation  (Rule 110)")
    lines.append("    λ too high → chaos/death   (Rule 30)")
    lines.append("")
    lines.append("  The environmental pressure parameter IS the lambda of the collective.")
    lines.append("")
    
    return "\n".join(lines), aggregated


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Phase diagram experiment")
    parser.add_argument('--ticks', type=int, default=2500, help="Ticks per trial")
    parser.add_argument('--trials', type=int, default=3, help="Trials per pressure level")
    parser.add_argument('--agents', type=int, default=60, help="Agents per trial")
    parser.add_argument('--quick', action='store_true', help="Quick mode: fewer levels, shorter runs")
    args = parser.parse_args()
    
    if args.quick:
        levels = [0.0, 0.3, 0.6, 0.85, 1.0, 1.3, 1.6, 2.0]
        ticks = 1500
        trials = 2
    else:
        levels = [0.0, 0.15, 0.3, 0.5, 0.7, 0.85, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
        ticks = args.ticks
        trials = args.trials
    
    results = run_phase_sweep(
        pressure_levels=levels,
        trials_per_level=trials,
        ticks=ticks,
        num_agents=args.agents
    )
    
    diagram, aggregated = render_phase_diagram(results, levels)
    print(diagram)
    
    # Save results
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phase_results.json')
    with open(output_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'params': {'ticks': ticks, 'trials': trials, 'agents': args.agents},
            'results': results,
            'aggregated': {str(k): v for k, v in aggregated.items()},
        }, f, indent=2)
    print(f"Results saved to {output_path}")
    
    # Save diagram as markdown
    diagram_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PHASE_DIAGRAM.md')
    with open(diagram_path, 'w') as f:
        f.write(f"# Phase Diagram: Environmental Pressure vs Collective Computation\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(f"```\n{diagram}\n```\n")
    print(f"Diagram saved to {diagram_path}")
