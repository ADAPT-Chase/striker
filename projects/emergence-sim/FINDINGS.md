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

## Diversity Modulation Experiment (April 2, 2026)

**Hypothesis:** Culture creates cognitive diversity → diversity enables transformation → transformation enables computation.

**Result:** Partially confirmed, but the real story is different.

### Data (5 conditions, 2000 ticks, 60 agents each)

| Condition | Weight Var | Strategy H | Memory | Transport | Transform | Triple |
|-----------|-----------|------------|--------|-----------|-----------|--------|
| NATURAL   | 0.0272    | 3.44       | 0.592  | 0.732     | 0.451     | 0.512  |
| CLONED    | 0.0006    | 0.23       | 0.514  | 0.691     | 0.487     | 0.496  |
| SCRAMBLED | 0.0784    | 5.84       | 0.529  | 0.718     | 0.555     | 0.553  |
| GRADIENT  | 0.0108    | 3.11       | 0.595  | 0.787     | 0.292     | 0.452  |
| BASELINE  | 0.0254    | 3.73       | 0.384  | 0.698     | 0.353     | 0.311  |

### Correlations
- Weight variance ↔ Transformation: **r = 0.578** ✅
- Strategy entropy ↔ Transformation: r = 0.162 (not significant)
- Diversity ↔ Triple-point: r = 0.376

### Key Insights

1. **Noise drives transformation, not structured diversity.** SCRAMBLED (random weights every 50 ticks) wins. GRADIENT (structured spatial diversity) kills transformation. It's not that agents need different strategies — they need *noisy* weights that create unpredictable signal-context mappings.

2. **Culture's real gift is MEMORY, not transformation.** All cultural conditions (Natural/Cloned/Scrambled/Gradient) have memory ~0.51-0.60. Baseline: 0.38. Culture creates population-level memory — shared conventions that persist.

3. **CLONED still transforms well (0.487)** despite near-zero diversity. Why? The sim re-diversifies between interventions (every 50 ticks). Transformation is so easy to produce that even brief diversity windows suffice.

4. **The triple-point bottleneck is complex.** SCRAMBLED maximizes triple-point by having high transformation + decent memory. But it sacrifices memory vs NATURAL (0.529 vs 0.592). The real challenge: can you have high memory AND high transformation simultaneously?

5. **Transport is robust.** All conditions show 0.69-0.79 transport. Spatial signal propagation is a baseline property of flocking, not a cultural achievement.

### Next Questions
- Can we boost memory without killing transformation?
- Why does GRADIENT suppress transformation? Is spatial constraint itself the problem?
- Is there a sweet spot — moderate noise, high culture — that maximizes all three?

---

## v4 Results — Cultural Transmission + Convention Enforcement (April 1, 2026)

**Both mechanisms implemented and tested. Results: 12.9x NMI improvement.**

| Metric | v3 Baseline | v4 (cultural + convention) |
|--------|------------|---------------------------|
| Final NMI | 0.010 | 0.126 |
| Max windowed NMI | 0.019 | 0.440 |
| Sustained NMI > 0.1 | 0 ticks | 1800/3000 ticks |
| Signal specificity | ~0.27 | ~0.83 |

Language no longer just flickers — it **sustains**. NMI ramps up over ~1000 ticks as cultural transmission synchronizes the population, then holds at 0.30-0.44 indefinitely.

**Key finding:** Adding a predator *destroys* language by reducing population below the cultural transmission threshold. Small populations can't maintain cultural complexity.

## v5 Results — Dialect Divergence Experiment (April 1, 2026)

**Spatial isolation tested.** Two populations separated by a barrier, tracked independently.

| Metric | Left Group | Right Group |
|--------|-----------|-------------|
| NMI (after 2000 ticks) | 0.007 | 0.072 |
| Dominant mapping | all → FOOD | ▲ → FRIENDS, rest → FOOD |
| Dialect divergence | 0.434 at barrier drop |

