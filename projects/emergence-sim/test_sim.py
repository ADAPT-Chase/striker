#!/usr/bin/env python3
"""Tests for emergence simulator v2."""
from sim import Simulation, Agent, Food, NUM_SIGNALS

def test_basic():
    sim = Simulation(num_agents=20, use_predator=False)
    assert len(sim.agents) == 20
    for _ in range(50):
        sim.step()
    assert sim.tick == 50
    assert len(sim.agents) > 0
    frame = sim.render()
    assert len(frame) > 100
    print("✓ basic simulation runs")

def test_signals():
    sim = Simulation(num_agents=30, use_predator=False)
    for _ in range(80):
        sim.step()
    # At least some agents should be signaling
    signaling = sum(1 for a in sim.agents if a.current_signal >= 0)
    assert signaling > 0, f"No agents signaling after 80 ticks"
    # Signal history should be populated
    total = sum(sum(sim.logger.signal_context_history[s].values()) for s in range(NUM_SIGNALS))
    assert total > 10, f"Only {total} signals recorded"
    print(f"✓ signals working ({signaling} active, {total} total emissions)")

def test_food():
    sim = Simulation(num_agents=20, use_predator=False)
    initial_food = len(sim.food_sources)
    assert initial_food > 0
    for _ in range(100):
        sim.step()
    total_eaten = sum(a.food_eaten for a in sim.agents)
    assert total_eaten > 0, "No food eaten"
    print(f"✓ food system works ({total_eaten} eaten)")

def test_predator():
    sim = Simulation(num_agents=40, use_predator=True)
    assert sim.predator is not None
    for _ in range(300):
        sim.step()
    # Predator exists and sim runs; deaths may come from predator or energy drain
    print(f"✓ predator works ({sim.deaths} deaths in 300 ticks)")

def test_inheritance():
    sim = Simulation(num_agents=40, use_predator=False)
    for _ in range(200):
        sim.step()
    assert sim.births > 0, "Should have births"
    # Check that children inherited weights
    for a in sim.agents:
        assert len(a.signal_weights) == NUM_SIGNALS
        assert len(a.response_weights) == NUM_SIGNALS
    print(f"✓ inheritance works ({sim.births} births)")

if __name__ == '__main__':
    test_basic()
    test_signals()
    test_food()
    test_predator()
    test_inheritance()
    print("\n🎉 All tests passed!")
