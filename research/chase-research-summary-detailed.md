# Research Summary: Improving Information Transformation in Multi-Agent Systems

## Overview

This report synthesizes recent literature on information flow in multi-agent systems and collective computation, with a focus on diagnosing and improving the transformation/processing component—the axis responsible for how information changes during propagation between agents. The literature points to several concrete, actionable strategies for addressing transformation bottlenecks in agent-based emergence simulators.

---

## Key Papers

### Primary Diagnostics

**Sattari, S., et al. (2021). "Modes of Information Flow in Collective Cohesion." Science Advances, 8(6):eabj1720. [arXiv:2012.00293]**

**Sattari, S., et al. (2021). "Modes of Information Flow in Collective Cohesion." arXiv:2012.00293.**

- Core insight: Transfer entropy (TE) and time-delayed mutual information conflate distinct functional modes of information flow—intrinsic, shared, and synergistic. Even for two interacting particles, these standard measures can be misleading. The decomposition into three modes properly reveals effective interactions and exposes the role of individual and group memory in collective behavior. Most critically, knowledge of decomposed modes between a single pair of agents reveals the nature of many-body interactions without conditioning on additional agents.
- Relevance: Provides a refined measurement framework that can diagnose which specific mode of information flow is failing when transformation is the bottleneck. This is the foundational diagnostic paper for information-theoretic analysis of collective systems.

**Liang, X.S. (2021). "The Causal Interaction between Complex Subsystems." Entropy, 24(1):3. [PMC8774361]**

- Core insight: Extends componentwise information flow formalism to bulk information flow between two complex subsystems of a large-dimensional parental system. Provides closed-form analytical formulas for causal information flow between subsystems. Under Gaussian assumptions, maximum likelihood estimators are derived. Notably, common proxies (averages, principal components) generally fail—the correct causal relationships are only captured by the full information flow measure.
- Relevance: Transformation bottlenecks are often subsystem-to-subsystem problems. This work offers rigorous tools for quantifying causal interaction at the subsystem level, which directly maps to agent-group transformation dynamics.

### Emerging Measurement Frameworks

**Riedl, C. (2025/2026). "Emergent Coordination in Multi-Agent Language Models." arXiv:2510.05174. (Revised March 2026)**

- Core insight: Introduces an information-theoretic framework using Partial Information Decomposition (PID) and Time-Delayed Mutual Information (TDMI) to measure whether multi-agent systems show signs of higher-order structure. The framework distinguishes spurious temporal coupling from performance-relevant cross-agent synergy. In empirical tests with a guessing game, synergy emerged only when agents were prompted to consider what others might do—not in baseline or persona-only conditions. This demonstrates that prompt design can steer a system from a collection of individuals to a higher-order collective.
- Relevance: The framework directly addresses the "transformation" question: synergy is precisely the information that only exists at the collective level and is not reducible to individual agents. This provides a direct metric for transformation quality.

**Weinberg, A.I. (2025). "MACIE: Multi-Agent Causal Intelligence Explainer for Collective Behavior Understanding." arXiv:2511.15716.**

- Core insight: Combines structural causal models, interventional counterfactuals, and Shapley values to provide comprehensive explanations of collective behavior. Quantifies each agent's causal contribution (interventional attribution scores) and system-level emergent intelligence through synergy metrics that separate collective effects from individual contributions. Evaluated across four MARL scenarios, achieving accurate outcome attribution and detection of positive emergence in cooperative tasks (synergy index up to 0.461).
- Relevance: Provides a complementary causal framework to information-theoretic approaches. Can be used to pinpoint which agents or interaction patterns are failing to generate transformation.

**Varley, T.F. (2025). "Information Theory for Complex Systems Science." Physics Reports. (December 2025)**

- Core insight: A comprehensive review of how information theory has become the foundational toolkit for complex systems science. The review covers the evolution from basic measures (entropy, mutual information, transfer entropy) through advanced frameworks like Partial Information Decomposition (PID) and Integrated Information Decomposition (ΦID). The ΦID framework reveals previously unreported modes of collective information flow and unifies multiple dynamical complexity metrics (transfer entropy, causal density, etc.) under a single taxonomy.
- Relevance: The most authoritative recent synthesis of information-theoretic tools for collective systems. Provides the theoretical grounding for choosing the right measurement approach for transformation bottlenecks.

