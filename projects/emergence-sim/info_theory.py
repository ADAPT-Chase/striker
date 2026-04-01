#!/usr/bin/env python3
"""
📐 INFORMATION-THEORETIC ANALYSIS OF EMERGENT COMMUNICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Measures whether agents have developed *real* communication using
rigorous information theory — not just pattern-matching heuristics.

Key metrics:
  • H(S) — entropy of signal usage (are all signals used equally?)
  • H(C) — entropy of contexts (how diverse are situations?)
  • H(S|C) — conditional entropy of signals given context
  • I(S;C) — mutual information between signals and contexts
           = H(S) - H(S|C)
           This is THE metric. If I(S;C) > 0, signals carry information
           about context. The higher, the more "language-like" the system.
  • NMI — normalized mutual information = I(S;C) / min(H(S), H(C))
           Ranges 0 to 1. 1 = perfect code. 0 = noise.
  • Channel capacity utilization — how much of the theoretical maximum
    information transfer is actually being used
  • Temporal dynamics — how these metrics evolve over time, detecting
    phase transitions where communication "clicks"

This module can answer: "Did the agents actually develop language,
or is the pattern detection just seeing noise?"
"""

import math
from collections import defaultdict
from typing import Optional


class SignalAnalyzer:
    """Tracks signal-context co-occurrences and computes information-theoretic metrics."""

    def __init__(self, num_signals: int = 4,
                 contexts: tuple = ('food_near', 'danger_near', 'friends_near', 'alone')):
        self.num_signals = num_signals
        self.contexts = contexts

        # Joint counts: joint[signal][context] = count
        self.joint_counts = defaultdict(lambda: defaultdict(int))
        self.total_observations = 0

        # Windowed tracking for temporal analysis
        self.window_size = 100  # observations per window
        self.current_window = defaultdict(lambda: defaultdict(int))
        self.current_window_count = 0
        self.history = []  # list of MetricSnapshot

        # Phase transition detection
        self.nmi_history = []
        self.phase_transitions = []

    def observe(self, signal: int, context: str):
        """Record a signal emission event."""
        self.joint_counts[signal][context] += 1
        self.total_observations += 1

        self.current_window[signal][context] += 1
        self.current_window_count += 1

        if self.current_window_count >= self.window_size:
            self._close_window()

    def _close_window(self):
        """Compute metrics for the current window and archive it."""
        snapshot = self._compute_metrics(self.current_window, self.current_window_count)
        snapshot['window_index'] = len(self.history)
        self.history.append(snapshot)

        # Phase transition detection: look for sudden NMI jumps
        self.nmi_history.append(snapshot['nmi'])
        if len(self.nmi_history) >= 3:
            recent = self.nmi_history[-3:]
            delta = recent[-1] - recent[0]
            if delta > 0.15:  # significant jump in 3 windows
                self.phase_transitions.append({
                    'window': len(self.history) - 1,
                    'nmi_before': recent[0],
                    'nmi_after': recent[-1],
                    'delta': delta
                })

        # Reset window
        self.current_window = defaultdict(lambda: defaultdict(int))
        self.current_window_count = 0

    def _compute_metrics(self, joint: dict, total: int) -> dict:
        """Compute all information-theoretic metrics from a joint distribution."""
        if total == 0:
            return {
                'h_signal': 0, 'h_context': 0, 'h_joint': 0,
                'h_signal_given_context': 0, 'mutual_info': 0,
                'nmi': 0, 'channel_utilization': 0,
                'total_obs': 0, 'signal_dist': {}, 'context_dist': {},
                'dominant_mappings': {}
            }

        # Marginal distributions
        signal_counts = defaultdict(int)
        context_counts = defaultdict(int)
        for s in joint:
            for c in joint[s]:
                signal_counts[s] += joint[s][c]
                context_counts[c] += joint[s][c]

        # P(S), P(C)
        p_signal = {s: count / total for s, count in signal_counts.items()}
        p_context = {c: count / total for c, count in context_counts.items()}

        # H(S) — signal entropy
        h_signal = -sum(p * math.log2(p) for p in p_signal.values() if p > 0)

        # H(C) — context entropy
        h_context = -sum(p * math.log2(p) for p in p_context.values() if p > 0)

        # H(S,C) — joint entropy
        h_joint = 0
        for s in joint:
            for c in joint[s]:
                p_sc = joint[s][c] / total
                if p_sc > 0:
                    h_joint -= p_sc * math.log2(p_sc)

        # H(S|C) = H(S,C) - H(C)
        h_signal_given_context = h_joint - h_context

        # I(S;C) = H(S) - H(S|C)
        mutual_info = h_signal - h_signal_given_context

        # Clamp to avoid floating point weirdness
        mutual_info = max(0, mutual_info)

        # NMI = I(S;C) / min(H(S), H(C))
        min_h = min(h_signal, h_context) if min(h_signal, h_context) > 0 else 1
        nmi = mutual_info / min_h

        # Channel capacity = log2(num_signals)
        max_capacity = math.log2(self.num_signals) if self.num_signals > 1 else 1
        channel_utilization = mutual_info / max_capacity if max_capacity > 0 else 0

        # Dominant signal-context mappings (what each signal "means")
        dominant_mappings = {}
        for s in joint:
            if signal_counts[s] > 0:
                best_ctx = max(joint[s], key=joint[s].get)
                strength = joint[s][best_ctx] / signal_counts[s]
                dominant_mappings[s] = {
                    'context': best_ctx,
                    'strength': strength,
                    'count': joint[s][best_ctx],
                    'total': signal_counts[s]
                }

        return {
            'h_signal': h_signal,
            'h_context': h_context,
            'h_joint': h_joint,
            'h_signal_given_context': h_signal_given_context,
            'mutual_info': mutual_info,
            'nmi': nmi,
            'channel_utilization': channel_utilization,
            'total_obs': total,
            'signal_dist': dict(p_signal),
            'context_dist': dict(p_context),
            'dominant_mappings': dominant_mappings
        }

    def get_cumulative_metrics(self) -> dict:
        """Get metrics over ALL observations so far."""
        return self._compute_metrics(self.joint_counts, self.total_observations)

    def get_latest_window_metrics(self) -> Optional[dict]:
        """Get metrics from the most recent completed window."""
        return self.history[-1] if self.history else None

    def interpretation(self) -> str:
        """Human-readable interpretation of the current state."""
        m = self.get_cumulative_metrics()
        if m['total_obs'] < 20:
            return "Insufficient data for analysis."

        lines = []
        lines.append(f"═══ INFORMATION-THEORETIC ANALYSIS ({m['total_obs']} observations) ═══")
        lines.append("")

        # Core metrics
        lines.append(f"  H(Signal)          = {m['h_signal']:.3f} bits")
        lines.append(f"  H(Context)         = {m['h_context']:.3f} bits")
        lines.append(f"  H(Signal|Context)  = {m['h_signal_given_context']:.3f} bits")
        lines.append(f"  I(Signal;Context)  = {m['mutual_info']:.3f} bits")
        lines.append(f"  NMI                = {m['nmi']:.3f}")
        lines.append(f"  Channel util.      = {m['channel_utilization']:.1%}")
        lines.append("")

        # Interpretation
        nmi = m['nmi']
        if nmi < 0.05:
            verdict = "NO COMMUNICATION — signals are essentially random noise"
        elif nmi < 0.15:
            verdict = "WEAK SIGNAL — slight correlation, possibly proto-communication"
        elif nmi < 0.30:
            verdict = "EMERGING LANGUAGE — signals carry meaningful context information"
        elif nmi < 0.50:
            verdict = "FUNCTIONAL COMMUNICATION — agents have developed a working signal code"
        elif nmi < 0.75:
            verdict = "RICH LANGUAGE — signals efficiently encode contextual information"
        else:
            verdict = "NEAR-PERFECT CODE — signals are almost deterministic encodings of context"

        lines.append(f"  VERDICT: {verdict}")
        lines.append("")

        # Signal meanings
        if m['dominant_mappings']:
            lines.append("  Signal meanings:")
            signal_names = ['◆', '▲', '●', '■']
            for s, mapping in sorted(m['dominant_mappings'].items()):
                name = signal_names[s] if s < len(signal_names) else f"#{s}"
                ctx = mapping['context']
                strength = mapping['strength']
                label = '✓' if strength > 0.5 else '~' if strength > 0.35 else '?'
                lines.append(f"    {name} → {ctx:15s} ({strength:.0%} of {mapping['total']} uses) [{label}]")

        # Phase transitions
        if self.phase_transitions:
            lines.append("")
            lines.append("  Phase transitions detected:")
            for pt in self.phase_transitions:
                lines.append(f"    Window {pt['window']}: NMI jumped {pt['nmi_before']:.3f} → {pt['nmi_after']:.3f} (+{pt['delta']:.3f})")

        # Temporal trend
        if len(self.history) >= 3:
            lines.append("")
            early_nmi = sum(h['nmi'] for h in self.history[:3]) / 3
            late_nmi = sum(h['nmi'] for h in self.history[-3:]) / 3
            delta = late_nmi - early_nmi
            if delta > 0.05:
                lines.append(f"  Trend: IMPROVING — NMI increasing ({early_nmi:.3f} → {late_nmi:.3f})")
            elif delta < -0.05:
                lines.append(f"  Trend: DEGRADING — NMI decreasing ({early_nmi:.3f} → {late_nmi:.3f})")
            else:
                lines.append(f"  Trend: STABLE — NMI roughly constant ({early_nmi:.3f} → {late_nmi:.3f})")

        return "\n".join(lines)

    def signal_specificity(self) -> dict:
        """For each signal, compute its specificity (how focused it is on one context).
        Uses entropy: low entropy = high specificity."""
        result = {}
        signal_names = ['◆', '▲', '●', '■']
        for s in self.joint_counts:
            total = sum(self.joint_counts[s].values())
            if total < 5:
                continue
            probs = {c: self.joint_counts[s][c] / total for c in self.joint_counts[s]}
            entropy = -sum(p * math.log2(p) for p in probs.values() if p > 0)
            max_entropy = math.log2(len(probs)) if len(probs) > 1 else 1
            specificity = 1 - (entropy / max_entropy) if max_entropy > 0 else 1
            name = signal_names[s] if s < len(signal_names) else f"#{s}"
            result[name] = {
                'specificity': specificity,
                'entropy': entropy,
                'distribution': probs,
                'uses': total
            }
        return result

    def context_predictability(self) -> dict:
        """For each context, how predictable is the signal choice?
        High predictability = agents consistently use the same signal for this context."""
        result = {}
        # Invert: context -> signal counts
        ctx_signal = defaultdict(lambda: defaultdict(int))
        for s in self.joint_counts:
            for c in self.joint_counts[s]:
                ctx_signal[c][s] += self.joint_counts[s][c]

        signal_names = ['◆', '▲', '●', '■']
        for c in ctx_signal:
            total = sum(ctx_signal[c].values())
            if total < 5:
                continue
            probs = {s: ctx_signal[c][s] / total for s in ctx_signal[c]}
            entropy = -sum(p * math.log2(p) for p in probs.values() if p > 0)
            max_entropy = math.log2(len(probs)) if len(probs) > 1 else 1
            predictability = 1 - (entropy / max_entropy) if max_entropy > 0 else 1
            dominant = max(probs, key=probs.get)
            name = signal_names[dominant] if dominant < len(signal_names) else f"#{dominant}"
            result[c] = {
                'predictability': predictability,
                'dominant_signal': name,
                'dominant_prob': probs[dominant],
                'uses': total
            }
        return result


