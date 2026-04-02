#!/usr/bin/env python3
"""
🧬 DIVERSITY MODULATION EXPERIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hypothesis: Culture creates cognitive diversity, not distributed memory.
            Diversity enables computation (transformation).
            
Test: Artificially increase/decrease agent signal_weight diversity
      and measure its effect on triple-point scores.

Conditions:
  1. NATURAL    — Normal sim with cultural transmission
  2. CLONED     — Every N ticks, force all agents to have same signal_weights 
                  (high conformity, low diversity)
  3. SCRAMBLED  — Every N ticks, randomize each agent's signal_weights 
                  (maximum diversity, no coherence)
  4. GRADIENT   — Force a spatial gradient of signal strategies 
                  (structured diversity)
  5. BASELINE   — No cultural transmission at all

If diversity IS the mechanism:
  - CLONED should kill transformation (conveyor belt)
  - SCRAMBLED should have high transformation but low memory (noise)
  - GRADIENT should maximize triple-point (structured diversity = computation)
  - NATURAL should be between GRADIENT and CLONED
"""

import math
import sys
import json
import random
import copy
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

import sim as emergence_sim
from triple_point_agents import TriplePointAnalyzer


def measure_diversity(agents, num_signals=4) -> Dict:
    """Measure cognitive diversity of the population.
    
    Returns:
        dict with diversity metrics:
        - weight_variance: mean variance of signal_weights across agents per (signal, context)
        - strategy_entropy: entropy of dominant-signal-per-context strategies
        - mean_disagreement: average pairwise strategy disagreement
    """
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    
    # Collect all weight vectors
    weight_vectors = []
    strategies = []
    
    for a in agents:
        if not hasattr(a, 'signal_weights'):
            continue
        vec = []
        strategy = []
        for s in range(num_signals):
            for ctx in contexts:
                w = a.signal_weights.get(s, {}).get(ctx, 0)
                vec.append(w)
            # Dominant context for this signal
            ctx_weights = {ctx: a.signal_weights.get(s, {}).get(ctx, 0) for ctx in contexts}
            if ctx_weights:
                dominant = max(ctx_weights, key=ctx_weights.get)
                strategy.append(dominant)
        weight_vectors.append(vec)
        strategies.append(tuple(strategy))
    
    if len(weight_vectors) < 2:
        return {"weight_variance": 0, "strategy_entropy": 0, "mean_disagreement": 0}
    
    # Weight variance: how different are the agents' signal weights?
    n_dims = len(weight_vectors[0])
    variances = []
    for d in range(n_dims):
        vals = [v[d] for v in weight_vectors]
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / len(vals)
        variances.append(var)
    weight_variance = sum(variances) / len(variances) if variances else 0
    
    # Strategy entropy: how many different strategies exist?
    strategy_counts = Counter(strategies)
    total = len(strategies)
    strategy_entropy = -sum(
        (c/total) * math.log2(c/total) 
        for c in strategy_counts.values() if c > 0
    )
    
    # Mean disagreement: fraction of (signal, context) pairs where agents disagree on dominant signal
    disagreements = 0
    comparisons = 0
    for i in range(min(len(strategies), 30)):  # sample for speed
        for j in range(i+1, min(len(strategies), 30)):
            for k in range(len(strategies[i])):
                if strategies[i][k] != strategies[j][k]:
                    disagreements += 1
                comparisons += 1
    mean_disagreement = disagreements / comparisons if comparisons > 0 else 0
    
    return {
        "weight_variance": round(weight_variance, 6),
        "strategy_entropy": round(strategy_entropy, 4),
        "mean_disagreement": round(mean_disagreement, 4),
    }


def intervention_cloned(sim_obj, interval=50):
    """Force all agents to have the population-mean signal_weights."""
    tick = sim_obj.tick if hasattr(sim_obj, 'tick') else 0
    if tick % interval != 0 or tick == 0:
        return
    
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    num_signals = 4
    
    # Compute mean weights
    mean_weights = {}
    for s in range(num_signals):
        mean_weights[s] = {}
        for ctx in contexts:
            vals = [a.signal_weights.get(s, {}).get(ctx, 0) for a in sim_obj.agents 
                    if hasattr(a, 'signal_weights')]
            mean_weights[s][ctx] = sum(vals) / len(vals) if vals else 0
    
    # Force all agents to mean
    for a in sim_obj.agents:
        if hasattr(a, 'signal_weights'):
            for s in range(num_signals):
                for ctx in contexts:
                    a.signal_weights[s][ctx] = mean_weights[s][ctx]


def intervention_scrambled(sim_obj, interval=50):
    """Randomize each agent's signal_weights."""
    tick = sim_obj.tick if hasattr(sim_obj, 'tick') else 0
    if tick % interval != 0 or tick == 0:
        return
    
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    num_signals = 4
    
    for a in sim_obj.agents:
        if hasattr(a, 'signal_weights'):
            for s in range(num_signals):
                for ctx in contexts:
                    a.signal_weights[s][ctx] = random.random()