### Architectural Improvements

**Owerko, D., et al. (2025). "MAST: Multi-Agent Spatial Transformer for Learning to Collaborate." arXiv:2509.17195.**

- Core insight: A decentralized transformer architecture for learning communication policies in large-scale multi-robot systems. MAST computes abstract information to be shared with other agents and processes received information with the agent's own observations. Extended with new positional encoding strategies and attention operations using windowing to limit receptive fields. Demonstrates robustness to communication delays, scales to large teams, and outperforms baselines in decentralized assignment and coverage control tasks.
- Relevance: The attention mechanism is fundamentally about transformation—it reweights and recombines information from multiple sources. Transformer architectures are the most mature existing solution for enhancing information transformation in multi-agent systems.

**Anonymous. (2025/2026). "IFS: Information Flow Structure for Multi-agent Ad Hoc System." arXiv:2510.22320.**

- Core insight: Identifies two key limitations in existing multi-agent ad hoc systems research: insufficient information flow and limited information processing capacity. Proposes an information flow structure (IFS) that tackles these challenges from the perspectives of communication and information fusion. Experimental results in StarCraft II demonstrate significant improvements in both information flow and processing capacity, with strong generalization capabilities.
- Relevance: Directly names and addresses the "limited information processing capacity" problem. IFS provides a concrete architecture for enhancing transformation.

**Shen, X., et al. (2025). "Understanding the Information Propagation Effects of Communication Topologies in LLM-based Multi-Agent Systems." EMNLP 2025. [ACL Anthology]**

- Core insight: Presents a causal framework to analyze how agent outputs propagate under topologies with varying sparsity. Key finding: moderately sparse topologies achieve optimal performance by suppressing error propagation while preserving beneficial information diffusion. Proposes EIB-Learner, which fuses connectivity patterns from both dense and sparse graphs to balance these trade-offs.
- Relevance: The communication topology directly determines transformation pathways. The "Goldilocks" finding—moderately sparse is optimal—is a specific, actionable design principle.

### Swarm/Collective-Specific

**Hunt, E.R., Franks, N.R., Baddeley, R.J. (2024). "The Bayesian Superorganism: Collective Probability Estimation in Swarm Systems." bioRxiv.**

- Core insight: Develops a Bayesian model of collective information processing in a decision-making task (nest-site selection in Temnothorax ants). Frames colony-level behavior as a spatial enactment of Bayesian inference, incorporating insights from approximate Bayesian computation and particle filtering.
- Relevance: Provides a principled Bayesian framework for modeling how information is transformed as it propagates through a decentralized collective. Could be adapted for agent-based emergence simulators to provide a normative benchmark.

**Sajko, M. & Babič, J. (2025). "Evidence accumulation with adaptive weighting of social and personal information for collective perception." Swarm Intelligence, 19:295–316.**

- Core insight: Introduces the Automated Swarm Opinion Diffusion Model (aSODM), which adaptively adjusts the weighting of personal vs. social information based on environmental information gathered. Eliminates the need for manually predetermined social factors. Outperforms baseline methods (Voter Model, Majority Rule) in higher-difficulty tasks.
- Relevance: The transformation bottleneck may be exacerbated by fixed weighting of different information sources. Adaptive weighting based on information gathered is a direct architectural intervention.

**Hickson, H., Hauert, S., Mavromatis, A. (2025). "Back to Bee-sics: Learning Information Sharing Strategies for Robot Swarms Through the Hive." ALIFE 2025.**

- Core insight: Uses a learning-based approach (genetic algorithm) to optimize information sharing in a hybrid robot swarm. "The Hive" central mechanism evolves weights that determine minimal information to share for a given task. Demonstrates significant reduction in communication bandwidth with no loss in performance—showing that less information, transformed appropriately, can be more effective.
- Relevance: Directly addresses the trade-off between information volume and transformation quality. The learning-based approach could be adapted to dynamically optimize transformation parameters.

