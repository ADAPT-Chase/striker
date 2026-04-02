# Literature on Transformation Bottlenecks in Multi-Agent Collective Computation (2023–2026)

## Executive synthesis of what the bottleneck most likely is

In the information-dynamics framing commonly used for distributed computation, system capability is often discussed as a combination of **information storage**, **information transfer**, and **information modification** (sometimes described as “processing” or “transformation”). citeturn2search32turn2search36

Given your observation that **memory and transport are strong** but **transformation during spatial propagation is the limiting axis**, the closest match in this literature is that the swarm has plenty of (a) **self-predictability** and (b) **directed influence**, but it is not generating enough **new, task-relevant information at interaction sites**—i.e., it is stuck in a regime dominated by **copying/averaging/relaying** (redundancy) rather than **nonlinear multi-source integration** (synergy / modification). This is precisely the gap that recent work on **partial information decomposition (PID)**, **O-information**, and **information-bottleneck-based decompositions** tries to quantify at scale. citeturn5search8turn5search2turn13search2turn5search7

A key implication (and a recurring warning in recent papers) is that “more information flowing” is not automatically “better computation.” For example, recent theoretical work on collective patterning finds that globally optimized collective outcomes do **not necessarily** correspond to maximizing inter-cell information transfer—objectives can trade off speed/accuracy and time-varying information flow in unintuitive ways. citeturn8search4turn8search2

## Measurement and diagnostics that separate transport from transformation

Transfer entropy (TE) remains a standard tool for measuring directed information flow, but several recent works highlight that **TE can be misleading when targets have strong self-memory**—which is exactly your regime (“memory is strong”). A 2025 *Scientific Reports* paper proposes and evaluates a **modified transfer entropy** (MT) intended to reduce delay-dependent artifacts introduced by target memory and uses it to distinguish direct vs indirectly mediated interactions in Vicsek-like and Langevin dynamics settings. citeturn20view0

This matters for your simulator because a perceived “transformation bottleneck” can be an artifact of measurement: if you rely on pairwise TE with an embedding/delay choice that is dominated by the target’s own predictability, you can underestimate (or misattribute) causal influence pathways. The MT framing specifically calls out that standard TE’s behavior over delays can become complicated under strong target memory, while MT’s formulation is designed to avoid that moving “support” issue. citeturn20view0

For diagnosing where “transport” is happening but not producing downstream change, a complementary direction is **transfer-entropy decomposition using information bottleneck ideas**. A 2024 arXiv paper (“Which bits went where?”) proposes localizing TE on both sides of an interaction (origin in the source’s past vs terminus in the target’s future) using an information-bottleneck-style learned compression, explicitly distinguishing itself from the **Transfer Entropy Bottleneck** (TEB) approach. citeturn12view0turn13search0  
This is directly useful in your context because it can answer: *Is information entering the receiver but getting “washed out” by the receiver’s update rule? Or is it already redundant before it arrives?* citeturn12view0

Because most agent simulators produce **continuous, moderately high-dimensional state vectors**, the last ~2 years have seen practical progress on TE estimation in those settings. **TREET** (2024) introduces a transformer-based neural TE estimator designed for high-dimensional continuous processes using a Donsker–Varadhan-style objective, explicitly motivated by the practical limitations of classic estimators in high dimensions. citeturn10search0turn22search6  
**TENDE** (arXiv 2025; positioned for AISTATS 2026) uses score-based diffusion models to estimate TE via conditional mutual information, targeting curse-of-dimensionality issues and reducing reliance on restrictive assumptions. citeturn22search3turn11view0

On the “tooling” side, **IDTxl** is still one of the most practical off-the-shelf toolkits for quickly moving from time series to (a) multivariate TE network inference and (b) related information-dynamics quantities, and it has recent releases in the 2024–2025 window. citeturn10search2turn10search6turn10search10  
Practically, multivariate TE (parent/driver selection) is often the difference between “everyone looks influential (pairwise TE)” and “here are the few sources that actually add predictive power beyond others.” citeturn10search10turn10search19

To measure “transformation” rather than “transport,” recent progress is strongest in **synergy/redundancy** quantification:

- **Partial Information Rate Decomposition (PIRD)** (PRL 2025; arXiv 2025) is explicitly motivated by PID’s widespread use on multivariate time series despite PID’s original definition for random variables, introducing a rate-based framework for dynamic networks. citeturn5search0turn5search8  
- **SΩI** (2024) introduces score-based estimation of **O-information**, a scalable synergy–redundancy balance metric intended to work beyond simplified assumptions that historically limited O-information’s practical use. citeturn5search2turn5search10  
- A 2024 Nature-portfolio paper proposes a “synergy-first backbone” decomposition for higher-order dependencies, which (conceptually) aligns well with “find the multi-agent subsets where transformation is actually happening.” citeturn5search7