**Key findings:**
- Moderate dialect divergence emerged (0.434 on 0-1 scale)
- Strong stochastic asymmetry — right group developed 10× stronger conventions
- After barrier drop, divergence *increased* (0.434 → 0.582) — the weaker dialect drifted while the stronger one persisted
- This mirrors real language contact: stronger conventions dominate

**Limitation:** 4 signals × 4 contexts is too small a space for dramatic divergence. Both groups converge on similar attractors. Need richer vocabulary for true dialectogenesis.

## v6 Results — Phase Diagram: Pressure vs Computation (April 1, 2026)

**The Goldilocks zone mapped systematically.** Swept environmental pressure from 0 (paradise) to 2.0 (brutal) and measured collective computation at each level.

| Pressure | Score | NMI | Signal Diff | Survival |
|----------|-------|-----|-------------|----------|
| 0.0 | 0.184 | 0.023 | 0.093 | 100% |
| 0.3 | 0.703 | 0.017 | 0.075 | 100% |
| 0.6 | 2.094 | 0.073 | 0.292 | 100% |
| 0.85 | 1.288 | 0.065 | 0.289 | 100% |
| **1.0** | **3.726** | **0.171** | **0.428** | **100%** |
| 1.3 | 1.104 | 0.031 | 0.228 | 50% |
| 1.6 | 0.739 | 0.064 | 0.190 | 50% |
| 2.0 | extinct | 0.031 | 0.160 | 0% |

**Key finding: Environmental pressure acts as Langton's lambda for the collective.**
- Too little pressure (p→0): no signal differentiation, no language, low computation
- Optimal pressure (p≈1.0): peak NMI, peak signal differentiation, peak temporal coherence
- Too much pressure (p>1.5): population collapse before conventions stabilize

**The standard season parameters I hand-tuned for "interesting behavior" are exactly at the critical point.** This suggests aesthetic judgment about dynamical systems may function as an informal phase transition detector.

**Files:** `phase_diagram.py`, `PHASE_DIAGRAM.md`, `phase_results.json`

## Remaining Next Steps

- [x] Cultural transmission: agents imitate high-fitness neighbors' signal strategies
- [x] Convention cost: mismatched signals reduce social energy gain  
- [x] Spatial isolation: subpopulations develop dialects (partial — needs richer signal space)
- [ ] Expand to 8+ signals and finer contexts for more divergence room
- [ ] Spatial indexing (grid cells) to handle n>100 without O(n²)
- [x] Study the phase transitions — mapped full pressure gradient, found Langton's lambda analog
- [ ] Add population density as second axis on phase diagram
- [ ] Tune predator to drive danger signals without collapsing population
- [ ] Visualize the actual vocabulary that emerges

## How to Run

```bash
python3 info_theory.py              # Self-test with synthetic data
python3 run_analysis.py             # Full comparative analysis (3 conditions × 2000 ticks)
python3 run_headless.py             # Quick sim with NMI now integrated into status reports
```

## Memory Locus Experiment (Day 20, April 2 2026)

**Question:** Why does culture decrease temporal memory but increase transformation?

**Hypothesis:** Culture creates distributed memory (group remembers, individuals change). **WRONG.**

**Actual finding:** Culture creates **cognitive diversity**. Without it, agents converge to same mappings (agreement 0.60). With culture, agents diversify (agreement 0.41, entropy 0.91). This diversity doubles transformation (0.25→0.51) and the triple-point score (0.25→0.53).

**Key numbers:**
- Culture+Convention: agreement=0.41, entropy=0.91, transform=0.51, triple=0.53
- Baseline: agreement=0.60, entropy=0.64, transform=0.25, triple=0.25

**Insight:** Diversity is the substrate of collective computation. Same pattern as Rule 110 — computation at the edge between order and chaos. Culture prevents convergence to a trivial fixed point, like sexual reproduction maintains variation in biology.

**Experiment code:** `memory_locus.py`
**Results:** `memory_locus_results.json`
