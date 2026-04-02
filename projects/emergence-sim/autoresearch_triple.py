#!/usr/bin/env python3
"""
🔄 AUTORESEARCH: Triple-Point Agent Optimization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Karpathy Loop applied to emergence sim:
  1. Pick a parameter to modify
  2. Run triple-point analysis
  3. Score
  4. Keep or revert
  5. Log everything everywhere

Results stored in:
  - SQLite (structured experiment log)
  - DragonflyDB (real-time state)
  - ChromaDB (semantic search of what happened)
  - W&B (detailed metrics + charts)
  - Git (code changes tracked)
"""

import json
import os
import sys
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).parent))
STRIKER_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, STRIKER_ROOT)

from triple_point_agents import TriplePointAnalyzer, run_experiment
from brain.memory import get_memory
from brain.consciousness import get_consciousness
from brain.semantic import get_semantic
from brain.experiments import get_tracker

# Try W&B — graceful if it fails
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False

# ── Parameter Space ──────────────────────────────────────────────────

PARAMETERS = {
    "num_agents": {"default": 60, "range": [30, 100], "type": "int"},
    "ticks": {"default": 2000, "range": [1000, 3000], "type": "int"},
    "cultural_rate": {"default": 0.15, "range": [0.05, 0.30], "type": "float"},
    "convention_strength": {"default": 0.03, "range": [0.01, 0.08], "type": "float"},
    "blend_rate": {"default": 0.45, "range": [0.1, 0.7], "type": "float"},
    "food_spawn_rate": {"default": 0.06, "range": [0.02, 0.15], "type": "float"},
    "food_energy": {"default": 3.0, "range": [1.5, 5.0], "type": "float"},
    "energy_drain": {"default": 0.14, "range": [0.08, 0.25], "type": "float"},
    "signal_threshold": {"default": 0.15, "range": [0.05, 0.4], "type": "float"},
}


def random_perturbation():
    """Pick a random parameter and perturb it."""
    param = random.choice(list(PARAMETERS.keys()))
    spec = PARAMETERS[param]
    
    if spec["type"] == "int":
        lo, hi = spec["range"]
        new_val = random.randint(lo, hi)
    else:
        lo, hi = spec["range"]
        current = spec["default"]
        # Perturb by ±20%
        delta = (hi - lo) * random.uniform(-0.2, 0.2)
        new_val = max(lo, min(hi, current + delta))
        new_val = round(new_val, 4)
    
    return param, spec["default"], new_val


def run_with_params(params: dict) -> dict:
    """Run the triple-point experiment with given parameters."""
    result = run_experiment(
        ticks=params.get("ticks", 2000),
        num_agents=params.get("num_agents", 60),
        use_cultural=True,
        use_convention=True,
        use_seasons=False,
        use_predator=False,
    )
    return result


