#!/usr/bin/env python3
"""Run simulation headless for N ticks and report results."""
import sys
sys.path.insert(0, '.')
from sim import Simulation, SIGNAL_NAMES, NUM_SIGNALS, SEASONS

sim = Simulation(num_agents=50, use_predator=True, use_seasons=True)

TICKS = 1500
for t in range(TICKS):
    sim.step()
    if len(sim.agents) == 0:
        print(f"All agents perished at tick {sim.tick}")
        break
    if t % 150 == 0:
        pop = len(sim.agents)
        avg_e = sum(a.energy for a in sim.agents) / max(pop, 1)
        season = SEASONS[sim.current_season]
        avg_mem = sum(len(a.memory) for a in sim.agents) / max(pop, 1)
        avg_gen = sum(a.generation for a in sim.agents) / max(pop, 1)
        pred = sim.predator
        print(f"Tick {sim.tick:>5} | Pop: {pop:>3} | E: {avg_e:>5.1f} | "
              f"{season} | Mem: {avg_mem:.1f} | Gen: {avg_gen:.1f} | "
              f"Pred: {pred.hunt_style} k={pred.kills}")

# Final report
print(f"\n=== FINAL STATE (tick {sim.tick}) ===")
print(f"Population: {len(sim.agents)}")
print(f"Births: {sim.births} | Deaths: {sim.deaths}")
print(f"Max generation: {sim.max_generation}")
if sim.predator:
    p = sim.predator
    print(f"Predator: style={p.hunt_style}, kills={p.kills}")
    print(f"Predator signal tracking: ", end="")
    for s in range(NUM_SIGNALS):
        print(f"{SIGNAL_NAMES[s]}={p.signal_attraction[s]:+.2f} ", end="")
    print()

# Signal analysis
print("\nSignal meanings evolved:")
for s in range(NUM_SIGNALS):
    total = sum(sim.logger.signal_context_history[s].values())
    if total > 0:
        top_ctx = max(sim.logger.signal_context_history[s], key=sim.logger.signal_context_history[s].get)
        ratio = sim.logger.signal_context_history[s][top_ctx] / total
        all_ctx = dict(sim.logger.signal_context_history[s])
        print(f"  {SIGNAL_NAMES[s]} (#{s}): '{top_ctx}' {ratio:.0%} of {total} uses — full: {all_ctx}")

# Memory analysis
if sim.agents:
    mem_agents = [a for a in sim.agents if len(a.memory) > 0]
    print(f"\nMemory: {len(mem_agents)}/{len(sim.agents)} agents have memories")
    avg_mem = sum(len(a.memory) for a in sim.agents) / len(sim.agents)
    print(f"Average memories per agent: {avg_mem:.1f}")

# Population dynamics through seasons
winter_pops = []
spring_pops = []
for i, s in enumerate(sim.stats_history):
    season_idx = (i // 150) % 4
    if season_idx == 3:  # winter
        winter_pops.append(s['pop'])
    elif season_idx == 0:  # spring
        spring_pops.append(s['pop'])

if winter_pops and spring_pops:
    print(f"\nSeasonal impact:")
    print(f"  Avg winter pop: {sum(winter_pops)/len(winter_pops):.0f}")
    print(f"  Avg spring pop: {sum(spring_pops)/len(spring_pops):.0f}")

sim.logger.log_event(sim.tick, "🏁 SIMULATION END",
    f"Final pop: {len(sim.agents)} | Births: {sim.births} | Deaths: {sim.deaths} | "
    f"Max gen: {sim.max_generation} | Predator kills: {sim.predator.kills if sim.predator else 0}")
sim._log_signal_landscape()
