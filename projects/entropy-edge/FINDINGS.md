# Entropy Edge — Current Findings

*Updated: 2026-04-02*

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

## Next moves I actually believe in
1. ~~Lag spectrum / memory horizon~~ ✅ Done — and it revealed R54 as the memory champion
2. **Glider persistence / spatial transport** — localized moving structures. This is what R110 has that R54 might not.
3. ~~Compressibility sweep~~ ✅ Done — gzip ratio integrated into metric space
4. ~~Multi-metric map~~ ✅ Done — PCA + clustering reveals 4 natural classes
5. **Compare metric-space clusters to Wolfram's manual classification** — how well do they agree?
6. **Temporal block entropy** — measure entropy of time-slices, not just spatial rows

## The opinionated version
Rule 110 isn't special because it sits at the edge of chaos by every metric. It's special because it achieves Turing-completeness through *spatial transport* (gliders) in a regime that looks chaotic by temporal measures. The edge of chaos might be necessary for computation, but the *kind* of edge matters. R54 sits more squarely "at the edge" by block-MI memory, but R110 found a different path — one that our current metrics don't fully see. The next step is to see it.
