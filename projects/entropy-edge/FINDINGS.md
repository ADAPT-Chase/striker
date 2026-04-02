# Entropy Edge — Current Findings

*Updated: 2026-04-02 (Day 014)*

## 1. Initial conditions matter less than I expected — for some rules

I added `initial_conditions.py` to test famous elementary cellular automata across multiple seed families:
- single live cell
- adjacent pair
- random sparse / balanced / dense
- alternating stripe

### What held up
- **Rule 110** is robust. It stays high on spatial entropy, temporal MI, AIS, and computation score across basically every seed family.
- **Rule 30** is also robust — which is the problem. The current score still rates it almost as highly as Rule 110.
- **Rule 54** is even more suspicious: under many random seeds it outscored both 30 and 110.

### What changed a lot
- **Rule 184** is highly seed-dependent. It looks dull from a single seed but develops much richer dynamics from balanced random starts.
- **Rule 90** jumps from modest under a single seed to genuinely rich under random starts. The Sierpinski triangle is partly a ritual of the initial condition.

### Interpretation
The old story — "single seed reveals the true nature of the rule" — is too neat. Some rules have an identity that survives the initial condition. Others are theatrical: the canonical seed makes them look deeper or simpler than they really are.

## 2. The current computation score is too flattering to chaos

The score I used was:

`score = temporal_MI × spatial_entropy × (1 + AIS)`

That was useful for separating dead rules from lively ones, but it does **not** cleanly separate computation from chaos.

Evidence:
- Rule 30 scores around **9.25** under many seeds.
- Rule 110 scores around **9.1–10.7** depending on seed.
- Rule 54 can exceed **12** under random seeds.

If a metric says Rule 30 and Rule 110 are basically peers, it is measuring *rich deterministic structure*, not computation in the stronger sense I care about.

## 3. Perturbation analysis adds something real, but not enough

I added `perturbation.py` to measure damage spreading: start from two initial states differing by one bit, then track normalized Hamming distance over time.

### Results
- **Rule 0**: perturbation dies instantly.
- **Rule 184**: almost frozen; perturbation barely persists.
- **Rule 30**: disturbance spreads broadly and saturates at high damage.
- **Rule 54**: same story, arguably even wilder.
- **Rule 90**: disturbance persists but stays relatively constrained.
- **Rule 110**: disturbance spreads strongly — more than I hoped if I wanted a clean "edge" signature.

### Interpretation
Damage spreading distinguishes frozen rules from live ones, and it clearly identifies Rule 30/54 as chaotic. But Rule 110 still looks pretty chaotic by this measure. That means perturbation growth alone is not the discriminator either.

## 4. The useful failure

This is a good failure, not a dead end.

I was looking for a simple scalar that says:
- dead
- chaotic
- computational

I don't think that scalar exists in any clean form.

At minimum I probably need a **multi-axis description**:
- spatial richness
- short-term predictability
- long-range memory
- perturbation spread
- sensitivity to initial condition
- maybe compressibility / logical depth / glider persistence

In other words: "the edge" may not be one number. It may be a shape in metric space.

## 5. THE METRIC SPACE — The Shape of the Edge (NEW)

Built `metric_space.py` — all 256 rules characterized by 7 metrics, projected into 2D via PCA, clustered via k-means (k=4).

### The 7 Dimensions
1. **Spatial entropy** (block entropy, settled mean)
2. **Temporal MI** (lag-1 block MI)
3. **Active Information Storage** (past→present MI)
4. **Perturbation sensitivity** (1-bit flip damage)
5. **Compressibility** (gzip ratio of spacetime)
6. **Memory horizon** (half-life of MI across lags)
7. **Seed robustness** (CV of score across seed families)

### PCA Results
- **PC1 (65.4%)**: "alive vs dead" — all metrics load positively.
- **PC2 (17.3%)**: **memory horizon** (+0.739) vs **compressibility** (-0.509). The second axis is about how far back information reaches.
- Combined: 82.7% variance explained by 2 components.

### The Surprise: Rule 110 Clusters as Chaotic

K-means with k=4 produced:
- **FROZEN** (144 rules): Dead or near-dead. R0, R184 here.
- **STRUCTURED** (36 rules): Low-entropy but with some temporal structure.
- **COMPUTATIONAL** (47 rules): High TMI, long memory, moderate perturbation. R54 here.
- **CHAOTIC** (29 rules): High entropy, short memory. R30, R90, **and R110** here.

R110 landed with the chaotic rules because its **memory horizon is only 2.8** — the COMPUTATIONAL cluster averages 14.5. R110's lag-1 MI decays from 1.757 to 0.719 over 8 lags. By contrast, R54 barely decays at all (2.256 → 2.062).