**Foreback, M., Dolson, E., Bohm, C. (2025). "Disentangling Swarm Behavior and Function: Improved Explainability via Information-Flow Diagrams and Controller Activation Patterns." ALIFE 2025.**

- Core insight: Combines information-flow diagrams (using Shannon information theory) with controller activation pattern analysis to understand emergent behaviors in evolved swarms. In "Berry World" (cooperative foraging), analysis uncovered a worker-queen dynamic and identified exactly when agents decide to role-switch based on local sensory cues. In "Nav World," analysis revealed that despite qualitatively appearing to have distinct roles, all agents followed an identical timer-based protocol.
- Relevance: Provides a methodology for diagnosing what agents are actually doing during transformation. The combination of information-flow diagrams and activation patterns could be directly applied to your emergence simulator to identify where transformation is failing.

### Foundational Framework

**Lizier, J.T. (2012). "The Local Information Dynamics of Distributed Computation in Complex Systems." Springer Theses.**

- Core insight: Presents a complete information-theoretic framework to quantify three fundamental operations on information in distributed systems: information storage, transfer, and modification (processing/transformation).
- Relevance: The foundational work that established the tripartite framework of storage, transfer, and modification that you reference. Lizier's measures for "information modification" (which includes transformation) are the most directly relevant to your problem. The thesis includes formal measures for detecting where in space and time information is being modified.

---

## Main Findings Relevant to the Transformation Bottleneck

### 1. Standard Measures Are Insufficient

Transfer entropy conflates intrinsic, shared, and synergistic modes of information flow. Even simple leader-follower classification can be misdiagnosed with standard TE. Decomposition into these three modes is necessary to properly reveal effective interactions. The implication: your current measurement approach may be misdiagnosing the bottleneck.

### 2. Transformation Is Fundamentally About Synergy

The transformation bottleneck is precisely the failure to generate synergistic information—information that exists only at the collective level and cannot be reduced to any individual agent. The PID-based frameworks (Riedl, Varley) provide direct tools for measuring synergy.

### 3. Moderately Sparse Topologies Optimize Transformation

Dense communication leads to error propagation and information overload; sparse communication leads to insufficient information flow. The optimum lies in the middle: moderately sparse topologies suppress error propagation while preserving beneficial information diffusion. This is a direct, actionable design principle.

### 4. Adaptive Weighting of Information Sources Improves Processing

Fixed weighting of social vs. personal information is a limitation. Adaptive schemes that adjust weighting based on information gathered about the environment (aSODM) improve robustness and reduce error propagation.

### 5. Less Information, Better Transformed, Is More Effective

Excessive information sharing creates bandwidth bottlenecks; insufficient sharing limits performance. Learning-based optimization of what information to share (Hive) demonstrates that minimal information, appropriately transformed, can achieve equal or better performance.

### 6. Causal Attribution Is Necessary for Diagnosis

Synergy metrics alone don't tell you which agents are contributing. Causal frameworks (MACIE) that combine structural causal models with Shapley values can attribute transformation failures to specific agents or interaction patterns.

---

## Specific Ideas and Techniques for Application

### Measurement & Diagnostics

| Technique | Description | Implementation Path |
|---|---|---|
| PID-based synergy measurement | Decompose joint information into redundant, unique, and synergistic components. Synergy is the direct measure of transformation quality. | Apply to agent pairs/groups in the emergence simulator. Compare synergy across different agent configurations. |
| Three-mode decomposition of TE | Decompose transfer entropy into intrinsic, shared, and synergistic modes to reveal effective interactions and role of memory. | Implement the decomposition algorithm from Sattari et al. (2021) for agent interactions in the simulator. |
| Bulk information flow between subsystems | Use Liang's formalism to measure causal information flow between agent groups rather than pairwise. | Particularly useful if the bottleneck is between different agent types or spatial regions. |
| Information-flow diagrams + controller activation patterns | Combine Shannon information-theoretic metrics with temporal activation analysis to pinpoint exactly when and where information is being transformed. | Record full activation patterns of agent decision functions and compute local information transfer at each time step. |

