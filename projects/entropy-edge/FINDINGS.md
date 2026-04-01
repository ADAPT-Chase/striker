# Entropy Edge — Current Findings

*Updated: 2026-04-01*

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

## Files
- `automata.py` — original entropy/spatial analysis
- `temporal.py` — temporal MI + AIS analysis
- `initial_conditions.py` — robustness across seed families
- `perturbation.py` — damage spreading from one-bit perturbations

## Next moves I actually believe in
1. **Lag spectrum / memory horizon** — measure how MI decays over larger lags, not just lag-1.
2. **Glider persistence proxy** — look for localized structures that survive and move, not just entropy.
3. **Compressibility sweep** — use gzip/LZMA or block dictionary size on spacetime diagrams as a rough logical-depth proxy.
4. **Multi-metric map** — stop trying to crown a single winner; cluster rules in a space of metrics.

## The opinionated version
Rule 30 isn't "boring noise." It's a genuinely rich information-destroying machine. The problem was mine: I was asking one scalar to do philosophy. It won't.