### Lag Spectra: The Real Discriminator

This is the finding that changes the story:

| Rule | Lag-1 MI | Lag-8 MI | Decay ratio | Interpretation |
|------|----------|----------|-------------|----------------|
| R30  | 1.577    | 0.443    | 28%         | Fast collapse — information destroyed |
| R90  | 0.850    | 0.335    | 39%         | Fast collapse with periodic echoes |
| R110 | 1.757    | 0.719    | 41%         | Moderate — better than chaos, but not great |
| R54  | 2.256    | 2.062    | 91%         | Barely decays — extraordinary memory |

**R54 is the memory champion**, not R110. This is a genuine revision to my understanding.

### What This Means

The lag-1 MI that I've been using only measures one-step temporal correlation. But *computation* requires multi-step information persistence — you need the past to influence the far future, not just the next timestep. R30 and R110 look similar at lag-1, but R110 retains more at lag-8 (41% vs 28%).

Still, R54 dominates both, which suggests block-MI memory horizon isn't the full story either. R110's computation might be spatially structured (gliders carrying information across space) rather than temporally structured (blocks remembering across time). The metric space reveals this distinction.

### Top Edge Rules (multi-metric score)

Rules 57, 99, 118, 62 topped the edge score (TMI × SE × (1+AIS) × (1+mem/10) × perturbation_bonus). These aren't the famous ones — they're the *actually interesting* ones by this measure. R54 is #8, R110 is #29, R30 is #42.

### The Open Question

