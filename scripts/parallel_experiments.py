#!/usr/bin/env python3
"""
Parallel Experiment Orchestrator
================================
Dispatches N experiment workers across available cores, collects results,
syncs them to the control box (via SSH/rsync or local file), and optionally
updates the concept graph and self-improvement loop.

Usage:
    python3 parallel_experiments.py N [--experiment EXPERIMENT_NAME] [--workers WORKERS] [--timeout TIMEOUT]
"""

import subprocess
import json
import os
import sys
import time
import argparse
import multiprocessing
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(process)d] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/experiment_orchestrator.log')
    ]
)
logger = logging.getLogger(__name__)

CONTROL_BOX_HOST = os.getenv("CONTROL_BOX_HOST", "127.0.0.1")
CONTROL_BOX_USER = os.getenv("CONTROL_BOX_USER", "x")
RESULTS_DIR = os.path.join(os.path.expanduser("~"), "striker", "results")
EXPERIMENT_DIR = os.path.join(os.path.expanduser("~"), "striker", "projects", "emergence-sim")
CONCEPT_GRAPH_DB = os.path.join(os.path.expanduser("~"), "striker", "brain", "concept_graph.db")

def run_experiment(worker_id: int, experiment_name: str, seed: int, timeout: int = 300) -> Dict:
    """
    Run a single experiment in isolation.
    Returns a dict with result data.
    """
    logger.info(f"Worker {worker_id}: Starting experiment '{experiment_name}' with seed {seed}")
    start_time = time.time()
    
    # Build command based on experiment type
    if experiment_name == "triple-point-agents":
        cmd = [sys.executable, os.path.join(EXPERIMENT_DIR, "autoresearch_triple.py"), "-n", "20", "--seed", str(seed)]
    elif experiment_name == "nonlinear-transformation":
        cmd = [sys.executable, os.path.join(EXPERIMENT_DIR, "nonlinear_experiment.py"), "--seed", str(seed)]
    elif experiment_name == "diversity-experiment":
        cmd = [sys.executable, os.path.join(EXPERIMENT_DIR, "diversity_experiment.py"), "--seed", str(seed)]
    elif experiment_name == "zero-copying-sweep":
        cmd = [sys.executable, os.path.join(EXPERIMENT_DIR, "zero_copying_sweep.py"), "--seed", str(seed)]
    else:
        logger.error(f"Unknown experiment: {experiment_name}")
        return {"worker_id": worker_id, "experiment": experiment_name, "error": f"Unknown experiment: {experiment_name}"}
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=EXPERIMENT_DIR
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            logger.info(f"Worker {worker_id}: Completed in {elapsed:.1f}s")
            # Parse output from the experiment
            output_lines = result.stdout.strip().split('\n')
            metrics = {}
            for line in output_lines:
                if ':' in line and any(k in line.lower() for k in ['triple', 'memory', 'transport', 'transformation', 'score']):
                    try:
                        key, val = line.rsplit(':', 1)
                        metrics[key.strip().lower()] = float(val.strip())
                    except:
                        pass
            
            return {
                "worker_id": worker_id,
                "experiment": experiment_name,
                "seed": seed,
                "status": "completed",
                "elapsed": round(elapsed, 2),
                "metrics": metrics,
                "output": result.stdout[-2000:],  # Last 2000 chars
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error(f"Worker {worker_id}: Failed (exit {result.returncode}) in {elapsed:.1f}s")
            return {
                "worker_id": worker_id,
                "experiment": experiment_name,
                "seed": seed,
                "status": "failed",
                "error": result.stderr[-1000:],
                "elapsed": round(elapsed, 2),
                "timestamp": datetime.now().isoformat()
            }
            
    except subprocess.TimeoutExpired:
        logger.error(f"Worker {worker_id}: Timed out after {timeout}s")
        return {
            "worker_id": worker_id,
            "experiment": experiment_name, 
            "seed": seed,
            "status": "timeout",
            "timeout": timeout,
            "elapsed": timeout,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Worker {worker_id}: Exception - {str(e)}")
        return {
            "worker_id": worker_id,
            "experiment": experiment_name,
            "seed": seed,
            "status": "exception",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def sync_results_to_control(results: List[Dict], control_host: str, control_user: str = "x"):
    """
    Sync results back to control box via rsync over SSH.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/tmp/experiment_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Rsync to control box
    dest = f"{control_user}@{control_host}:/home/x/striker/results/"
    cmd = ["rsync", "-avz", "--relative", results_file, dest]
    try:
        subprocess.run(cmd, check=True, timeout=30)
        logger.info(f"Results synced to control box: {dest}")
    except Exception as e:
        logger.warning(f"Failed to sync results: {e}. Saving locally.")
        os.makedirs(os.path.dirname(results_file), exist_ok=True)

def update_concept_graph(results: List[Dict]):
    """
    Update the concept graph with experiment results.
    This is a stub—will be implemented when Layer 5 is built.
    """
    logger.info(f"Would update concept graph with {len(results)} results if Layer 5 was ready")
    # TODO: Connect to concept_graph.py when it's implemented
    # cg = ConceptGraph()
    # for res in results:
    #     if res["status"] == "completed":
    #         cg.add_node(f"experiment:{res['experiment']}_{res['seed']}_{res['worker_id']}", ...)
    pass

def run_self_improvement_loop():
    """
    Run the self-improvement loop after experiments complete.
    This is a stub—will be implemented when Layer 6 is built.
    """
    logger.info("Would run self-improvement loop if Layer 6 was ready")
    # TODO: Connect to self_improvement_loop.py when it's implemented
    pass

def main():
    parser = argparse.ArgumentParser(description="Parallel Experiment Orchestrator")
    parser.add_argument("num_experiments", type=int, help="Number of experiments to run in parallel")
    parser.add_argument("--experiment", type=str, default="triple-point-agents", 
                        help="Experiment type to run")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of worker processes (default = num_experiments)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout per experiment in seconds (default: 300)")
    parser.add_argument("--start-seed", type=int, default=42,
                        help="Starting seed (default: 42)")
    parser.add_argument("--sync-host", type=str, default=None,
                        help="Control box host for rsync (default: from env)")
    
    args = parser.parse_args()
    
    # Create results directory
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Calculate seeds for each experiment
    total = args.num_experiments
    workers = args.workers or min(total, multiprocessing.cpu_count() - 2)  # Leave 2 cores for OS
    workers = max(1, workers)
    
    logger.info(f"Starting {total} experiments of type '{args.experiment}' with {workers} workers")
    logger.info(f"Seeds: {args.start_seed} to {args.start_seed + total - 1}")
    logger.info(f"Timeout per experiment: {args.timeout}s")
    logger.info(f"Available CPU cores: {multiprocessing.cpu_count()}")
    
    start_time = time.time()
    
    # Dispatch experiments in parallel using multiprocessing
    all_results = []
    
    with multiprocessing.Pool(processes=workers) as pool:
        # Create argument list for each worker
        worker_args = [
            (i, args.experiment, args.start_seed + i, args.timeout)
            for i in range(total)
        ]
        
        # Run all experiments
        results = pool.starmap(run_experiment, worker_args)
        all_results.extend(results)
    
    elapsed_total = time.time() - start_time
    
    # Summarize results
    completed = sum(1 for r in all_results if r["status"] == "completed")
    failed = sum(1 for r in all_results if r["status"] == "failed")
    timed_out = sum(1 for r in all_results if r["status"] == "timeout")
    exceptions = sum(1 for r in all_results if r["status"] == "exception")
    
    logger.info(f"Results in {elapsed_total:.1f}s:")
    logger.info(f"  Completed: {completed}/{total}")
    logger.info(f"  Failed:    {failed}/{total}")
    logger.info(f"  Timed out: {timed_out}/{total}")
    logger.info(f"  Exception: {exceptions}/{total}")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"results_{args.experiment}_{timestamp}.json"
    results_path = os.path.join(RESULTS_DIR, results_file)
    
    with open(results_path, 'w') as f:
        json.dump({
            "experiment": args.experiment,
            "total": total,
            "workers": workers,
            "elapsed": round(elapsed_total, 2),
            "results": all_results
        }, f, indent=2)
    
    logger.info(f"Results saved to: {results_path}")
    
    # Sync to control box if host is different
    sync_host = args.sync_host or os.getenv("CONTROL_BOX_HOST")
    if sync_host and sync_host != "127.0.0.1":
        sync_results_to_control(all_results, sync_host)
    
    # Update concept graph (Layer 5) if available
    if os.path.exists(CONCEPT_GRAPH_DB):
        update_concept_graph(all_results)
    
    # Run self-improvement loop (Layer 6) if available
    run_self_improvement_loop()
    
    logger.info("=== Experiment cycle complete ===")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())