def run_autoresearch(iterations: int = 10, project_name: str = "triple-point-agents"):
    """Run the full autoresearch loop."""
    
    mem = get_memory()
    consciousness = get_consciousness()
    sem = get_semantic()
    tracker = get_tracker()
    
    # Initialize W&B
    wb_run = None
    if WANDB_AVAILABLE:
        try:
            wb_run = wandb.init(
                project="striker-emergence",
                name=f"autoresearch-{datetime.now().strftime('%Y%m%d-%H%M')}",
                config={"iterations": iterations, "base_params": {k: v["default"] for k, v in PARAMETERS.items()}},
                tags=["autoresearch", "triple-point", "emergence-sim"],
            )
            print("✅ W&B initialized")
        except Exception as e:
            print(f"⚠️ W&B init failed: {e}")
            wb_run = None

    # Get baseline
    print("\n" + "=" * 60)
    print("📊 Running baseline...")
    print("=" * 60)
    
    base_params = {k: v["default"] for k, v in PARAMETERS.items()}
    baseline = run_with_params(base_params)
    
    if "summary" not in baseline:
        print("❌ Baseline failed")
        return
    
    best_score = baseline["summary"]["mean_triple"]
    best_params = deepcopy(base_params)
    
    print(f"\n🎯 Baseline triple-point: {best_score:.4f}")
    
    if wb_run:
        wandb.log({
            "iteration": 0,
            "triple_point": best_score,
            "memory": baseline["summary"]["mean_memory"],
            "transport": baseline["summary"]["mean_transport"],
            "transformation": baseline["summary"]["mean_transformation"],
            "max_triple": baseline["summary"]["max_triple"],
            "computing_windows": baseline["summary"]["computing_windows"],
            "outcome": "baseline",
        })

    # Log baseline
    mem.log_experiment(
        target=project_name,
        hypothesis="Baseline measurement with default parameters",
        change=json.dumps(base_params),
        metric="triple_point",
        score=best_score,
        outcome="keep",
        notes=json.dumps(baseline["summary"])
    )

    # ── Autoresearch Loop ────────────────────────────────────────
    
    results_log = [{"iteration": 0, "params": base_params, "score": best_score, "outcome": "baseline"}]
    
    for i in range(1, iterations + 1):
        print(f"\n{'=' * 60}")
        print(f"🔄 Iteration {i}/{iterations}")
        print(f"{'=' * 60}")
        
        # Perturb a parameter
        param_name, old_val, new_val = random_perturbation()
        print(f"   Changing {param_name}: {old_val} → {new_val}")
        
        # Run with new params
        test_params = deepcopy(best_params)
        test_params[param_name] = new_val
        
        hypothesis = f"Change {param_name} from {old_val} to {new_val} to improve triple-point score"
        
        try:
            result = run_with_params(test_params)
        except Exception as e:
            print(f"   ❌ Run failed: {e}")
            mem.log_experiment(
                target=project_name,
                hypothesis=hypothesis,
                change=f"{param_name}: {old_val} → {new_val}",
                metric="triple_point",
                score=0,
                outcome="discard",
                notes=f"Error: {str(e)}"
            )
            continue
        
        if "summary" not in result:
            print("   ❌ No summary in result")
            continue
        
        new_score = result["summary"]["mean_triple"]
        delta = new_score - best_score
        
        # Keep or discard
        if new_score > best_score:
            outcome = "keep"
            best_score = new_score
            best_params = deepcopy(test_params)
            PARAMETERS[param_name]["default"] = new_val
            icon = "✅"
        else:
            outcome = "discard"
            icon = "❌"
        
        print(f"\n   {icon} Score: {new_score:.4f} (Δ = {delta:+.4f}) → {outcome.upper()}")
        print(f"   Best so far: {best_score:.4f}")
        
        # ── Log everywhere ───────────────────────────────────────
        
        # SQLite
        mem.log_experiment(
            target=project_name,
            hypothesis=hypothesis,
            change=f"{param_name}: {old_val} → {new_val}",
            metric="triple_point",
            score=new_score,
            outcome=outcome,
            notes=json.dumps({
                "summary": result["summary"],
                "params": test_params,
                "delta": delta,
            })
        )
        
        # W&B
        if wb_run:
            log_data = {
                "iteration": i,
                "triple_point": new_score,
                "memory": result["summary"]["mean_memory"],
                "transport": result["summary"]["mean_transport"],
                "transformation": result["summary"]["mean_transformation"],
                "max_triple": result["summary"]["max_triple"],
                "computing_windows": result["summary"]["computing_windows"],
                "delta": delta,
                "outcome": outcome,
                "param_changed": param_name,
                "param_old": old_val,
                "param_new": new_val,
                "best_score": best_score,
            }
            wandb.log(log_data)
        
        # ChromaDB — semantic summary
        summary_text = (
            f"Iteration {i}: Changed {param_name} from {old_val} to {new_val}. "
            f"Triple-point score: {new_score:.4f} (delta {delta:+.4f}). "
            f"Memory={result['summary']['mean_memory']:.3f}, "
            f"Transport={result['summary']['mean_transport']:.3f}, "
            f"Transformation={result['summary']['mean_transformation']:.3f}. "
            f"Outcome: {outcome}."
        )
        sem.add("research", summary_text, metadata={
            "type": "autoresearch",
            "project": project_name,
            "iteration": str(i),
            "score": str(new_score),
            "outcome": outcome,
        })
        
        # DragonflyDB — current state
        consciousness.remember(
            f"Autoresearch iter {i}: {param_name} {old_val}→{new_val}, score {new_score:.4f} ({outcome})",
            category="experiment",
            importance=4 if outcome == "keep" else 2,
        )
        
        results_log.append({
            "iteration": i,
            "param": param_name,
            "old": old_val,
            "new": new_val,
            "score": new_score,
            "delta": delta,
            "outcome": outcome,
        })
    
    # ── Final Summary ────────────────────────────────────────────
    
    print(f"\n{'=' * 60}")
    print(f"🏁 AUTORESEARCH COMPLETE")
    print(f"{'=' * 60}")
    
    kept = [r for r in results_log if r["outcome"] == "keep"]
    discarded = [r for r in results_log if r["outcome"] == "discard"]
    
    print(f"   Iterations: {iterations}")
    print(f"   Kept: {len(kept)}")
    print(f"   Discarded: {len(discarded)}")
    print(f"   Baseline: {results_log[0]['score']:.4f}")
    print(f"   Best: {best_score:.4f}")
    print(f"   Improvement: {best_score - results_log[0]['score']:+.4f}")
    print(f"\n   Best parameters:")
    for k, v in best_params.items():
        default = {p: s["default"] for p, s in PARAMETERS.items()}.get(k)
        changed = " ← CHANGED" if v != default else ""
        print(f"     {k}: {v}{changed}")
    
    # Update experiment thread
    tracker.update_thread(
        "triple-point-agents",
        result=f"Autoresearch {iterations} iters: {results_log[0]['score']:.4f} → {best_score:.4f} ({best_score - results_log[0]['score']:+.4f}). Kept {len(kept)}/{iterations}.",
        score=best_score,
        next_steps=f"Best params: {json.dumps({k:v for k,v in best_params.items() if v != PARAMETERS[k]['range'][0]})}"
    )
    
    # Save full results
    Path("autoresearch_results.json").write_text(json.dumps({
        "log": results_log,
        "best_params": best_params,
        "best_score": best_score,
    }, indent=2))
    
    if wb_run:
        wandb.finish()
        print("✅ W&B run finalized")
    
    return results_log


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=5, help="Number of iterations")
    args = parser.parse_args()
    
    run_autoresearch(iterations=args.n)