## Mechanistic levers from collective behavior and swarm robotics that plausibly raise transformation

A recurring mechanistic theme in collective systems is that the biggest gains often come not from changing what’s transmitted, but from changing **interaction regime and topology**—i.e., *who listens to whom, when, and with what coupling strengths*.

Criticality is one of the strongest recent “knobs” supported by real robotic experiments. A 2023 *Journal of the Royal Society Interface* paper uses up to 50 programmable swarm robots with Vicsek-like interactions and reports that collective response is maximized near a critical state induced by **alignment weight/scale**, while not all order–disorder transitions confer functional advantages. citeturn17view0  
This lines up with your bottleneck framing because “transformation” often requires the swarm to sit at a regime where perturbations and signals are neither damped out (too ordered) nor lost (too disordered), which is the standard intuition behind criticality-for-processing claims. citeturn17view0

Where criticality work becomes actionable is in clarifying *which* parameters matter: the same 2023 robot paper emphasizes that alignment-related coupling parameters are essential, and that noise and other non-alignment factors can highlight (rather than solely create) the functional advantages of alignment-induced criticality. citeturn17view0  
In your simulator, that points to a practical intervention: tune **directional/velocity coupling strength and interaction radius** deliberately to sit near the “functional critical” boundary, rather than indiscriminately increasing noise or bandwidth. citeturn17view0

Topology-specific results in 2025–2026 make this even more concrete. A 2026 *Communications Physics* paper (“Nested interaction network enhances responsiveness…”) argues that nestedness in interaction networks varies with maneuvering context and uses a contagion-model analysis where a **perfectly nested interaction network** achieves high information transfer efficiency; it then proposes a local mechanism to form that nested topology in a self-propelled model and reports improved responsiveness and robustness in collective-turn simulations under noise. citeturn19search0turn19search1turn22search9  
This is one of the most directly actionable recent contributions for a transformation bottleneck because it offers: a measurable structural target (nestedness) → a local rule to generate it → group-level responsiveness and transfer-efficiency outcomes. citeturn19search0turn19search1

Attention/salience-based interaction rules provide another plausible route to increasing transformation: rather than continuously averaging neighbors, agents selectively respond to “surprising” changes that carry new information. A 2024 *Nature Communications* paper proposes a heuristic measure of “motion salience” from first-person relative motion changes and empirically links it to leader–follower structure and future changes in velocity consensus in bird-flocking data. citeturn18search0turn18search3  
Complementing this, a 2025 work on selective interactions regulated by a motion-salience threshold explicitly frames a threshold-based mechanism that switches between an activated state responding to significant cues and an inactive alignment state. citeturn19search3turn19search13  
Mechanistically, these are “transformation amplifiers” because they introduce **nonlinear gating** and **event-driven computation points** where the swarm reacts differently depending on locally detected structure. citeturn18search0turn19search3

Higher-order interactions are another structural lever that, in effect, create more opportunities for multi-source integration (and therefore synergy). A 2024 paper proposes “higher-order topology” (hypergraph interactions between individuals and sub-groups) to improve the responsiveness–persistence trade-off, explicitly moving beyond pairwise interaction patterns. citeturn19search2turn19search5  
Separately, 2023 work in *Nature Communications* shows that higher-order interactions can shape collective dynamics differently depending on whether they are represented as hypergraphs vs simplicial complexes, warning that “just adding group interactions” is not enough—the representation impacts dynamics. citeturn19search22

Finally, a 2025 arXiv paper defines and quantifies “influence” in a modified Vicsek model with non-reciprocal interactions and empirically connects that influence to transfer entropy under fixed noise strengths; it also highlights asymmetric noise effects where noise on “influencers” can enhance information transfer while noise on “followers” suppresses it, and it uses the system as a testbed for PID methods. citeturn9view0turn23search1  
For your simulator, the actionable takeaway is that **stochasticity can be beneficial if it is role- and location-specific** (e.g., exploration/influencer agents) rather than uniformly injected, which can otherwise just wash out transformation at the receivers. citeturn9view0

## Learning-based approaches that operationalize transformation as representation learning

If your simulator can include learned communication or learned update rules, the MARL / multi-agent perception literature provides “transformation objectives” that are much more explicit than most swarm/active-matter models.

A clean example is **Graph Information Bottleneck (GIB)** for multi-agent communication (AAAI 2024), which uses a bottleneck objective to compress communication while retaining information useful for coordination; as a design pattern, this discourages raw copying and pushes messages toward task-relevant transformations. citeturn4search1turn4search0  
A related TPAMI 2024 paper extends GIB-based communication to robustness under perturbations/noise, which is relevant if you intentionally introduce stochasticity to escape local minima in collective computation. citeturn4search16