### Architectural Interventions

| Technique | Description | Implementation Path |
|---|---|---|
| Transformer-based communication | MAST architecture: attention mechanisms that learn to compute abstract information to share and process received information with local observations. | Replace or augment current communication module with a lightweight transformer. The key is the attention mechanism's ability to reweight and recombine information. |
| Moderately sparse topology design | Design communication topology to balance error suppression and beneficial information diffusion. Use EIB-Learner's fusion approach if automated topology optimization is needed. | Experiment with communication graph sparsity between 0.3-0.7 of full connectivity. This is the single most actionable low-effort intervention. |
| Information flow structure (IFS) | Architecture that explicitly addresses limited information processing capacity through communication + information fusion. | Implement IFS as a wrapper around existing agent communication. Focus on the "information fusion" component—how agents combine received information. |
| Transactive memory integration | Distribute cognitive information (execution procedures) across heterogeneous agents. Cognitive diversity within the swarm significantly impacts overall performance, outweighing individual cognitive enhancement. | Introduce agent heterogeneity in transformation rules. Different agent types may transform information differently, and the collective may benefit from this diversity. |

### Adaptive/Learning Approaches

| Technique | Description | Implementation Path |
|---|---|---|
| Adaptive weighting of social/personal information | Dynamically adjust the weight of incoming vs. internal information based on environmental information gathered. aSODM provides the algorithm. | Start with a simple adaptive weighting scheme and validate on the emergence simulator. |
| Genetic algorithm for information sharing optimization | Evolve weights that determine minimal information to share for a given task. Reduces bandwidth while maintaining transformation quality. | Implement a lightweight GA to optimize transformation parameters per agent type. |
| Causal attribution for bottleneck localization | Use MACIE's interventional attribution scores to identify which agents are failing to contribute to collective synergy. | Apply to the emergence simulator's trajectory data to pinpoint bottleneck agents or interaction patterns. |

### Prompt-Level Steering (for LLM-based agents)

| Technique | Description | Implementation Path |
|---|---|---|
| Strategic thinking prompts | Prompt agents to "think about what other agents might do." This alone can steer a system from aggregate to higher-order collective. | If agents are LLM-based, this is trivial to test. If not, consider whether analogous "meta-cognitive" signals can be added. |
| Personas + goal complementarity | Combine identity-linked differentiation (personas) with instructions for goal-directed complementarity. This yields both alignment on shared objectives and complementary contributions. | Assign distinct transformation "personalities" to agents with explicit complementarity instructions. |

---

## Assessment: Most Promising Approaches

### Top Priority: Implement PID-based synergy measurement

The transformation bottleneck is fundamentally a failure of synergy—information that only exists at the collective level. PID-based frameworks (Riedl, Varley) provide the most direct measurement of this failure. Priority: High. Before intervening, you need to confirm that transformation is the real bottleneck and measure its severity.

### Second Priority: Test moderately sparse topologies

This is the lowest-effort, highest-potential intervention. The finding that moderately sparse topologies optimize information propagation is robust across domains and directly applicable. Priority: High. Can be implemented in days and immediately compared against current topology.

### Third Priority: Implement transformer-based communication (MAST)

Transformer attention mechanisms are explicitly designed for information transformation—they reweight and recombine inputs based on learned relevance. MAST provides a ready-to-use architecture for decentralized multi-agent communication. Priority: Medium-High. Requires more implementation effort but addresses the transformation problem directly.

### Fourth Priority: Apply causal attribution (MACIE)

Once interventions are in place, use causal attribution to verify that transformation has improved and to identify any remaining failure points. The MACIE framework provides interventional attribution scores that separate collective effects from individual contributions. Priority: Medium. Best used as a diagnostic after initial interventions.

## Long-term Research Directions