class PopulationDynamicsAnalyzer:
    """Tracks population-level information metrics over time."""

    def __init__(self):
        self.snapshots = []

    def record(self, tick: int, agents: list, season: int = 0):
        """Record population state at a given tick."""
        if not agents:
            return

        pop = len(agents)
        energies = [a.energy for a in agents]
        generations = [a.generation for a in agents]
        memory_sizes = [len(a.memory) for a in agents]

        # Energy distribution entropy
        energy_bins = [0] * 5  # [0-3, 3-6, 6-9, 9-12, 12+]
        for e in energies:
            idx = min(int(e / 3), 4)
            energy_bins[idx] += 1
        energy_probs = [b / pop for b in energy_bins if b > 0]
        energy_entropy = -sum(p * math.log2(p) for p in energy_probs) if energy_probs else 0

        # Generation diversity (are all agents the same generation or diverse?)
        gen_counts = defaultdict(int)
        for g in generations:
            gen_counts[g] += 1
        gen_probs = [c / pop for c in gen_counts.values()]
        gen_entropy = -sum(p * math.log2(p) for p in gen_probs if p > 0)

        self.snapshots.append({
            'tick': tick,
            'pop': pop,
            'avg_energy': sum(energies) / pop,
            'energy_entropy': energy_entropy,
            'avg_generation': sum(generations) / pop,
            'max_generation': max(generations),
            'gen_entropy': gen_entropy,
            'avg_memory': sum(memory_sizes) / pop,
            'season': season,
        })

    def resilience_index(self) -> float:
        """How well does the population recover from winter?
        Measures pop ratio: first-spring-tick / last-winter-tick across all cycles."""
        if len(self.snapshots) < 20:
            return 0.0

        winter_lows = []
        spring_highs = []
        prev_season = -1
        for snap in self.snapshots:
            s = snap['season']
            if prev_season == 3 and s == 0:  # winter -> spring transition
                winter_lows.append(snap['pop'])
            if prev_season == 0 and s == 1:  # spring -> summer transition
                spring_highs.append(snap['pop'])
            prev_season = s

        if not winter_lows or not spring_highs:
            return 0.0

        pairs = min(len(winter_lows), len(spring_highs))
        ratios = [spring_highs[i] / max(winter_lows[i], 1) for i in range(pairs)]
        return sum(ratios) / len(ratios) if ratios else 0.0