def intervention_gradient(sim_obj, interval=100):
    """Force a spatial gradient: agents on the left prefer signal 0 for food,
    agents on the right prefer signal 3. Creates structured diversity."""
    tick = sim_obj.tick if hasattr(sim_obj, 'tick') else 0
    if tick % interval != 0 or tick == 0:
        return
    
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    num_signals = 4
    width = 120  # sim width
    
    for a in sim_obj.agents:
        if not hasattr(a, 'signal_weights'):
            continue
        # Position-based bias
        x_frac = a.x / width  # 0 to 1
        for s in range(num_signals):
            # Each signal has a preferred x-band
            band_center = s / (num_signals - 1)  # 0, 0.33, 0.67, 1.0
            proximity = max(0, 1.0 - 2.0 * abs(x_frac - band_center))
            for ctx in contexts:
                # Blend existing weight with position bias
                old = a.signal_weights.get(s, {}).get(ctx, 0)
                a.signal_weights[s][ctx] = old * 0.5 + proximity * 0.5


def run_condition(name, ticks=2000, num_agents=60, intervention=None, 
                  use_cultural=True, use_convention=True) -> Dict:
    """Run one experimental condition."""
    print(f"\n{'='*60}")
    print(f"  CONDITION: {name}")
    print(f"  Cultural: {use_cultural}, Convention: {use_convention}")
    print(f"{'='*60}")
    
    s = emergence_sim.Simulation(num_agents=num_agents)
    if hasattr(s, 'cultural_transmission'):
        s.cultural_transmission = use_cultural
    if hasattr(s, 'convention_enforcement'):
        s.convention_enforcement = use_convention
    
    analyzer = TriplePointAnalyzer()
    diversity_timeline = []
    
    for tick in range(ticks):
        s.tick = tick  # expose tick for interventions
        
        # Apply intervention if any
        if intervention:
            intervention(s)
        
        s.step()
        analyzer.record_tick(s.agents)
        
        # Measure diversity every 100 ticks
        if tick % 100 == 0:
            div = measure_diversity(s.agents)
            div['tick'] = tick
            div['pop_size'] = len(s.agents)
            diversity_timeline.append(div)
            
        if tick % 500 == 0:
            print(f"  Tick {tick}/{ticks} — {len(s.agents)} agents")
    
    results = analyzer.analyze()
    
    # Compute mean diversity
    if diversity_timeline:
        mean_wv = sum(d['weight_variance'] for d in diversity_timeline) / len(diversity_timeline)
        mean_se = sum(d['strategy_entropy'] for d in diversity_timeline) / len(diversity_timeline)
        mean_dis = sum(d['mean_disagreement'] for d in diversity_timeline) / len(diversity_timeline)
    else:
        mean_wv = mean_se = mean_dis = 0
    
    diversity_summary = {
        "mean_weight_variance": round(mean_wv, 6),
        "mean_strategy_entropy": round(mean_se, 4),
        "mean_disagreement": round(mean_dis, 4),
        "timeline": diversity_timeline,
    }
    
    if "summary" in results:
        summary = results["summary"]
        print(f"\n  Results for {name}:")
        print(f"    Memory:         {summary['mean_memory']:.4f}")
        print(f"    Transport:      {summary['mean_transport']:.4f}")
        print(f"    Transformation: {summary['mean_transformation']:.4f}")
        print(f"    Triple Point:   {summary['mean_triple']:.4f}")
        print(f"    Diversity (wv): {mean_wv:.6f}")
        print(f"    Diversity (se): {mean_se:.4f}")
        print(f"    Disagreement:   {mean_dis:.4f}")
    
    return {
        "condition": name,
        "triple_point": results,
        "diversity": diversity_summary,
    }