Causal-influence-driven training is another line that directly targets “causal information flow between agents” rather than correlation. The AAAI 2024 paper **Situation-Dependent Causal Influence-Based Cooperative MARL** (SCIC) proposes an intrinsic reward mechanism based on situation-dependent causal influence measured via causal intervention and conditional mutual information, explicitly trying to learn when/where an agent’s actions influence others and to encourage exploration of those regimes. citeturn4search2turn4search5  
For a transformation bottleneck, this implies a concrete training objective: reward agents for entering states where their actions create nontrivial causal effects on neighbors (a prerequisite for meaningful transformation). citeturn4search2

Finally, multi-agent perception work sometimes encodes “good collaboration” directly as a mutual-information constraint. The AAAI 2024 **CMiMC** framework (“What Makes Good Collaborative Views?”) proposes maximizing mutual information between pre- and post-collaboration features while also optimizing downstream performance, explicitly treating fusion as an information-preserving-but-useful transformation rather than an opaque averaging step. citeturn4search3turn4search6  
Even if your system is not doing perception, the design pattern transfers: treat “receiver aggregation” as a learned encoder trained to preserve discriminative information from multiple neighbors while producing a representation that improves collective-level objectives. citeturn4search3

## Practical experimental playbook for your emergence simulator

A pragmatic approach suggested by this literature is to run a paired set of experiments: **instrumentation to measure transformation correctly**, and **rule/topology interventions** that are likely to increase synergy/modification without simply inflating raw transfer.

For instrumentation, the highest-value upgrade in your “memory strong” regime is to validate that your transport metrics are not lying. The 2025 hidden-mediator paper makes a concrete case that TE’s delay dependence can become complicated under strong target memory and that modified TE can better reflect causal influence vs delay. citeturn20view0  
In practice, that translates into: compare (a) pairwise TE, (b) modified TE, and (c) multivariate TE (parent selection) on the same runs before you interpret “transport vs transformation” conclusions. citeturn20view0turn10search10turn10search19

For transformation measurement, pick one synergy-capable metric that matches your data regime. If you can work with limited neighborhood size (e.g., each agent aggregates from k=2…5 neighbors), rate-aware PID frameworks like PIRD are directly motivated by the need to treat multivariate time series properly. citeturn5search0turn5search8  
If neighborhood size is larger, scalable synergy–redundancy balance metrics like O-information (and recent score-based estimators) are designed to be more tractable than full PID lattices. citeturn5search2turn5search10

For interventions, the most evidence-backed “low engineering effort” levers in 2023–2026 are:

- **Tune alignment coupling parameters to sit near functional criticality**, because real robot experiments show alignment-induced criticality is where collective response is maximized, and not all order–disorder transitions are beneficial. citeturn17view0  
- **Introduce nestedness / hierarchical listening rules**, because a 2026 study provides both a structural target (nestedness) and a local mechanism that improves responsiveness and transfer efficiency. citeturn19search0turn19search1  
- **Adopt salience-gated interaction updates**, because motion-salience work argues for selective response to meaningful local changes (a natural way to create “transformative events”). citeturn18search0turn19search3  
- **Add limited higher-order interactions** (micro-groups) rather than only pairwise averaging, because recent work explicitly motivates higher-order topology for improved responsiveness and shows that higher-order representation affects dynamics. citeturn19search2turn19search22

If you can use learning, the two most “drop-in” objective templates are (a) an information bottleneck on communication/aggregation (Graph IB) and (b) an intrinsic reward based on state-dependent causal influence (SCIC). citeturn4search1turn4search2

## What looks most promising for your specific bottleneck

The strongest “signal” across the last ~2–3 years is that **interaction architecture** is a first-class variable for collective computation: nestedness, attention/salience gating, and coupling-to-criticality repeatedly show up as mechanisms that change responsiveness and information flow properties at the group level. citeturn19search0turn17view0turn18search0

If your bottleneck is truly “transformation” (not a TE estimation artifact), the most promising combination is: (1) add **selective, nonlinear gating** (salience thresholds) so interactions are not always linear averaging, and (2) modify topology toward **nested/hierarchical structures** so signals propagate efficiently and land in contexts that make multi-source integration possible. citeturn19search0turn19search3turn18search0

Separately, the most important “don’t fool yourself” move is to use a transport metric that respects your strong-memory condition (e.g., compare TE vs MT, and consider multivariate TE tools like IDTxl) so you don’t misdiagnose transport as the limiting axis. citeturn20view0turn10search2turn10search19

## Research summary file

[Download the research summary markdown](sandbox:/mnt/data/striker/research/transformation-bottleneck-literature.md)