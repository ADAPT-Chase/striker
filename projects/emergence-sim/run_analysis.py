#!/usr/bin/env python3
"""
Run the emergence sim with full information-theoretic analysis.
Outputs a rigorous assessment of whether real communication emerges.
"""
import sys
sys.path.insert(0, '.')
from sim import Simulation, SIGNAL_NAMES, NUM_SIGNALS, SEASONS
from info_theory import SignalAnalyzer, PopulationDynamicsAnalyzer

# Run 3 trials with different conditions
TICKS = 2000
CONFIGS = [
    {'name': 'Baseline (no predator, no seasons)', 'predator': False, 'seasons': False},
    {'name': 'Predator only', 'predator': True, 'seasons': False},
    {'name': 'Full (predator + seasons)', 'predator': True, 'seasons': True},
]

print("╔══════════════════════════════════════════════════════════════╗")
print("║  EMERGENCE COMMUNICATION ANALYSIS — Information Theory      ║")
print("║  Testing whether agents develop genuine language            ║")
print("╚══════════════════════════════════════════════════════════════╝")
print()

results = []

for config in CONFIGS:
    print(f"━━━ Trial: {config['name']} ━━━")
    sim = Simulation(num_agents=50, use_predator=config['predator'], use_seasons=config['seasons'])
    analyzer = SignalAnalyzer()
    pop_analyzer = PopulationDynamicsAnalyzer()

    # Hook into simulation: track every signal emission
    original_decide = sim._agent_decide_signal.__func__ if hasattr(sim._agent_decide_signal, '__func__') else None

    extinct = False
    for t in range(TICKS):
        # Before step, note signal states
        pre_signals = {a.id: a.current_signal for a in sim.agents}

        sim.step()

        if len(sim.agents) == 0:
            print(f"  ☠ All agents perished at tick {sim.tick}")
            extinct = True
            break

        # After step, detect new signal emissions
        for a in sim.agents:
            if a.current_signal >= 0 and (a.id not in pre_signals or pre_signals.get(a.id, -1) != a.current_signal):
                analyzer.observe(a.current_signal, a.last_context or 'unknown')

        # Record population dynamics every 10 ticks
        if t % 10 == 0:
            pop_analyzer.record(sim.tick, sim.agents, sim.current_season)

        # Progress
        if t % 500 == 0 and t > 0:
            m = analyzer.get_cumulative_metrics()
            print(f"  tick {t:>5}: pop={len(sim.agents):>3}, NMI={m['nmi']:.3f}, "
                  f"I(S;C)={m['mutual_info']:.3f} bits, obs={m['total_obs']}")

    if not extinct:
        print(f"  ✓ Completed {TICKS} ticks, final pop: {len(sim.agents)}")

    # Full analysis
    print()
    print(analyzer.interpretation())

    # Signal specificity
    print()
    spec = analyzer.signal_specificity()
    if spec:
        print("  Signal specificity (1 = always same context, 0 = random):")
        for name, data in sorted(spec.items()):
            bar = '█' * int(data['specificity'] * 20) + '░' * (20 - int(data['specificity'] * 20))
            print(f"    {name} [{bar}] {data['specificity']:.3f}")

    # Context predictability
    pred = analyzer.context_predictability()
    if pred:
        print()
        print("  Context predictability (1 = one signal per context, 0 = random):")
        for ctx, data in sorted(pred.items()):
            bar = '█' * int(data['predictability'] * 20) + '░' * (20 - int(data['predictability'] * 20))
            print(f"    {ctx:15s} [{bar}] {data['predictability']:.3f} → {data['dominant_signal']}")

    # Population resilience
    resilience = pop_analyzer.resilience_index()
    if resilience > 0:
        print(f"\n  Population resilience (winter→spring recovery): {resilience:.2f}x")

    # Phase transitions
    if analyzer.phase_transitions:
        print(f"\n  ⚡ {len(analyzer.phase_transitions)} phase transition(s) detected!")

    results.append({
        'config': config['name'],
        'metrics': analyzer.get_cumulative_metrics(),
        'transitions': len(analyzer.phase_transitions),
        'resilience': resilience,
        'extinct': extinct,
        'final_pop': len(sim.agents),
        'max_gen': sim.max_generation,
    })

    print()
    print("─" * 64)
    print()

# Comparative summary
print("╔══════════════════════════════════════════════════════════════╗")
print("║  COMPARATIVE RESULTS                                        ║")
print("╚══════════════════════════════════════════════════════════════╝")
print()
print(f"{'Config':<35} {'NMI':>6} {'I(S;C)':>8} {'Pop':>5} {'Gen':>5}")
print("─" * 64)
for r in results:
    m = r['metrics']
    pop = '☠' if r['extinct'] else str(r['final_pop'])
    print(f"{r['config']:<35} {m['nmi']:>6.3f} {m['mutual_info']:>7.3f}b {pop:>5} {r['max_gen']:>5}")

print()
# Key finding
nmis = [r['metrics']['nmi'] for r in results if not r['extinct']]
if nmis:
    best = max(results, key=lambda r: r['metrics']['nmi'])
    print(f"Best communication emerged in: {best['config']}")
    print(f"  NMI = {best['metrics']['nmi']:.3f} — ", end="")
    nmi = best['metrics']['nmi']
    if nmi < 0.05:
        print("No real communication. Signals are noise.")
    elif nmi < 0.15:
        print("Weak proto-communication. Barely above chance.")
    elif nmi < 0.30:
        print("Genuine emerging language. Signals carry real information.")
    elif nmi < 0.50:
        print("Functional communication system. This is real.")
    else:
        print("Strong language. Agents efficiently encode meaning in signals.")

    # The key insight
    print()
    print("KEY INSIGHT: Predator pressure should force communication to develop")
    print("faster and stronger — danger contexts create evolutionary pressure for")
    print("reliable signaling. Seasons add boom/bust cycles that test whether the")
    print("communication system is robust or fragile.")
    if len(results) >= 3:
        baseline_nmi = results[0]['metrics']['nmi']
        predator_nmi = results[1]['metrics']['nmi']
        full_nmi = results[2]['metrics']['nmi']
        if predator_nmi > baseline_nmi:
            print(f"\n✓ CONFIRMED: Predator pressure improved NMI by {predator_nmi - baseline_nmi:+.3f}")
        else:
            print(f"\n✗ SURPRISING: Predator pressure did NOT improve communication ({predator_nmi - baseline_nmi:+.3f})")
        if full_nmi > predator_nmi:
            print(f"✓ Seasonal stress further improved NMI by {full_nmi - predator_nmi:+.3f}")
        else:
            print(f"  Seasonal stress {'reduced' if full_nmi < predator_nmi else 'maintained'} NMI ({full_nmi - predator_nmi:+.3f})")