def compute_correlations(results):
    """Compute correlation between diversity and triple-point axes."""
    points = []
    for r in results:
        if "summary" not in r["triple_point"]:
            continue
        s = r["triple_point"]["summary"]
        d = r["diversity"]
        points.append({
            "condition": r["condition"],
            "diversity": d["mean_weight_variance"],
            "strategy_entropy": d["mean_strategy_entropy"],
            "disagreement": d["mean_disagreement"],
            "memory": s["mean_memory"],
            "transport": s["mean_transport"],
            "transformation": s["mean_transformation"],
            "triple": s["mean_triple"],
        })
    
    if len(points) < 3:
        return points
    
    # Simple Pearson correlation: diversity vs transformation
    divs = [p["diversity"] for p in points]
    transforms = [p["transformation"] for p in points]
    triples = [p["triple"] for p in points]
    
    def pearson(x, y):
        n = len(x)
        if n < 3:
            return 0
        mx, my = sum(x)/n, sum(y)/n
        sx = math.sqrt(sum((xi-mx)**2 for xi in x) / n)
        sy = math.sqrt(sum((yi-my)**2 for yi in y) / n)
        if sx == 0 or sy == 0:
            return 0
        return sum((xi-mx)*(yi-my) for xi, yi in zip(x, y)) / (n * sx * sy)
    
    print(f"\n{'='*60}")
    print(f"  CORRELATION ANALYSIS")
    print(f"{'='*60}")
    
    r_div_transform = pearson(divs, transforms)
    r_div_triple = pearson(divs, triples)
    r_entropy_transform = pearson(
        [p["strategy_entropy"] for p in points], transforms
    )
    r_disagree_transform = pearson(
        [p["disagreement"] for p in points], transforms
    )
    
    print(f"  diversity ↔ transformation:  r = {r_div_transform:.4f}")
    print(f"  diversity ↔ triple-point:    r = {r_div_triple:.4f}")
    print(f"  strategy_entropy ↔ transf:   r = {r_entropy_transform:.4f}")
    print(f"  disagreement ↔ transf:       r = {r_disagree_transform:.4f}")
    
    for p in points:
        print(f"\n  {p['condition']:12s}: div={p['diversity']:.6f}  "
              f"mem={p['memory']:.4f}  trans={p['transport']:.4f}  "
              f"xform={p['transformation']:.4f}  triple={p['triple']:.4f}")
    
    return {
        "points": points,
        "correlations": {
            "diversity_vs_transformation": round(r_div_transform, 4),
            "diversity_vs_triple": round(r_div_triple, 4),
            "strategy_entropy_vs_transformation": round(r_entropy_transform, 4),
            "disagreement_vs_transformation": round(r_disagree_transform, 4),
        }
    }


if __name__ == "__main__":
    random.seed(42)
    
    TICKS = 2000
    N_AGENTS = 60
    
    all_results = []
    
    # 1. Natural (cultural + convention)
    all_results.append(run_condition(
        "NATURAL", ticks=TICKS, num_agents=N_AGENTS,
        use_cultural=True, use_convention=True
    ))
    
    # 2. Cloned (forced homogeneity)
    all_results.append(run_condition(
        "CLONED", ticks=TICKS, num_agents=N_AGENTS,
        intervention=intervention_cloned,
        use_cultural=True, use_convention=True
    ))
    
    # 3. Scrambled (maximum random diversity)
    all_results.append(run_condition(
        "SCRAMBLED", ticks=TICKS, num_agents=N_AGENTS,
        intervention=intervention_scrambled,
        use_cultural=True, use_convention=True
    ))
    
    # 4. Gradient (structured diversity)
    all_results.append(run_condition(
        "GRADIENT", ticks=TICKS, num_agents=N_AGENTS,
        intervention=intervention_gradient,
        use_cultural=True, use_convention=True
    ))
    
    # 5. Baseline (no culture)
    all_results.append(run_condition(
        "BASELINE", ticks=TICKS, num_agents=N_AGENTS,
        use_cultural=False, use_convention=False
    ))
    
    # Correlation analysis
    correlation = compute_correlations(all_results)
    
    # Save everything
    output = {
        "experiment": "diversity_modulation",
        "hypothesis": "Cognitive diversity enables transformation, which enables computation",
        "conditions": [r["condition"] for r in all_results],
        "results": all_results,
        "correlation": correlation,
    }
    
    Path("diversity_results.json").write_text(json.dumps(output, indent=2, default=str))
    print(f"\n\nResults saved to diversity_results.json")
    
    # Final verdict
    if isinstance(correlation, dict) and "correlations" in correlation:
        corr = correlation["correlations"]
        print(f"\n{'='*60}")
        print(f"  🧬 VERDICT")
        print(f"{'='*60}")
        r = corr["diversity_vs_transformation"]
        if r > 0.5:
            print(f"  ✅ CONFIRMED: Diversity → Transformation (r={r:.4f})")
            print(f"     Cognitive diversity IS the mechanism behind transformation.")
        elif r > 0.2:
            print(f"  🔶 PARTIAL: Weak diversity → transformation link (r={r:.4f})")
            print(f"     Diversity matters but isn't the whole story.")
        elif r < -0.2:
            print(f"  ❌ INVERTED: More diversity = LESS transformation (r={r:.4f})")
            print(f"     Hypothesis wrong — coherence might matter more than diversity.")
        else:
            print(f"  ⬜ INCONCLUSIVE: No clear relationship (r={r:.4f})")
            print(f"     Diversity doesn't predict transformation linearly.")
        
        r2 = corr["diversity_vs_triple"]
        print(f"\n  Diversity ↔ Triple-point: r={r2:.4f}")
        if r2 > 0.5:
            print(f"  💡 Diversity directly enables collective computation.")
        elif r2 < -0.2:
            print(f"  🤔 More diversity = less computation? Check if it destroys memory.")
