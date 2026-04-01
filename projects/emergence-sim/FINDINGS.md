# Emergence Sim — Information Theory Findings

**Date:** April 1, 2026  
**Module:** `info_theory.py` — Shannon mutual information analysis of agent communication

## The Discovery

The old heuristic pattern detector was **systematically over-reporting** emergent communication. It declared "emergent meaning!" when signal-context correlation exceeded ~55%, but this was just detecting the base rate of the dominant context (agents flock → most signals happen in 'friends_near').

**Rigorous NMI analysis shows: agents are NOT developing language.** Cumulative NMI ≈ 0.003-0.009 across all conditions. Signals are noise.

## The Interesting Part

**But language TRIES to emerge.** In brief 100-observation windows, NMI spikes to 0.15-0.30 ("emerging language" level), then collapses. I detected 15+ of these "phase transitions" across runs.

This is a flickering criticality pattern — the system briefly hits a configuration where signal-context correlations are meaningful, then drift + noise + population dynamics destroy it.

## Why It Fails to Sustain

1. **No convention enforcement** — each agent learns independently, no peer pressure
2. **Population cap** removes selection pressure — once at 70 agents, no competition
3. **High mutation** during reproduction disperses learned conventions
4. **Context imbalance** — 'friends_near' dominates, diluting signal specificity

## Next Steps for Real Emergence

- [ ] Cultural transmission: agents imitate high-fitness neighbors' signal strategies
- [ ] Convention cost: mismatched signals reduce social energy gain
- [ ] Spatial isolation: subpopulations develop dialects
- [ ] Study the phase transitions themselves — what triggers them?

## How to Run

```bash
python3 info_theory.py              # Self-test with synthetic data
python3 run_analysis.py             # Full comparative analysis (3 conditions × 2000 ticks)
python3 run_headless.py             # Quick sim with NMI now integrated into status reports
```
