#!/usr/bin/env python3
"""
Recursive Self-Improvement Loop — Layer 6
===========================================
A six-stage, evidence-based loop that lets the agent generate hypotheses
from the concept graph, test them, evaluate results, update beliefs/skills,
and repeat — driving real cognitive evolution over time.

Stages:
  1. Observe      — Review recent experience, experiments, skill usage
  2. Hypothesize  — Generate testable hypotheses from the concept graph
  3. Plan         — Design minimal viable tests with clear criteria
  4. Act          — Execute tests, log everything
  5. Evaluate     — validated / falsified / inconclusive
  6. Update       — Promote validated, retire falsified, update graph
"""

import json
import os
import sys
import time
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from concept_graph import ConceptGraph

logger = logging.getLogger("self_improvement")

# ── Data structures ───────────────────────────────────────────────────
@dataclass
class Hypothesis:
    uid: str
    label: str
    description: str
    predicted_outcome: str
    rationale: str  # concept graph path that led to this
    success_criteria: str
    experiment_name: str
    experiment_args: Dict = field(default_factory=dict)
    confidence: float = 0.3
    status: str = "pending"  # pending → validated | falsified | inconclusive
    evidence: str = ""
    created_at: str = ""
    tested_at: str = ""
    elapsed: float = 0.0

@dataclass
class ImprovementReport:
    loop_id: str
    stage: str          # which stage we're at
    action: str         # what was done
    details: str
    timestamp: str = ""
    metrics: Dict = field(default_factory=dict)