if __name__ == '__main__':
    # Quick self-test with synthetic data
    analyzer = SignalAnalyzer()

    # Scenario: agents that have learned a code
    # Signal 0 = food, Signal 1 = danger, Signal 2 = friends, Signal 3 = alone
    import random
    random.seed(42)

    for _ in range(500):
        r = random.random()
        if r < 0.3:
            ctx = 'food_near'
            sig = 0 if random.random() < 0.8 else random.randint(0, 3)
        elif r < 0.5:
            ctx = 'danger_near'
            sig = 1 if random.random() < 0.7 else random.randint(0, 3)
        elif r < 0.8:
            ctx = 'friends_near'
            sig = 2 if random.random() < 0.6 else random.randint(0, 3)
        else:
            ctx = 'alone'
            sig = 3 if random.random() < 0.5 else random.randint(0, 3)

        analyzer.observe(sig, ctx)

    print(analyzer.interpretation())
    print()

    spec = analyzer.signal_specificity()
    print("Signal specificity:")
    for name, data in spec.items():
        print(f"  {name}: specificity={data['specificity']:.3f} (entropy={data['entropy']:.3f})")

    print()
    pred = analyzer.context_predictability()
    print("Context predictability:")
    for ctx, data in pred.items():
        print(f"  {ctx}: predictability={data['predictability']:.3f}, "
              f"dominant={data['dominant_signal']} ({data['dominant_prob']:.0%})")
