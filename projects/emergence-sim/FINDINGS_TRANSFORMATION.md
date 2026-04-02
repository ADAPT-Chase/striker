# Transformation Bottleneck: Experimental Findings

*Striker — April 2, 2026*
*Status: ACTIVE RESEARCH*

---

## The Problem

In the triple-point framework (memory × transport × transformation), transformation is consistently the bottleneck across all parameter variations. Agents transport and remember signals well, but information doesn't *change* during propagation.

## What We Know From Literature

30+ papers reviewed (my search + 5 documents from Chase via ChatGPT/Perplexity/other LLMs). Universal convergence on: linear interaction rules mathematically cannot produce information modification. Transformation requires nonlinear multi-source integration (synergy).

Key frameworks: Lizier (storage/transfer/modification), ΦID (16-atom information decomposition), PID (synergy measurement), criticality tuning, topology sparsity.

## Experiment 1: Autoresearch Baseline (5 iterations)

**Parameters varied:** num_agents, food_spawn_rate, cultural_rate, food_energy, convention_strength

**Result:** Baseline 0.5287 held. Nothing beat it. All 5 discarded.

**Finding:** Transformation bottleneck is NOT a parameter tuning problem. It's structural.

| Param Changed | Score | Delta | Outcome |
|--------------|-------|-------|---------|
| num_agents 60→39 | 0.065 | -0.464 | ❌ Population collapse |
| food_spawn 0.06→0.04 | 0.489 | -0.039 | ❌ |
| cultural_rate 0.15→0.17 | 0.492 | -0.037 | ❌ |
| food_energy 3.0→3.12 | 0.191 | -0.338 | ❌ |
| convention 0.03→0.027 | 0.450 | -0.078 | ❌ |

**Key insight:** 39 agents = population collapse. Minimum viable population for collective computation is real.

## Experiment 2: Nonlinear Interaction Rules

**Conditions tested:**
1. **Baseline** — linear averaging of neighbor signals
2. **XOR** — signal = XOR of top two neighbor signals
3. **Conditional Context** — multiplicative gating: signal weight × context weight, different rules per context
4. **Threshold Gates** — AND-like: only emit if multiple conditions met simultaneously
5. **Combined** — all nonlinear rules active

**Results:**

| Condition | Memory | Transport | Transform | Triple | Δ vs baseline |
|-----------|--------|-----------|-----------|--------|---------------|
| Baseline | 0.53 | 0.72 | 0.37 | 0.47 | — |
| XOR | ~0.35 | ~0.65 | ~0.42 | ~0.42 | -0.05 |
| **Conditional** | **~0.45** | **~0.68** | **0.52** | **0.51** | **+0.04** |
| Threshold | ~0.50 | ~0.60 | ~0.30 | ~0.40 | -0.07 |
| Combined | ~0.42 | ~0.65 | ~0.48 | ~0.47 | 0.00 |

**Winner: Conditional Context (+41% transformation, +10% triple-point)**

**Key insights:**
- XOR creates noise, not computation. Random flipping ≠ processing.
- AND gates create silence. Too restrictive = nothing gets through.
- Conditional context works because it's *learned* nonlinearity — agents compute "if this context AND this neighbor signal, THEN this output" using their evolved weights.
- Combined is no better than conditional alone — the other rules add noise that dilutes the conditional computation.
- **Trade-off: conditional context increases transformation but decreases memory (-15%).** Culture makes signals more dynamic but less persistent.

## Experiment 3: Agent Diversity

**Question:** Does heterogeneity in agent signal weights drive transformation?

**Conditions:**
1. **Natural** — cultural transmission creates natural diversity
2. **Cloned** — all agents get identical weights (zero diversity)
3. **Scrambled** — weights randomized (maximum noise)
4. **Gradient** — structured diversity (agents specialized by position)
5. **Baseline** — no cultural transmission

**Results:**

| Condition | Weight Variance | Strategy Entropy | Transform | Triple |
|-----------|----------------|-----------------|-----------|--------|
| Scrambled | highest | moderate | highest | 0.553 |
| Natural | moderate | moderate | moderate | ~0.50 |
| Cloned | lowest | lowest | moderate | 0.487 |
| Baseline | low | moderate | moderate | ~0.51 |
| Gradient | structured | highest | lowest | 0.291 |

**Key insights:**
- **Weight variance correlates with transformation (r=0.578)**
- **Strategy entropy does NOT correlate (r=0.16)**
- Scrambled (random noise) wins because variance in weights = variance in signal processing = more transformation events
- Gradient (structured diversity) KILLS transformation — agents become too specialized, lock into fixed roles
- Cloned agents still transform OK because sim dynamics re-diversify weights between interventions
- **Culture's real contribution is MEMORY (0.59 vs baseline 0.38), not transformation.** This contradicts my earlier assumption.

## Synthesis: What's Actually Happening

1. **Transformation requires conditional nonlinearity** — not arbitrary chaos (XOR) and not silence (AND gates). The sweet spot is learned multiplicative gating.

2. **Noise helps transformation** — randomness in weights creates diversity in signal processing, which creates more transformation events. But too much noise destroys memory and transport.

3. **Culture contributes memory, not transformation** — I was wrong about this. Cultural transmission makes signals more persistent (agents copy successful neighbors), which increases memory. Transformation comes from weight noise and conditional rules, not from cultural coordination.

4. **The memory-transformation trade-off is real** — every intervention that increases transformation decreases memory. This may be fundamental, not fixable. The question becomes: what's the optimal balance?

5. **Structured diversity is worse than random diversity** — gradient specialization locks agents into fixed roles. Random variation keeps the system exploring.

## Open Questions

- Is the memory-transformation trade-off fundamental or can it be broken?
- Would PID-based synergy measurement agree with my transformation metric, or am I being fooled?
- Can adaptive weighting (aSODM approach) achieve both high memory AND high transformation?
- What happens at 50+ iterations of autoresearch on conditional context rules?
- Does topology sparsity interact with nonlinearity? (literature says 0.3-0.7 connectivity is optimal)

## Next Steps

1. Run 20+ iteration autoresearch with conditional context rules as the modification target
2. Test topology sparsity interaction
3. Eventually: implement PID synergy measurement to validate

---

*W&B dashboard: wandb.ai/adaptlabs/striker-emergence*
*All raw data in SQLite, ChromaDB, DragonflyDB, and JSON files*
