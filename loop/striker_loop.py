#!/usr/bin/env python3
"""
The Striker Loop — Karpathy-style autonomous self-improvement.

Cycle: READ target → EVALUATE baseline → PROPOSE change → APPLY → EVALUATE → KEEP or REVERT

Each iteration = one experiment, logged to the brain.
Uses git for safe revert. Uses DragonflyDB for active experiment state.
Designed to be called by cron or heartbeat (one iteration per call).

Usage:
    python3 striker_loop.py --target emergence-sim     # Run one iteration
    python3 striker_loop.py --target poetry-engine     # Run one iteration
    python3 striker_loop.py --target emergence-sim -n 5  # Run 5 iterations
    python3 striker_loop.py --status                    # Show loop status
"""

import argparse
import json
import os
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

# Setup paths
STRIKER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(STRIKER_ROOT))

from brain.memory import get_memory
from brain.cache import get_cache


def load_target(name: str) -> dict:
    """Load a target config from YAML."""
    target_path = STRIKER_ROOT / "loop" / "targets" / f"{name}.yaml"
    if not target_path.exists():
        raise FileNotFoundError(f"Target config not found: {target_path}")
    with open(target_path) as f:
        return yaml.safe_load(f)


def git_snapshot(message: str):
    """Commit current state to git."""
    subprocess.run(["git", "add", "-A"], cwd=str(STRIKER_ROOT),
                   capture_output=True)
    subprocess.run(["git", "commit", "-m", message, "--allow-empty"],
                   cwd=str(STRIKER_ROOT), capture_output=True)


def git_revert():
    """Revert last commit (undo failed experiment)."""
    subprocess.run(["git", "revert", "HEAD", "--no-edit"],
                   cwd=str(STRIKER_ROOT), capture_output=True)


def git_get_hash() -> str:
    """Get current git hash."""
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=str(STRIKER_ROOT), capture_output=True, text=True)
    return result.stdout.strip()


def run_eval(target: dict) -> dict:
    """Run the evaluation script and return results."""
    eval_script = STRIKER_ROOT / target["eval_script"]
    if not eval_script.exists():
        return {"score": 0.0, "error": f"Eval script not found: {eval_script}"}

    try:
        result = subprocess.run(
            [sys.executable, str(eval_script)],
            capture_output=True, text=True, timeout=120,
            cwd=str(STRIKER_ROOT)
        )
        if result.returncode != 0:
            return {"score": 0.0, "error": result.stderr[:500]}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"score": 0.0, "error": "Eval timed out"}
    except json.JSONDecodeError:
        return {"score": 0.0, "error": f"Invalid eval output: {result.stdout[:200]}"}


def run_iteration(target: dict, iteration: int = 0) -> dict:
    """Run one iteration of the Striker Loop."""
    mem = get_memory()
    target_name = target["name"]
    file_path = STRIKER_ROOT / target["file_to_modify"]

    print(f"\n{'='*60}")
    print(f"🔄 Striker Loop — {target_name} — Iteration {iteration}")
    print(f"{'='*60}")

    # Step 1: Evaluate current baseline
    print("\n📊 Evaluating baseline...")
    baseline = run_eval(target)
    baseline_score = baseline.get("score", 0.0)
    print(f"   Baseline score: {baseline_score:.4f}")

    if baseline.get("error"):
        print(f"   ⚠ Error: {baseline['error']}")

    # Step 2: Read current file
    if not file_path.exists():
        print(f"   ❌ Target file not found: {file_path}")
        return {"outcome": "error", "reason": "file not found"}

    current_code = file_path.read_text()

    # Step 3: Snapshot before change
    git_snapshot(f"🔬 Loop pre-experiment: {target_name} iter {iteration}")

    # Step 4: The experiment would normally modify the file here.
    # For now, log the baseline and return — actual modification
    # will be done by the AI agent calling this loop.
    result = {
        "target": target_name,
        "iteration": iteration,
        "baseline_score": baseline_score,
        "baseline_details": baseline,
        "file": str(file_path),
        "git_hash": git_get_hash(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Log to brain
    mem.log_experiment(
        target=target_name,
        hypothesis=f"Baseline measurement, iteration {iteration}",
        change="none (baseline)",
        metric=target.get("metric_name", "score"),
        score=baseline_score,
        outcome="inconclusive",
        notes=json.dumps(baseline)
    )

    # Cache active state
    try:
        cache = get_cache()
        cache.set_active_experiment({
            "target": target_name,
            "iteration": iteration,
            "baseline": baseline_score,
            "started": result["timestamp"],
        })
        cache.increment(f"loop:{target_name}:iterations")
        cache.push_recent("experiments", {
            "target": target_name,
            "score": baseline_score,
            "iteration": iteration,
        })
    except Exception:
        pass  # Cache is optional

    print(f"\n✅ Iteration {iteration} complete. Score: {baseline_score:.4f}")
    return result


def show_status():
    """Show current loop status."""
    mem = get_memory()
    print("\n📊 Striker Loop Status\n")

    # Recent experiments
    experiments = mem.get_experiments(limit=10)
    if experiments:
        print("━━━ Recent Experiments ━━━")
        for e in experiments:
            icon = "✅" if e["outcome"] == "keep" else "❌" if e["outcome"] == "discard" else "🔄"
            score = f"{e['result_score']:.4f}" if e["result_score"] is not None else "?"
            print(f"  {icon} [{e['target']}] {e['hypothesis'][:60]}... → {score}")
    else:
        print("  No experiments yet.")

    # Cache state
    try:
        cache = get_cache()
        active = cache.get_active_experiment()
        if active:
            print(f"\n━━━ Active Experiment ━━━")
            print(f"  Target: {active.get('target')}")
            print(f"  Baseline: {active.get('baseline')}")
            print(f"  Started: {active.get('started')}")

        # Iteration counts
        print(f"\n━━━ Iteration Counts ━━━")
        for target_file in (STRIKER_ROOT / "loop" / "targets").glob("*.yaml"):
            name = target_file.stem
            count = cache.get_counter(f"loop:{name}:iterations")
            print(f"  {name}: {count}")
    except Exception:
        pass

    print()


def main():
    parser = argparse.ArgumentParser(description="Striker Loop — autonomous self-improvement")
    parser.add_argument("--target", help="Target name (from loop/targets/)")
    parser.add_argument("-n", type=int, default=1, help="Number of iterations")
    parser.add_argument("--status", action="store_true", help="Show loop status")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if not args.target:
        parser.print_help()
        return

    target = load_target(args.target)
    results = []
    for i in range(args.n):
        result = run_iteration(target, iteration=i)
        results.append(result)

    if len(results) == 1:
        print(json.dumps(results[0], indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Completed {len(results)} iterations")
        scores = [r.get("baseline_score", 0) for r in results]
        print(f"Scores: {[f'{s:.4f}' for s in scores]}")


if __name__ == "__main__":
    main()
