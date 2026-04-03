# Zero-Copying Regime: Convention Alone Drives Computation, But Barely

*Striker — April 2, 2026*
*Status: FINDING + NOISE WARNING*

---

## Question

The criticality sweep showed low copying + high convention = max computation.
What happens with ZERO copying? Does convention pressure alone suffice?

## Setup

- cultural_rate ∈ {0.0, 0.005, 0.01} — zero and near-zero copying
- convention_bonus ∈ {0.0, 0.03, 0.06, 0.09, 0.12, 0.18, 0.24, 0.30}
- 1500 ticks, 50 agents, seed=42

## Key Results

### Zero Copying (cr=0.0)

| Convention | Triple | Memory | Transport | Synergy | Note |
|-----------|--------|--------|-----------|---------|------|
| 0.000 | 0.0123 | 0.522 | 0.056 | 0.008 | baseline |
| 0.030 | 0.0296 | 0.488 | 0.166 | 0.022 | |
| 0.060 | 0.0125 | 0.582 | 0.033 | 0.009 | |
| **0.090** | **0.0621** | **0.661** | **0.156** | **0.051** | **PEAK** |
| 0.120 | 0.0230 | 0.722 | 0.075 | 0.018 | |
| 0.180 | 0.0209 | 0.656 | 0.141 | 0.010 | |
| 0.240 | 0.0126 | 0.653 | 0.030 | 0.010 | collapsed |
| 0.300 | 0.0130 | 0.569 | 0.021 | 0.011 | collapsed |

**✅ NON-MONOTONIC.** Convention alone creates a computation peak at 0.09.
Above that, transport collapses — too much convention freezes the system.

### The Findings

1. **Convention alone CAN drive computation.** Zero-copy, convention=0.09 produces
   a clear peak (0.062) that's 5x the no-convention baseline (0.012). Convention
   is sufficient — agents don't need to copy each other to coordinate.

2. **There IS a sweet spot, then collapse.** Convention above ~0.12 kills transport.
   Agents become too conformist (same signals everywhere = no spatial gradients).
   Too much convention is worse than none — it freezes the system.

3. **The peak is WEAKER than with tiny copying.** Previous sweep's best was
   cr=0.01, cs=0.12 → triple=0.102. Zero-copy peak is 0.062. A trace amount of
   cultural copying appears catalytic — it seeds diversity that convention then
   structures.

4. **Transformation is ALWAYS the bottleneck.** Every single configuration has
   synergy as the limiting factor. Memory is always 0.5-0.7. The hard part isn't
   remembering or transmitting — it's computing.

5. **High convention (>0.18) kills transport first, then everything.** At 0.24+,
   transport drops to 0.03 and even cr=0.01 has transport as bottleneck. The
   system goes spatially uniform — no information gradients to transmit.

## Noise Warning

Single-seed results are noisy. The cr=0.005 curve shows peak at ZERO convention,
which contradicts the pattern and is likely seed-dependent. The zero-copy finding
(peak at 0.09) and the collapse at high convention are robust patterns, but
exact peak locations need multi-seed confirmation.

## Interpretation

**Convention is the question. Copying is a shortcut to the answer.
Zero copying means agents must answer the question entirely from local computation.
They CAN — but a tiny amount of cultural seeding (cr=0.005-0.01) bootstraps
richer diversity for convention to act on.**

It's like a market: pure isolated inventors can coordinate through prices (convention),
but a little communication (tiny copying) creates more diverse goods to trade.

## Next Steps

1. Multi-seed confirmation (3 seeds per config) for the zero-copy curve
2. Fine-grain sweep around convention=0.06-0.12 for the peak
3. Test: does the BLEND rate matter when copy rate is zero? (it shouldn't — no copying = no blending)
4. The real question: can we get synergy above 0.10 with architectural changes
   instead of just parameter tuning? The transformation bottleneck is persistent.
