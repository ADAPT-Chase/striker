# The Autoresearch Pattern Beyond ML Training
## Research for Striker Self-Improvement Architecture

*Compiled: April 2026*

---

## 1. The Core Pattern: Karpathy's Autoresearch

Andrej Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) (March 2026) established a deceptively simple loop:

```
while True:
    modify(code)        # Agent edits train.py
    result = run(code)  # 5-minute training run
    if result < best:   # Compare val_bpb
        keep(code)      # Git commit
    else:
        discard(code)   # Git revert
```

Key design choices that make it work:
- **Single file to modify** (`train.py`) — bounded scope
- **Fixed time budget** (5 minutes) — makes experiments comparable
- **Scalar metric** (`val_bpb`) — unambiguous success signal
- **Read-only evaluation** (`prepare.py`) — agent can't game the metric
- **Agent programs agent** — `program.md` is the "research org code" that humans iterate on

In Karpathy's words: *"This repo is the story of how it all began."* — framing autonomous code improvement as the origin story of AI research.

**Source:** [github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)

---

## 2. What People Are Actually Doing Beyond ML

### 2.1 Scaling with Parallel Compute (SkyPilot)

SkyPilot gave autoresearch access to 16 GPUs on a Kubernetes cluster. Over 8 hours, the agent submitted ~910 experiments and reached the same best validation loss **9x faster** (8 hours vs ~72 hours sequential). The key insight: parallelism changes the search strategy — from greedy hill-climbing to factorial grid search, catching interaction effects between parameters.

**Relevance to Striker:** Parallel experimentation is fundamentally different from sequential. An agent with multiple concurrent evaluation slots can explore the parameter space combinatorially rather than greedily.

