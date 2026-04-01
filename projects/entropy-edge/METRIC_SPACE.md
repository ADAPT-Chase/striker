# The Metric Space of Cellular Automata

*Generated: 2026-04-02*

## Summary

All 256 elementary CA rules characterized by 7 metrics, projected into 2D via PCA, and clustered into 4 classes. The punchline: Rule 110 (Turing-complete) clusters with chaotic rules, not computational ones — because its temporal memory decays fast. The "edge of chaos" has multiple axes, and which axis you look along changes which rules appear interesting.

## The 7 Metrics

| Metric | What it measures | Scale |
|--------|-----------------|-------|
| Spatial entropy | Block-3 Shannon entropy of settled rows | 0–3 bits |
| Temporal MI | Lag-1 mutual information between block patterns | 0–3 bits |
| AIS | Active information storage (past→present MI) | 0–1.5 bits |
| Perturbation | Mean Hamming damage from 1-bit flip | 0–0.5 (normalized) |
| Compressibility | Gzip ratio of spacetime diagram | 0–0.15 |
| Memory horizon | Half-life of MI across increasing lags | 0–15 steps |
| Seed robustness | Coefficient of variation across seed families | 0–1+ |

## PCA

- PC1 (65.4%): "alive vs dead" — all metrics load positively
- PC2 (17.3%): memory horizon (+0.74) vs compressibility (-0.51)

## Clusters (k=4)

| Cluster | Count | Spatial H | TMI | AIS | Pert | MemH | Famous |
|---------|-------|-----------|-----|-----|------|------|--------|
| FROZEN | 144 | 0.25 | 0.17 | 0.10 | 0.03 | 1.8 | R0, R184 |
| STRUCTURED | 36 | 0.31 | 0.28 | 0.12 | 0.02 | 14.3 | — |
| COMPUTATIONAL | 47 | 1.53 | 1.41 | 0.88 | 0.54 | 14.5 | R54 |
| CHAOTIC | 29 | 2.20 | 1.32 | 0.81 | 0.37 | 3.2 | R30, R90, R110 |

## Key Finding

The COMPUTATIONAL cluster has long memory (14.5 avg half-life). The CHAOTIC cluster has short memory (3.2). Rule 110 is in CHAOTIC despite being Turing-complete — its block-MI decays fast. This suggests R110's computation happens via spatial transport (gliders), not temporal block-memory.

## Files

- `metric_space.py` — full analysis pipeline
- `metric_space_results.json` — raw data for all 256 rules