# ── Core Loop ──────────────────────────────────────────────────────────
class SelfImprovementLoop:
    """The engine of agent cognition and evolution."""

    def __init__(self, graph: Optional[ConceptGraph] = None, results_dir: str = None):
        if results_dir is None:
            self.results_dir = os.path.join(os.path.expanduser("~"), "striker", "results")
        else:
            self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)

        if graph is None:
            self.graph = ConceptGraph()
        else:
            self.graph = graph

        self.loop_counter = 0
        self.log_path = os.path.join(self.results_dir, "improvement_log.jsonl")

    # ── Stage 1: Observe ─────────────────────────────────────────────
    def observe(self) -> List[Dict]:
        """Review recent experience to find improvement opportunities."""
        logger.info("Stage 1: Observe")
        opportunities = []

        # 1a. Look for concepts with high contradiction load
        for nid in list(self.graph.graph.nodes):
            contradictions = self.graph.contradiction_check(nid)
            if contradictions:
                opportunities.append({
                    "type": "contradiction",
                    "concept": nid,
                    "contradictions": contradictions,
                    "action": "resolve_contradiction",
                })

        # 2. Look for unsupported hypotheses
        for nid, data in self.graph.graph.nodes(data=True):
            if data.get("type") == "hypothesis":
                valid = self.graph.validated_by(nid)
                fals = self.graph.falsified_by(nid)
                if not valid and not fals:
                    opportunities.append({
                        "type": "untested_hypothesis",
                        "hypothesis": nid,
                        "action": "test_hypothesis",
                    })

        # 3. Look for recent experiment results that haven't been incorporated
        results_files = []
        if os.path.exists(self.results_dir):
            for f in sorted(os.listdir(self.results_dir)):
                if f.startswith("results_") and f.endswith(".json"):
                    results_files.append(os.path.join(self.results_dir, f))

        latest_results = results_files[-1] if results_files else None
        if latest_results:
            opportunities.append({
                "type": "new_results",
                "path": latest_results,
                "action": "integrate_results",
            })

        # 4. Look for low-confidence principles that need more evidence
        for nid, data in self.graph.graph.nodes(data=True):
            if data.get("type") == "principle" and data.get("confidence", 0.5) < 0.6:
                opportunities.append({
                    "type": "low_confidence_principle",
                    "concept": nid,
                    "confidence": data.get("confidence", 0),
                    "action": "gather_more_evidence",
                })

        logger.info(f"Observe found {len(opportunities)} opportunities")
        return opportunities

    # ── Stage 2: Hypothesize ─────────────────────────────────────────
    def hypothesize(self, opportunities: List[Dict]) -> List[Hypothesis]:
        """Generate testable hypotheses from observed opportunities."""
        logger.info("Stage 2: Hypothesize")
        hypotheses = []

        for opp in opportunities:
            if opp["action"] == "test_hypothesis":
                # Already a hypothesis — just promote it for testing
                h = self.graph.get_node(opp["hypothesis"])
                if h:
                    hyp = Hypothesis(
                        uid=opp["hypothesis"],
                        label=h.get("label", opp["hypothesis"]),
                        description=h.get("description", ""),
                        predicted_outcome=h.get("source", ""),
                        rationale="",
                        success_criteria="to be defined",
                        experiment_name="to be defined",
                    )
                    hypotheses.append(hyp)

            elif opp["action"] == "resolve_contradiction":
                concept = opp["concept"]
                hyp = Hypothesis(
                    uid=f"hypothesis:resolve-{concept}",
                    label=f"Resolve contradiction around {concept}",
                    description=f"Multiple sources both support and contradict {concept}. Run experiments to determine which side holds.",
                    predicted_outcome="Either supports or contradicts will be validated by evidence",
                    rationale=f"contradiction_check({concept}) → {opp['contradictions']}",
                    success_criteria="One side wins with p < 0.05 or equivalent metric gap",
                    experiment_name="contradiction-resolution",
                )
                hypotheses.append(hyp)

            elif opp["action"] == "integrate_results":
                # Parse latest results and generate new hypotheses
                try:
                    with open(opp["path"]) as f:
                        data = json.load(f)
                    results = data.get("results", [])
                    completed = [r for r in results if r.get("status") == "completed"]
                    if completed:
                        # Extract metrics across all completed runs
                        triples = [r.get("metrics", {}).get("triple", 0) for r in completed if "triple" in r.get("metrics", {})]
                        if triples:
                            best = max(triples)
                            avg = sum(triples) / len(triples)
                            hyp = Hypothesis(
                                uid=f"hypothesis:improve-from-{round(avg, 3)}",
                                label=f"Improve triple-point score from {avg:.3f}",
                                description=f"Best triple-point from latest run was {best:.3f}, avg was {avg:.3f}. Can we push higher with different parameters?",
                                predicted_outcome=f"Triple-point score > {best:.3f}",
                                rationale=f"results file: {opp['path']}",
                                success_criteria=f"triple-point > {best:.3f}",
                                experiment_name="triple-point-agents",
                            )
                            hypotheses.append(hyp)
                except Exception as e:
                    logger.warning(f"Could not parse results file: {e}")

            elif opp["action"] == "gather_more_evidence":
                concept = opp["concept"]
                hyp = Hypothesis(
                    uid=f"hypothesis:evidence-for-{concept}",
                    label=f"Gather more evidence for {concept}",
                    description=f"Principle {concept} has low confidence ({opp.get('confidence', 0):.2f}). Run more experiments to validate.",
                    predicted_outcome=f"Confidence in {concept} will increase above 0.6",
                    rationale=f"Low-confidence principle detected: {concept}",
                    success_criteria=f"Confidence > 0.6 after new experiments",
                    experiment_name="principle-validation",
                )
                hypotheses.append(hyp)

        logger.info(f"Generated {len(hypotheses)} hypotheses for testing")
        return hypotheses

    # ── Stage 3: Plan ────────────────────────────────────────────────
    def plan(self, hypotheses: List[Hypothesis]) -> List[Dict]:
        """Design minimal viable tests for each hypothesis."""
        logger.info("Stage 3: Plan")
        test_plans = []

        for h in hypotheses:
            plan = {
                "hypothesis_uid": h.uid,
                "experiment_name": h.experiment_name,
                "experiment_args": {
                    "seed": 42,
                    "num_experiments": 5,  # minimal viable test
                    "workers": 4,          # default parallelism
                },
                "success_criteria": h.success_criteria,
                "timeout": 600,            # 10 minutes per experiment
            }

            # Specific plans based on experiment type
            if h.experiment_name == "triple-point-agents":
                plan["experiment_args"]["experiment"] = "triple-point-agents"
            elif h.experiment_name == "contradiction-resolution":
                plan["experiment_args"]["experiment"] = "triple-point-agents"
            elif h.experiment_name == "principle-validation":
                plan["experiment_args"]["experiment"] = "triple-point-agents"
            elif h.experiment_name == "to be defined":
                plan["experiment_args"]["experiment"] = "triple-point-agents"
                plan["experiment_name"] = "triple-point-agents"

            test_plans.append(plan)

        logger.info(f"Planned {len(test_plans)} tests")
        return test_plans

    # ── Stage 4: Act ─────────────────────────────────────────────────
    def act(self, test_plans: List[Dict]) -> List[Dict]:
        """Execute the test plans."""
        logger.info("Stage 4: Act")
        results = []

        for plan in test_plans:
            logger.info(f"Running experiment: {plan['experiment_name']} for hypothesis {plan['hypothesis_uid']}")

            # Build command
            script = os.path.join(os.path.expanduser("~"), "striker", "scripts", "parallel_experiments.py")
            exp_args = plan["experiment_args"]
            cmd = [
                sys.executable, script,
                str(exp_args.get("num_experiments", 5)),
                "--experiment", exp_args.get("experiment", "triple-point-agents"),
                "--workers", str(exp_args.get("workers", 4)),
                "--timeout", str(plan.get("timeout", 600)),
                "--start-seed", str(exp_args.get("seed", 42)),
            ]

            start = time.time()
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=plan.get("timeout", 600) + 60)
                elapsed = time.time() - start
                results.append({
                    "hypothesis_uid": plan["hypothesis_uid"],
                    "status": "executed" if proc.returncode == 0 else "exec_failed",
                    "stdout": proc.stdout[-3000:],
                    "stderr": proc.stderr[-1000:],
                    "returncode": proc.returncode,
                    "elapsed": round(elapsed, 2),
                    "plan": plan,
                })
            except subprocess.TimeoutExpired:
                elapsed = time.time() - start
                results.append({
                    "hypothesis_uid": plan["hypothesis_uid"],
                    "status": "timeout",
                    "elapsed": round(elapsed, 2),
                    "plan": plan,
                })
            except Exception as e:
                results.append({
                    "hypothesis_uid": plan["hypothesis_uid"],
                    "status": f"exception: {e}",
                    "elapsed": 0,
                    "plan": plan,
                })

        logger.info(f"Acted on {len(results)} plans")
        return results

    # ── Stage 5: Evaluate ────────────────────────────────────────────
    def evaluate(self, results: List[Dict]) -> List[Dict]:
        """Analyze results against success criteria."""
        logger.info("Stage 5: Evaluate")
        evaluations = []

        for r in results:
            plan = r.get("plan", {})
            criteria = plan.get("success_criteria", "")
            hyp_uid = r.get("hypothesis_uid", "")

            if r["status"] != "executed":
                evaluations.append({
                    "hypothesis_uid": hyp_uid,
                    "outcome": "inconclusive",
                    "reason": f"Execution failed: {r['status']}",
                })
                continue

            # Parse experiment results from stdout
            output = r.get("stdout", "")
            metric_value = self._extract_metric(output, criteria)

            if metric_value is not None:
                # Check if criteria is met
                # Look for patterns like "triple-point > 0.588"
                if ">" in criteria:
                    try:
                        threshold = float(criteria.split(">")[1].strip())
                        if metric_value > threshold:
                            outcome = "validated"
                        elif metric_value < threshold - 0.02:  # small margin
                            outcome = "falsified"
                        else:
                            outcome = "inconclusive"
                    except (ValueError, IndexError):
                        outcome = "inconclusive"
                else:
                    outcome = "validated" if metric_value > 0 else "falsified"

                evaluations.append({
                    "hypothesis_uid": hyp_uid,
                    "outcome": outcome,
                    "metric_value": metric_value,
                    "criteria": criteria,
                })
            else:
                evaluations.append({
                    "hypothesis_uid": hyp_uid,
                    "outcome": "inconclusive",
                    "reason": "Could not extract metric from output",
                    "output_snippet": output[-500:],
                })

        logger.info(f"Evaluations: {len([e for e in evaluations if e['outcome'] == 'validated'])} validated, "
                    f"{len([e for e in evaluations if e['outcome'] == 'falsified'])} falsified, "
                    f"{len([e for e in evaluations if e['outcome'] == 'inconclusive'])} inconclusive")
        return evaluations

    def _extract_metric(self, output: str, criteria: str) -> Optional[float]:
        """Extract relevant metric from experiment output."""
        import re

        # Look for triple-point score in output
        patterns = [
            r'triple[=: ]+([0-9.]+)',
            r'Triple point[=: ]+([0-9.]+)',
            r'mean_triple[=: ]+([0-9.]+)',
            r'score[=: ]+([0-9.]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    return float(matches[-1])
                except ValueError:
                    continue
        return None

    # ── Stage 6: Update ──────────────────────────────────────────────
    def update(self, evaluations: List[Dict]):
        """Update the concept graph and internal state based on evaluations."""
        logger.info("Stage 6: Update")
        loop_id = f"loop-{self.loop_counter}"
        ts = datetime.now().isoformat()

        for ev in evaluations:
            hyp_uid = ev.get("hypothesis_uid", "")
            outcome = ev.get("outcome", "inconclusive")

            if outcome == "validated":
                # Promote: hypothesis → principle (if confidence high enough)
                node = self.graph.get_node(hyp_uid)
                if node:
                    # Increase confidence
                    old_conf = node.get("confidence", 0.3)
                    new_conf = min(1.0, old_conf + 0.3)
                    self.graph.update_node_confidence(hyp_uid, new_conf)

                    # Create principle node from hypothesis
                    principle_uid = hyp_uid.replace("hypothesis:", "principle:")
                    self.graph.add_node(
                        uid=principle_uid,
                        label=node.get("label", ""),
                        node_type="principle",
                        description=node.get("description", ""),
                        source=f"validated from {hyp_uid}",
                        confidence=new_conf,
                    )

                    # Link: experiment result VALIDATED_BY principle
                    self.graph.add_edge(
                        source_uid=hyp_uid,
                        target_uid=principle_uid,
                        edge_type="VALIDATED_BY",
                        weight=0.9,
                        evidence=f"loop {loop_id}: {json.dumps(ev)}",
                    )

                    logger.info(f"Validated: {hyp_uid} → principle: {principle_uid} (conf={new_conf:.2f})")

                    self._log(loop_id, "validated", f"Promoted {hyp_uid} to {principle_uid}",
                              {"old_confidence": old_conf, "new_confidence": new_conf})

            elif outcome == "falsified":
                node = self.graph.get_node(hyp_uid)
                if node:
                    old_conf = node.get("confidence", 0.3)
                    new_conf = max(0.0, old_conf - 0.3)
                    self.graph.update_node_confidence(hyp_uid, new_conf)

                    # If confidence drops below threshold, demote
                    if new_conf < 0.1:
                        self.graph.delete_node(hyp_uid)
                        logger.info(f"Falsified and deleted: {hyp_uid} (conf={new_conf:.2f})")
                        self._log(loop_id, "falsified_deleted", f"Deleted {hyp_uid} (conf too low: {new_conf:.2f})")
                    else:
                        logger.info(f"Falsified: {hyp_uid} (conf={old_conf:.2f} → {new_conf:.2f})")
                        self._log(loop_id, "falsified", f"Reduced confidence: {hyp_uid} from {old_conf:.2f} to {new_conf:.2f}")

            elif outcome == "inconclusive":
                logger.info(f"Inconclusive: {hyp_uid} — {ev.get('reason', 'unknown')}")
                self._log(loop_id, "inconclusive", f"Inconclusive for {hyp_uid}: {ev.get('reason', 'unknown')}")

        # Final save
        self.graph.save()
        logger.info(f"Graph saved. Loop {loop_id} complete.")

    def _log(self, loop_id: str, action: str, details: str, metrics: Dict = None):
        """Append to improvement log."""
        entry = {
            "loop_id": loop_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics or {},
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # ── Run full loop ─────────────────────────────────────────────────
    def run(self, max_hypotheses: int = 5) -> Dict:
        """Execute one full Observe → Hypothesize → Plan → Act → Evaluate → Update cycle."""
        self.loop_counter += 1
        loop_id = f"loop-{self.loop_counter}"
        ts = datetime.now().isoformat()

        logger.info(f"{'='*60}")
        logger.info(f"Starting {loop_id}")
        logger.info(f"{'='*60}")

        start = time.time()

        # 1. Observe
        opportunities = self.observe()

        # 2. Hypothesize
        hypotheses = self.hypothesize(opportunities)
        hypotheses = hypotheses[:max_hypotheses]  # Cap for efficiency

        if not hypotheses:
            logger.info("No hypotheses to test. Loop skipped.")
            return {"loop_id": loop_id, "stage": "observe", "hypotheses": 0, "elapsed": time.time() - start}

        # 3. Plan
        test_plans = self.plan(hypotheses)

        # 4. Act
        results = self.act(test_plans)

        # 5. Evaluate
        evaluations = self.evaluate(results)

        # 6. Update
        self.update(evaluations)

        elapsed = time.time() - start
        summary = {
            "loop_id": loop_id,
            "opportunities": len(opportunities),
            "hypotheses": len(hypotheses),
            "tests_run": len(results),
            "validated": len([e for e in evaluations if e['outcome'] == 'validated']),
            "falsified": len([e for e in evaluations if e['outcome'] == 'falsified']),
            "inconclusive": len([e for e in evaluations if e['outcome'] == 'inconclusive']),
            "elapsed": round(elapsed, 2),
            "timestamp": ts,
        }

        logger.info(f"Loop {loop_id} complete: {json.dumps(summary)}")
        self._log(loop_id, "loop_complete", f"Summary: {json.dumps(summary)}", summary)
        return summary


# ── CLI ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-hypotheses", type=int, default=5, help="Max hypotheses to test per loop")
    parser.add_argument("--loops", type=int, default=1, help="Number of loops to run")
    parser.add_argument("--db", type=str, default=None, help="Path to concept graph DB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

    loop = SelfImprovementLoop(graph=ConceptGraph(db_path=args.db) if args.db else None)

    for i in range(args.loops):
        summary = loop.run(max_hypotheses=args.max_hypotheses)
        print(json.dumps(summary, indent=2))