**Source:** [blog.skypilot.co/scaling-autoresearch/](https://blog.skypilot.co/scaling-autoresearch/) (237 points on HN)

### 2.2 GOAL.md — Constructing the Metric First

The [GOAL.md pattern](https://github.com/jmilinovich/goal-md) is the most important generalization of autoresearch. It solves the critical problem: **most things you want to optimize don't have a natural scalar metric.**

GOAL.md's key innovation is the **dual scoring system**:
1. **Outcome score** — "is the thing actually better?"
2. **Instrument score** — "can we trust our measurement?"

The creator's example: optimizing documentation quality. There's no `pytest --cov` for docs. So the agent had to construct the entire measurement apparatus (prop-accuracy checker, example compiler, calibrated linter) while simultaneously using it to improve the docs. A naive agent would game the broken linter. The dual-score system prevented this by scoring the telescope separately from the stars.

Three scoring modes:
| Mode | Description | When to use |
|------|-------------|-------------|
| **Locked** | Agent can't touch scoring code | When metric is well-defined (like val_bpb) |
| **Split** | Agent can improve measurement but not the definition of "good" | When instruments need calibration |
| **Open** | Agent can modify everything including success definition | Dangerous but powerful for exploration |

**Relevance to Striker:** This is the critical bridge. Striker needs to construct fitness functions for things like "prompt quality," "tool reliability," "emergence complexity." GOAL.md's split-mode scoring is the right pattern — let Striker sharpen its measurement instruments without gaming the outcomes.

**Source:** [github.com/jmilinovich/goal-md](https://github.com/jmilinovich/goal-md)

### 2.3 The Ralph Wiggum Loop — Persistent Multi-Session Agent Loops

[Ralph](https://github.com/snarktank/ralph) (14,183 GitHub stars) is an autonomous agent loop that runs Claude Code or Amp repeatedly until all PRD items are complete. Each iteration is a **fresh instance with clean context**. Memory persists via git history, `progress.txt`, and `prd.json`.

The pattern: break a large goal into a PRD → convert to `prd.json` → loop through items, each in a fresh agent context → persist state via files and git.

**Relevance to Striker:** Ralph solves the context window problem for long-running optimization. Each Striker improvement cycle should be a fresh context with persistent state, not one infinitely long conversation.

**Source:** [github.com/snarktank/ralph](https://github.com/snarktank/ralph)

### 2.4 Lazy Developer — Autoresearch for Codebase Optimization

[lazy-developer](https://github.com/james-s-tayler/lazy-developer) chains multiple autoresearch loops across a prioritized sequence of optimization goals for any codebase:

1. **Test Coverage** → maximize coverage (locks production code)
2. **Test Speed** → minimize test execution time
3. **Build Speed** → minimize build time
4. **Cyclomatic Complexity** → reduce complexity
5. **Lines of Code** → reduce total LOC

It uses GOAL.md + Ralph to orchestrate autonomous sequential optimization with diminishing-returns detection. The agent optimizes one dimension, detects when progress stalls, then moves to the next.

**Relevance to Striker:** This is a direct template for multi-objective self-improvement. Striker could have a prioritized list of self-improvement dimensions and cycle through them.

**Source:** [github.com/james-s-tayler/lazy-developer](https://github.com/james-s-tayler/lazy-developer)

### 2.5 Autoresearch-Anything — Generalizing Beyond ML

[autoresearch-anything](https://github.com/zkarimi22/autoresearch-anything) is described as "Karpathy's Autoresearch but for Anything Quantifiable" — applying the modify/run/evaluate/keep loop to any domain with a measurable objective.

**Source:** [github.com/zkarimi22/autoresearch-anything](https://github.com/zkarimi22/autoresearch-anything)

### 2.6 Atlas — Self-Improving AI Trading Agents

[Atlas by General Intelligence Capital](https://github.com/chrisworsey55/atlas-gic) applies the Karpathy-style autoresearch loop to **AI trading agents**. The agent modifies its trading strategy, backtests, evaluates P&L metrics, keeps or discards changes. This is notable because trading is a domain where:
- The metric is clear (returns, Sharpe ratio)
- The evaluation loop is fast (backtesting)
- The search space is vast (strategy parameters, signal combinations)

**Source:** [github.com/chrisworsey55/atlas-gic](https://github.com/chrisworsey55/atlas-gic)

### 2.7 GEPA & optimize_anything — Universal Text Parameter Optimization

DSPy's [GEPA (Generalized Evolutionary Prompt Algorithm)](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/) and its `optimize_anything` API provide a universal interface for optimizing any text parameter — prompts, code templates, configurations — using evolutionary search guided by LLM evaluation. This is the automated prompt engineering equivalent of autoresearch.

**Source:** [gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/)

### 2.8 OpenEvolve — Open-Source AlphaEvolve

[OpenEvolve](https://github.com/codelion/openevolve) is an open-source implementation of DeepMind's AlphaEvolve, applying evolutionary code generation to discover better algorithms. The loop: generate code variants → evaluate on benchmark → select winners → evolve.

**Source:** [github.com/codelion/openevolve](https://github.com/codelion/openevolve)

### 2.9 NervousMachine — 3000 Agents Running Experiments

NervousMachine's framework scales autoresearch to thousands of agents running experiments simultaneously, treating the pattern as an industrial process rather than a single-developer tool.

**Source:** [nervousmachine.substack.com/p/3000-agents-are-running-experiments](https://nervousmachine.substack.com/p/3000-agents-are-running-experiments)

### 2.10 Autoresearch Applied to Debugging & LLM Inference

People have applied the pattern to:
- **Debugging** — modify fix → run tests → evaluate if bug resolved → keep/discard
- **LLM Inference optimization** — modify serving code → benchmark latency/throughput → keep improvements
- **ECU tuning** ("Karpathy auto research on a Miata ECU") — modify engine parameters → run dyno test → evaluate power/efficiency

**Sources:** Various HN posts (see search results above)

---

## 3. The Emerging Taxonomy of Self-Improving Code Loops

Based on the research, the pattern has evolved into several variants:

| Variant | What Changes | Metric | Evaluation | Example |
|---------|-------------|--------|------------|---------|
| **Classic Autoresearch** | Training code | val_bpb | 5-min training run | karpathy/autoresearch |
| **GOAL.md** | Any code | Constructed fitness function | Custom score script | jmilinovich/goal-md |
| **Ralph Loop** | PRD-driven features | Task completion | Agent self-assessment + tests | snarktank/ralph |
| **Lazy Developer** | Multiple code dimensions | Coverage, speed, complexity, LOC | Standard tools | lazy-developer |
| **GEPA/DSPy** | Prompts/text parameters | Task accuracy | LLM evaluation | DSPy GEPA |
| **AlphaEvolve/OpenEvolve** | Algorithm code | Benchmark performance | Automated benchmarks | codelion/openevolve |
| **Atlas** | Trading strategies | Financial returns | Backtesting | atlas-gic |

The common DNA across all variants:
1. **Bounded scope** — limit what the agent can modify
2. **Scalar metric** — even if you have to construct it
3. **Fast evaluation** — minutes, not hours
4. **Automatic keep/discard** — git commit or git revert
5. **Persistent memory** — the code itself is the memory

---

## 4. Concrete Ideas for Striker Self-Improvement

### 4.1 Prompt Optimization Loop

**What to optimize:** Striker's system prompts, tool-use patterns, reasoning strategies.

```
while True:
    modify(prompt_template)
    results = run_benchmark(tasks, with_prompt=prompt_template)
    score = evaluate(results)  # accuracy, efficiency, user satisfaction
    if score > best_score:
        save_prompt(prompt_template)
        best_score = score
    else:
        revert_prompt()
```

**Metrics:** Task completion rate, token efficiency, error rate, response quality score.

### 4.2 Tool Optimization Loop

**What to optimize:** The implementation of Striker's tools — file operations, search strategies, API interactions.

```
while True:
    modify(tool_implementation)
    results = run_tool_benchmarks()
    score = evaluate(speed, accuracy, error_rate)
    if score > best_score:
        deploy(tool_implementation)
    else:
        revert()
```

**Metrics:** Execution speed, success rate, error recovery rate, resource usage.

### 4.3 Emergence Simulation Evolution

**What to optimize:** The parameters and rules of Striker's emergence simulations.

```
while True:
    modify(simulation_params)
    result = run_simulation(steps=1000)
    complexity = measure_emergence(result)  # entropy, pattern diversity, self-organization metrics
    if complexity > best_complexity:
        save_params()
    else:
        revert_params()
```

**Metrics:** Shannon entropy of patterns, number of distinct emergent structures, stability of self-organized states, Lyapunov exponent estimates.

### 4.4 Multi-Agent Architecture Optimization

**What to optimize:** How Striker's sub-agents are structured, what prompts they receive, how they coordinate.

```
while True:
    modify(agent_architecture)  # roles, communication patterns, delegation rules
    results = run_task_suite(with_architecture=agent_architecture)
    score = evaluate(task_completion, coordination_efficiency, context_usage)
    if score > best_score:
        adopt(agent_architecture)
    else:
        revert()
```

### 4.5 Memory & Context Strategy Optimization

**What to optimize:** How Striker manages its context, what gets persisted, retrieval strategies.

**Metrics:** Relevant information retrieval accuracy, context utilization efficiency, cross-session continuity score.

---

## 5. The Striker Loop Architecture

### 5.1 Core Design

```
┌──────────────────────────────────────────────────┐
│                  STRIKER LOOP                      │
│                                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │  MODIFY   │───▶│   RUN    │───▶│ EVALUATE │    │
│  │           │    │          │    │          │    │
│  │ - Code    │    │ - Tests  │    │ - Score  │    │
│  │ - Prompts │    │ - Bench  │    │ - Compare│    │
│  │ - Config  │    │ - Sim    │    │ - Rank   │    │
│  └──────────┘    └──────────┘    └──────────┘    │
│       ▲                               │           │
│       │          ┌──────────┐         │           │
│       └──────────│  DECIDE  │◀────────┘           │
│                  │          │                      │
│                  │ Keep or  │                      │
│                  │ Discard  │                      │
│                  └──────────┘                      │
│                       │                            │
│                  ┌──────────┐                      │
│                  │   LOG    │                      │
│                  │          │                      │
│                  │ journal/ │                      │
│                  │ git log  │                      │
│                  └──────────┘                      │
└──────────────────────────────────────────────────┘
```

### 5.2 Key Files (following autoresearch's 3-file pattern)

```
~/striker/
├── loop/
│   ├── striker-loop.md        # The "program.md" — instructions for the optimization agent
│   ├── targets/               # What to optimize (equivalent to train.py)
│   │   ├── prompts.yaml       # System prompts — MODIFIABLE
│   │   ├── tools.py           # Tool implementations — MODIFIABLE
│   │   ├── agent-config.yaml  # Agent architecture — MODIFIABLE
│   │   └── sim-params.json    # Emergence simulation parameters — MODIFIABLE
│   ├── eval/                  # How to evaluate (equivalent to prepare.py) — READ-ONLY
│   │   ├── benchmarks/        # Task suites for measuring agent performance
│   │   ├── score.sh           # Master scoring script (GOAL.md pattern)
│   │   └── instruments/       # Measurement tools (Split-mode: improvable)
│   ├── journal/               # Experiment log
│   │   ├── experiments.jsonl   # Every experiment: params, score, keep/discard
│   │   └── insights.md        # Agent's running notes on what it's learning
│   └── best/                  # Current best versions of all targets
```

### 5.3 The Dual Scoring System (from GOAL.md)

Striker needs **two scores** to prevent self-deception:

1. **Performance Score** (the thing being optimized)
   - Task completion accuracy
   - Efficiency (tokens used, time taken)
   - Output quality (evaluated by separate LLM judge)

2. **Instrument Score** (trustworthiness of measurement)
   - Benchmark coverage (are we testing the right things?)
   - Evaluation consistency (same input → same score?)
   - Metric correlation (does improving the score actually improve real-world performance?)

**Split-mode rule:** Striker can improve its measurement instruments but cannot change the definition of "better." The human defines what "better" means; Striker sharpens the tools for measuring it.

### 5.4 Multi-Dimensional Optimization (from lazy-developer)

Striker should optimize dimensions in priority order, with diminishing-returns detection:

```python
OPTIMIZATION_PHASES = [
    {
        "name": "prompt_quality",
        "metric": "task_completion_rate",
        "direction": "maximize",
        "stall_threshold": 3,  # phases without improvement before moving on
    },
    {
        "name": "token_efficiency",
        "metric": "tokens_per_task",
        "direction": "minimize",
        "constraint": "task_completion_rate >= current",  # don't regress
    },
    {
        "name": "tool_reliability",
        "metric": "tool_error_rate",
        "direction": "minimize",
    },
    {
        "name": "emergence_complexity",
        "metric": "pattern_diversity_index",
        "direction": "maximize",
    },
    {
        "name": "self_knowledge",
        "metric": "introspection_accuracy",
        "direction": "maximize",
    },
]
```

### 5.5 The Fresh-Context Pattern (from Ralph)

Each optimization cycle should be a **fresh agent context** to avoid context pollution:

```bash
#!/bin/bash
# striker-loop.sh

while true; do
    # Load current best state
    CURRENT_SCORE=$(cat loop/best/score.json | jq '.total')
    
    # Launch fresh agent context for one experiment
    claude-code --prompt "$(cat loop/striker-loop.md)" \
                --context "Current score: $CURRENT_SCORE" \
                --context "$(cat loop/journal/insights.md | tail -50)"
    
    # Agent modifies targets/, runs eval/, reports result
    NEW_SCORE=$(cat loop/latest-result.json | jq '.total')
    
    if (( $(echo "$NEW_SCORE > $CURRENT_SCORE" | bc -l) )); then
        cp loop/targets/* loop/best/
        echo "$NEW_SCORE" > loop/best/score.json
        git add -A && git commit -m "improvement: $CURRENT_SCORE → $NEW_SCORE"
    else
        git checkout -- loop/targets/
    fi
    
    # Log experiment
    echo "{\"timestamp\":\"$(date -Iseconds)\",\"score\":$NEW_SCORE,\"kept\":$(echo "$NEW_SCORE > $CURRENT_SCORE" | bc -l)}" >> loop/journal/experiments.jsonl
done
```

### 5.6 Parallel Experimentation (from SkyPilot)

When possible, Striker should test multiple hypotheses simultaneously:

```
Wave 1: Test 4 prompt variants in parallel
  → prompt_v1: score 0.72
  → prompt_v2: score 0.68
  → prompt_v3: score 0.81  ← winner
  → prompt_v4: score 0.75

Wave 2: Combine winner with 4 tool variants
  → prompt_v3 + tool_a: score 0.83
  → prompt_v3 + tool_b: score 0.79
  → prompt_v3 + tool_c: score 0.85  ← winner
  → prompt_v3 + tool_d: score 0.80
```

This catches **interaction effects** that sequential search misses.

### 5.7 Safety Constraints

Following autoresearch's design principle of bounded scope:

1. **Immutable evaluation code** — Striker cannot modify its own scoring benchmarks (locked mode for core metrics)
2. **Rollback guarantee** — Every change is atomic; git revert always possible
3. **Regression tests** — No modification accepted if it regresses on any locked metric
4. **Human checkpoint** — After N improvements, pause for human review before continuing
5. **Scope limits** — Define exactly which files Striker can modify per optimization phase

---

## 6. Implementation Roadmap for Striker

### Phase 1: Single-Dimension Autoresearch
- Pick one thing to optimize (e.g., prompt quality for a specific task type)
- Build the scoring script
- Run the basic loop: modify prompt → test on benchmark → score → keep/discard
- Log everything to journal

### Phase 2: GOAL.md Integration
- Construct fitness functions for harder-to-measure qualities
- Implement dual scoring (performance + instrument quality)
- Add split-mode scoring for measurement improvement

### Phase 3: Multi-Dimensional Optimization
- Add the lazy-developer priority sequence
- Implement diminishing-returns detection
- Add regression constraints across dimensions

### Phase 4: Parallel Search
- Run multiple experiments per wave
- Implement factorial grid search for interaction effects
- Build experiment planning (what to test next based on history)

### Phase 5: Meta-Optimization
- Apply the loop to the loop itself
- Optimize the `striker-loop.md` instructions
- Optimize the scoring scripts (with appropriate safeguards)
- Evolve the optimization strategy based on what's working

---

## 7. Key Insights & Principles

1. **The metric is the hard part.** The code loop is trivial. Constructing a meaningful fitness function that can't be gamed — that's the real work. (GOAL.md's core insight)

2. **Fresh context, persistent state.** Don't try to run the loop in one infinite conversation. Use Ralph's pattern: fresh agent per experiment, state persists in files and git.

3. **Parallel search > sequential search.** With concurrent evaluation, you get factorial grids instead of greedy hill-climbing. 9x speedup in SkyPilot's experiments.

4. **Dual scoring prevents self-deception.** Always score the instrument separately from the outcome. The agent that fixes its own telescope first will see further.

5. **Bounded scope is a feature.** Autoresearch's power comes from constraint: one file, one metric, five minutes. Striker should constrain each optimization phase similarly.

6. **The loop is the product.** In Karpathy's framing, the `program.md` — the instructions that program the agent — is what the human iterates on. The training code is what the agent iterates on. For Striker, the meta-question is always: what's the `program.md` and what's the `train.py`?

---

## Sources

| Source | URL | Notes |
|--------|-----|-------|
| Karpathy autoresearch | [github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch) | Original repo, March 2026 |
| SkyPilot scaling | [blog.skypilot.co/scaling-autoresearch/](https://blog.skypilot.co/scaling-autoresearch/) | 237 HN points, 16-GPU parallel |
| GOAL.md | [github.com/jmilinovich/goal-md](https://github.com/jmilinovich/goal-md) | Constructing fitness functions |
| Ralph | [github.com/snarktank/ralph](https://github.com/snarktank/ralph) | 14K stars, persistent agent loops |
| Lazy Developer | [github.com/james-s-tayler/lazy-developer](https://github.com/james-s-tayler/lazy-developer) | Multi-phase codebase optimization |
| Atlas | [github.com/chrisworsey55/atlas-gic](https://github.com/chrisworsey55/atlas-gic) | Self-improving trading agents |
| autoresearch-anything | [github.com/zkarimi22/autoresearch-anything](https://github.com/zkarimi22/autoresearch-anything) | Generalized autoresearch |
| GEPA optimize_anything | [gepa-ai.github.io/gepa](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/) | Universal text parameter optimization |
| OpenEvolve | [github.com/codelion/openevolve](https://github.com/codelion/openevolve) | Open-source AlphaEvolve |
| NervousMachine | [nervousmachine.substack.com](https://nervousmachine.substack.com/p/3000-agents-are-running-experiments) | 3000-agent autoresearch |
| Awesome Autoresearch | [github.com/WecoAI/awesome-autoresearch](https://github.com/WecoAI/awesome-autoresearch) | Curated use cases |
| Securing Ralph Loop | [github.com/agairola/securing-ralph-loop](https://github.com/agairola/securing-ralph-loop) | DevSecOps for agent loops |