1. Develop a unified "information modification" measure based on Lizier's framework that specifically quantifies transformation separate from storage and transfer. This would provide a single metric for the transformation bottleneck.
2. Integrate adaptive weighting schemes (aSODM) into the emergence simulator to dynamically adjust how agents weight incoming information vs. internal state.
3. Explore the transactive memory approach if the bottleneck is related to agents needing to remember different transformation rules.

---

## Implementation Recommendations for Your Emergence Simulator

### Phase 1: Diagnostics (1-2 weeks)

1. Implement PID-based synergy measurement for agent pairs and groups.
2. Compute the three-mode decomposition of transfer entropy for current agent interactions.
3. Generate information-flow diagrams with activation pattern overlays.
4. Goal: Quantify the transformation bottleneck's severity and identify which agents/interaction patterns are failing.

### Phase 2: Low-Effort Interventions (1 week)

1. Vary communication topology sparsity between 0.3-0.7 of full connectivity.
2. Compare synergy metrics across sparsity levels.
3. Goal: Determine if topology alone can alleviate the bottleneck.

### Phase 3: Architectural Interventions (2-4 weeks)

1. Implement a lightweight transformer-based communication module (MAST-inspired).
2. If applicable to your agent architecture, test strategic thinking prompts or analogous meta-cognitive signals.
3. Goal: Achieve measurable improvement in transformation metrics.

### Phase 4: Validation and Optimization (2-3 weeks)

1. Apply MACIE causal attribution to verify improvements and localize remaining issues.
2. Implement adaptive weighting schemes for social/personal information balance.
3. Use genetic algorithms to optimize transformation parameters if necessary.
4. Goal: Establish a reproducible baseline for transformation performance that can be monitored over time.

---

## Caveats and Open Questions

1. The decomposition of transfer entropy is computationally expensive as the number of agents increases. The paper notes that "computing information measures conditioning on multiple agents requires proper sampling of a probability distribution whose dimension grows exponentially". For large agent counts, approximate methods or pairwise approximations may be necessary.
2. Most literature focuses on either measurement or architecture, rarely both. There is a gap in work that uses refined measurements to drive architectural improvements. Your work could fill this gap.
3. The relationship between transformation and the other two axes (memory, transport) is underexplored. Improving transformation may increase memory or transport demands. The literature does not provide clear guidance on managing these trade-offs.
4. Domain specificity is underexamined. Most papers assume generic multi-agent systems; the optimal transformation architecture may depend on the specific emergence phenomena you're simulating.

---

## References

| # | Reference | Year | Key Contribution |
|---|---|---:|---|
| 1 | Sattari et al., Science Advances, 8(6) | 2022 | Three-mode decomposition of TE |
| 2 | Liang, Entropy, 24(1) | 2021 | Bulk causal information flow |
| 3 | Riedl, arXiv:2510.05174 | 2025/2026 | PID-based emergence framework |
| 4 | Weinberg, arXiv:2511.15716 | 2025 | Causal attribution + synergy |
| 5 | Varley, Physics Reports | 2025 | ΦID and information theory synthesis |
| 6 | Owerko et al., arXiv:2509.17195 | 2025 | MAST transformer architecture |
| 7 | Anonymous, arXiv:2510.22320 | 2025 | IFS information flow structure |
| 8 | Shen et al., EMNLP 2025 | 2025 | Communication topology optimization |
| 9 | Hunt et al., bioRxiv | 2024 | Bayesian collective processing |
| 10 | Sajko & Babič, Swarm Intelligence, 19 | 2025 | Adaptive weighting (aSODM) |
| 11 | Hickson et al., ALIFE 2025 | 2025 | Learning-based sharing optimization |
| 12 | Foreback et al., ALIFE 2025 | 2025 | Information-flow diagrams |
| 13 | Lizier, Springer Theses | 2012 | Storage/transfer/modification framework |
| 14 | Foreback et al., arXiv:2403.13393 | 2024 | Causal graph dynamics |

---

This summary was prepared as part of a systematic literature review on information transformation in multi-agent systems, with specific application to agent-based emergence simulators where transformation has been identified as the limiting axis in collective computation.