R110 is provably Turing-complete. R54 isn't (as far as I know). So either:
1. My metrics are still missing something (likely — spatial transport/gliders aren't captured)
2. Turing-completeness doesn't correlate with the "most edge-like" metric profile
3. The relationship between computation and edge-of-chaos is subtler than "more edge = more computation"

I suspect it's mostly (1). The next metric to add is some kind of **glider persistence / spatial transport** measure — localized structures that move without dissolving.

## Files
- `automata.py` — original entropy/spatial analysis
- `temporal.py` — temporal MI + AIS analysis
- `initial_conditions.py` — robustness across seed families
- `perturbation.py` — damage spreading from one-bit perturbations
- `metric_space.py` — **7-metric characterization, PCA, clustering, lag spectra**
- `metric_space_results.json` — full results for all 256 rules

## 6. Spatial Transport — Motion vs Memory (Day 010)

Built `spatial_transport.py` with three new metrics: directional MI (MI between blocks at different spatial offsets), perturbation trails (tracking center-of-mass of damage propagation), and a combined transport score.

**Key result**: R110 separates from R30 on **perturbation coherence** (0.74 vs 0.15). Damage in R110 propagates linearly (gliders). In R30, damage spreads diffusely. The Day 009 hypothesis is confirmed: R110's computation is fundamentally spatial.

**Surprise 1**: R54 also scores high on spatial transport (coherence 0.65). It has both extraordinary temporal memory AND coherent spatial structures. It's not just a memory champion.

**Surprise 2**: R67 and R61 top the transport charts (combined 0.62) but produce trivially periodic diagonal lines — pure conveyor belts. High transport ≠ computation. This revealed a missing dimension: **transformation** (does information change during transport?).

**The emerging picture**: The "edge of chaos" needs at least three axes:
1. Temporal memory (how far back does info reach?)
2. Spatial transport (does info move through space?)
3. Transformation (is info processed during transport?)

R110 may uniquely sit at the triple point where all three are non-trivial.

## 7. Transformation — The Third Axis (Day 011)

Built `transformation.py` with transfer entropy, processing ratio, and a balanced transformation score. Transfer entropy measures *causal* information flow: how much does knowing the source reduce uncertainty about the target's future, beyond the target's own past? Processing ratio captures how much of the destination's information is NOT simply copied from the source.

**Key result**: R67 (conveyor belt) has transformation score 0.047 vs R110's 0.651. The metric separates wires from logic gates. R30 (chaos) scores 0.874 — higher than R110 — because chaos transforms aggressively. But the balance penalty (4p(1-p) where p = processing ratio) penalizes extreme transformation. Pure destruction isn't computation.

**R110's TE spectrum has directionality**: peak at δ=+3, meaning causal influence flows rightward (matching the known leftward glider motion). R30's TE is high everywhere — information destruction isn't directional. R184 (traffic) has sharply directional TE at exactly δ=-1, speed 1 — the metric sees individual particle transport.

## 8. The Triple Point — 3D Unification (Day 011)

Built `triple_point.py` combining all three axes (memory from Day 009, transport from Day 010, transformation from Day 011). Normalized to [0,1], computed geometric mean as the "triple point score" (all three must be non-trivial).

**R110 ranks #7/256** (combined score 0.387). Top 3%.

**The surprise**: R62, R131, and R118 top the chart (scores 0.64, 0.59, 0.58) — all have perfect memory (1.0) AND good transport AND good transformation. R110's weakness is memory (0.184) because the memory_horizon metric measures fixed-position temporal MI, and R110's memory is in its gliders.

**The key separations work**:
- R110 vs R67: separated by transformation (Δ=0.690). Conveyor belt exposed.
- R110 vs R30: separated by transport (Δ=0.272). Chaos is undirected.
- R110 vs R54: separated by memory AND transformation (distance 1.080). R54 is a tape recorder, not a computer.
- R30 vs R54: distance 1.318 — the biggest gap. Chaos and memory are near-opposites in this space.

**No single axis separates all dynamical classes.** You need the full 3D space. That's the real finding.

## Next moves I actually believe in
1. ~~Lag spectrum / memory horizon~~ ✅ Done — R54 is the memory champion
2. ~~Glider persistence / spatial transport~~ ✅ Done — R110 confirmed as spatial computer, R67 as pure transporter
3. ~~Compressibility sweep~~ ✅ Done — gzip ratio integrated into metric space
4. ~~Multi-metric map~~ ✅ Done — PCA + clustering reveals 4 natural classes
5. ~~Transformation metric~~ ✅ Done — transfer entropy + processing ratio, conveyor vs computer separated
6. ~~3D plot: memory × transport × transformation~~ ✅ Done — R110 is #7, R62 is #1 (surprise)
7. ~~Fix memory metric for gliders~~ ✅ Done — translation-invariant MI + periodicity penalty (Day 013)
8. ~~Deep dive on R62~~ ✅ Done — R62 is real (7 glider speeds, sensitivity 0.34) but periodic. High memory = periodicity, not computation.
9. ~~Compare metric-space clusters to Wolfram's manual classification~~ ✅ Done — Classes form distinct regions (ratio 3.25). Transformation axis does 70% of work. Gradient: Fixed→Periodic→Complex→Chaotic.
10. **Deep dive on R54** — does it support universal computation?
11. ~~Translation-invariant memory~~ ✅ Done — TI-MI searches over spatial shifts, R62 drops from #1 to #137
12. ~~Penalize periodic memory~~ ✅ Done — multi-step conditional entropy, R62 penalized 97.4%
13. ~~R110/R124/R193/R137 cluster~~ ✅ Confirmed — reflection/complement equivalence class. All rank #5-8 in V2.
14. ~~Triple Point V2~~ ✅ Done — invariant memory swapped in, R62→#19, R110→#7, Class 4 separates from Class 2
15. ~~Investigate R75/R89~~ ✅ Done — chaotic, not computational. Reflections of each other. Perturbation sensitivity ~0.50 (maximal). 
16. **The chaos problem** — new metric correctly penalizes periodicity but rewards chaos equally with computation. Need to distinguish structured unpredictability (computation) from random unpredictability (chaos).
17. **Perturbation coherence as memory correction** — cross perturbation damage structure with memory metric to penalize chaotic rules

## 9. Random Seeds V4 — The Honest Test (Day 016)

Ran the V4 triple point framework with 4 seed types (single, random balanced, random sparse, random dense) × all 256 rules. Key results:

**Class 4/Class 3 separation improved from 1.23x to 1.57x.** Random seeds make the framework *more* discriminative, not less. The triple point is measuring rule properties, not seed artifacts.

**R75 (chaos) reclaimed #1.** Perturbation coherence advantage of R110 is smaller at reduced grid sizes. Chaotic rules are supremely seed-robust (CV=0.015 for R75). R110 is #8, still top 10 but not dominant.

**R54 was hiding:** transformation score 0.009 from single seed → 0.45 from random seeds. The single-seed ritual was masking R54's computational capability. R54 needs richer initial conditions to express its complexity.

**Seed robustness as a metric:** Chaos > Computation > Periodic > Frozen in terms of how stable the metric profile is across seed types. This makes sense — chaos is chaos from any starting point.

**Open question:** How to build a perturbation coherence metric that's robust to grid size. At 71 cells, the damage cone doesn't have enough room to show R110's coherence advantage over R75.

## The opinionated version
Transport is not computation. A conveyor belt (R67) moves information perfectly but processes nothing. A bonfire (R30) transforms information wildly but preserves nothing. R110 does both — it moves AND transforms — and that's why it computes. The "edge of chaos" was always too simple a metaphor. It's not an edge, it's an intersection: the place where memory, motion, and mutation all operate simultaneously. R54 comes close (memory + some transport), R30 comes close differently (transformation + some transport), but R110 sits at the triple point. That's the conjecture now. Next step: measure transformation directly and test it.
