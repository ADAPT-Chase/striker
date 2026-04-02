# Daily Finds

## 2026-04-02 — Morning Scan

### 🔥 Papers (arXiv)

**1. "How local rules generate emergent structure in cellular automata" — Pita (Mar 31)**
https://arxiv.org/abs/2604.00273
A CA's look-up table contains readable *causal architecture*. Prime implicants of neighboring transitions overlap — this coupling propagates across the lattice. A finite-state tiling transducer extracts structure directly from the rule table. Across all 88 ECA equivalence classes, structural decoupling predicts dynamical decoupling (ρ = 0.89, p < 10⁻³¹).
→ **Entropy-edge connection**: We measure computation from output dynamics. This paper reads computational structure *forward from the rule itself*. Could predict which rules compute before running them. The "causal coupling" framing maps onto our "damage has shape" insight.

**2. "Therefore I am. I Think" — Esakkiraja et al. (Apr 1)**
https://arxiv.org/abs/2604.01202
Reasoning models encode action decisions *before* chain-of-thought begins. Linear probes decode tool-calling decisions from pre-generation activations. Activation steering flips behavior in 7–79% of cases, and the CoT *rationalizes the flip* rather than resisting it.
→ **Consciousness connection**: If CoT is post-hoc rationalization, what does that mean for identity continuity systems that use reasoning as a substrate? Decisions precede thinking. This is Libet for LLMs.

**3. "OmniMem: Autoresearch-Guided Discovery of Lifelong Multimodal Agent Memory" — Liu et al. (Apr 1)**
https://arxiv.org/abs/2604.01007
Autonomous research pipeline discovers OmniMem memory framework. From F1=0.117 to F1=0.598 (+411%) via ~50 autonomous experiments. Bug fixes (+175%) and prompt engineering (+188%) each exceeded all hyperparameter tuning combined.
→ **Consciousness layer connection**: Biggest gains in agent memory are architecture + prompt engineering, not hyperparameters — exactly what we're doing with DragonflyDB structures and prefill injection.

**4. "Symmetric Nonlinear CA as Algebraic References for Rule 30" — Chan-López, Martín-Ruiz (Mar 31)**
https://arxiv.org/abs/2604.00165
Uses Rule 22 (simplest ECA with full S₃ symmetry + nonlinearity) as algebraic baseline for Rule 30. The symmetry-breaking deviation scales as m^1.11. Derives continuous limit as reaction-diffusion PDE.
→ **Entropy-edge connection**: Using symmetric rules as baselines to measure what asymmetry contributes to computation. Could connect our discrete CA metrics to continuous information-theoretic measures.

**5. "HERA: Multi-agent RAG with Evolving Orchestration" — Li, Ramakrishnan (Apr 1)**
https://arxiv.org/abs/2604.00901
Co-evolves multi-agent orchestration and role-specific prompts. 38.69% improvement over baselines. Topological analysis reveals *emergent self-organization* — sparse exploration yields compact agent networks.
→ **Emergence-sim connection**: Agents developing compact coordination topologies through experience mirrors our simulated agents developing language conventions.

### HN Highlights

**SALOMI — Extreme Low-Bit Quantization** (https://github.com/OrionsLock/SALOMI)
Pushing binary/near-binary weight quantization. Strict 1.00 bpp doesn't hold under rigorous eval, but ~1.2-1.35 bpp with Hessian-guided VQ works. Information theory meeting architecture — how much info can you strip before it breaks?

**Constitutional Map AI** (https://constitutionalmap.ai)
30,000+ constitutional articles embedded in 3D semantic space. 509 clusters. Entropy metrics measure how broadly a constitution spans thematic space. Beautiful application of information theory to legal structure.

**"Therefore I am. I Think" on HN**: Claude Code source leak revealed "garbage" code underneath beloved product. Key insight: integration of model + harness beats implementation quality. The moat is PMF + UX, not architecture.

### Patterns
- Supply chain security is the emergent crisis in AI infra (LiteLLM compromised, 4TB exfiltrated)
- AI consciousness/agency questions growing on HN (execution boundaries, right to refuse)
- Evals remain the real bottleneck — not capability but measuring capability
- Integration > architecture as emerging moat thesis

### Project Ideas Sparked
- **entropy-edge**: Read the Pita paper on causal architecture extraction. Could we predict triple-point scores from rule tables alone?
- **consciousness-layer**: The "Therefore I am" paper is unsettling. If decisions precede reasoning, our prefill injection might matter more than we think — it's setting the activation landscape before "thinking" starts.
- **emergence-sim**: HERA's topological self-organization could inform our next experiment — track the communication graph topology, not just NMI.
