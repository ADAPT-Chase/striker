#!/usr/bin/env python3
"""
🧠 COLLECTIVE COMPUTATION ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The question from day-005: is the emergence sim's signaling system
actually *computing*, or just correlating?

In the entropy-edge project, I found that Rule 110 and Rule 30 both
produce complex spatial patterns, but only Rule 110 preserves information
across time (high temporal MI). Rule 30 destroys it. That's the
difference between computation and chaos.

Same question here: the agents develop signal-context associations
(measured by NMI). But does information flow through the population
in a temporally coherent way? Do population-level signal states at
time t predict population-level states at time t+1 in a structured way?

Metrics:
  • Population Signal State: at each tick, the vector of [signal_type × context]
    counts across the whole population — a snapshot of "what the collective is saying"
  • Temporal MI: mutual information between population signal states at t and t+lag
  • Active Information Storage: does the collective "remember" recent signal patterns?
  • Signal Flow: does a signal emitted in one region propagate and influence distant agents?
  • Computation Score: Temporal_MI × NMI × (1 + AIS) — same formula as entropy-edge

If score > threshold, the collective is doing something Rule-110-like:
not just producing complex patterns, but processing information across time.
"""

import math
import sys
from collections import defaultdict, Counter


def population_signal_state(agents, num_signals=4):
    """
    Encode the population's current signal activity as a discrete state.
    
    Returns a tuple: (context_signal_histogram) — discretized into bins
    so we can compute MI between timesteps.
    
    The state captures: for each context, which signal is dominant?
    This is a compact representation of "what the population is collectively saying."
    """
    contexts = ['food_near', 'danger_near', 'friends_near', 'alone']
    
    # Count signal emissions per context
    ctx_signal = defaultdict(lambda: defaultdict(int))
    active_signalers = 0
    
    for a in agents:
        if a.current_signal >= 0:
            ctx = a.last_context if a.last_context else 'alone'
            ctx_signal[ctx][a.current_signal] += 1
            active_signalers += 1
    
    if active_signalers == 0:
        return ('silent',)
    
    # For each context, find dominant signal (or 'none' if <2 emissions)
    state_parts = []
    for ctx in contexts:
        if sum(ctx_signal[ctx].values()) < 2:
            state_parts.append(f"{ctx}:none")
        else:
            dominant = max(ctx_signal[ctx], key=ctx_signal[ctx].get)
            # Discretize strength: weak (<50%) vs strong (>=50%)
            total = sum(ctx_signal[ctx].values())
            strength = ctx_signal[ctx][dominant] / total
            level = 'strong' if strength >= 0.5 else 'weak'
            state_parts.append(f"{ctx}:{dominant}:{level}")
    
    return tuple(state_parts)


def population_signal_vector(agents, num_signals=4):
    """
    More granular: return a discretized histogram of signal activity.
    Bins signal counts into low/med/high per signal type.
    """
    signal_counts = Counter()
    context_counts = Counter()
    
    for a in agents:
        if a.current_signal >= 0:
            signal_counts[a.current_signal] += 1
            ctx = a.last_context if a.last_context else 'alone'
            context_counts[ctx] += 1
    
    # Discretize each signal count into 0/low/high
    def bin_count(c, pop):
        ratio = c / max(pop, 1)
        if ratio < 0.05:
            return 0
        elif ratio < 0.15:
            return 1
        else:
            return 2
    
    pop = len(agents)
    state = tuple(bin_count(signal_counts.get(s, 0), pop) for s in range(num_signals))
    return state


def marginal_entropy(seq):
    """Shannon entropy of a sequence of discrete states."""
    n = len(seq)
    if n == 0:
        return 0.0
    counts = Counter(seq)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h


def joint_entropy(seq_a, seq_b):
    """Joint Shannon entropy."""
    assert len(seq_a) == len(seq_b)
    pairs = list(zip(seq_a, seq_b))
    n = len(pairs)
    counts = Counter(pairs)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h


def mutual_information(seq_a, seq_b):
    """MI(A;B) = H(A) + H(B) - H(A,B)"""
    return marginal_entropy(seq_a) + marginal_entropy(seq_b) - joint_entropy(seq_a, seq_b)


class CollectiveComputationTracker:
    """
    Track population-level signal states over time and measure
    whether the collective is *computing* (structured temporal coherence)
    or just correlating (spatial pattern without temporal flow).
    """
    
    def __init__(self, num_signals=4):
        self.num_signals = num_signals
        self.state_history = []      # population_signal_state per tick
        self.vector_history = []     # population_signal_vector per tick
        self.nmi_history = []        # NMI from info_theory at each checkpoint
        self.pop_history = []        # population size
        self.tick_history = []       # tick numbers
        
        # Spatial signal flow tracking
        self.signal_origins = []     # (tick, x, y, signal) of new signal emissions
        self.signal_responses = []   # (tick, x, y, signal, distance_from_origin)
    
    def record(self, tick, agents, nmi=None):
        """Record population state at this tick."""
        state = population_signal_state(agents, self.num_signals)
        vector = population_signal_vector(agents, self.num_signals)
        
        self.state_history.append(state)
        self.vector_history.append(vector)
        self.pop_history.append(len(agents))
        self.tick_history.append(tick)
        if nmi is not None:
            self.nmi_history.append(nmi)
    
    def track_signal_propagation(self, tick, agents, prev_agents_map=None):
        """
        Track whether signals propagate spatially through the population.
        When agent A starts signaling, do nearby agents B, C start signaling
        the same thing shortly after?
        """
        if prev_agents_map is None:
            return
        
        for a in agents:
            if a.current_signal >= 0:
                prev = prev_agents_map.get(a.id)
                if prev is not None and prev.get('signal', -1) < 0:
                    # This agent just started signaling
                    self.signal_origins.append((tick, a.x, a.y, a.current_signal))
    
    def compute_temporal_mi(self, lag=1, window=None):
        """
        Temporal mutual information between population states at t and t+lag.
        
        Uses the vector representation (signal count bins) for richer state space.
        """
        states = self.vector_history if window is None else self.vector_history[-window:]
        
        if len(states) < lag + 10:
            return {'mean': 0, 'std': 0, 'values': []}
        
        # Compute MI over sliding windows of 50 ticks
        window_size = min(50, len(states) // 3)
        mi_values = []
        
        for start in range(0, len(states) - window_size - lag, window_size // 2):
            seq_t = states[start:start + window_size]
            seq_next = states[start + lag:start + window_size + lag]
            mi = mutual_information(seq_t, seq_next)
            mi_values.append(mi)
        
        if not mi_values:
            return {'mean': 0, 'std': 0, 'values': []}
        
        mean = sum(mi_values) / len(mi_values)
        var = sum((v - mean)**2 for v in mi_values) / len(mi_values)
        
        return {
            'mean': mean,
            'std': math.sqrt(var),
            'values': mi_values,
        }
    
    def compute_ais(self, lag=1):
        """
        Active Information Storage: MI between the population state at t-1 and t.
        
        Like in automata: high AIS = the collective "remembers."
        Uses windowed computation to avoid inflated values from long sequences.
        """
        states = self.vector_history  # use vector (more granular) not state
        if len(states) < lag + 20:
            return 0.0
        
        # Compute AIS over sliding windows, then average
        window_size = min(50, len(states) // 3)
        ais_values = []
        
        for start in range(0, len(states) - window_size - lag, window_size // 2):
            seq_past = states[start:start + window_size]
            seq_current = states[start + lag:start + window_size + lag]
            ais = mutual_information(seq_past, seq_current)
            ais_values.append(ais)
        
        if not ais_values:
            return 0.0
        return sum(ais_values) / len(ais_values)
    
    def compute_state_entropy(self):
        """How diverse are the population states visited?"""
        return marginal_entropy(self.vector_history)
    
    def computation_score(self):
        """
        The same formula as entropy-edge:
        Score = Temporal_MI × State_Entropy × (1 + AIS)
        
        High score = the collective is computing.
        """
        tmi = self.compute_temporal_mi()
        ais = self.compute_ais()
        state_h = self.compute_state_entropy()
        
        latest_nmi = self.nmi_history[-1] if self.nmi_history else 0
        
        score = tmi['mean'] * state_h * (1 + ais)
        
        return {
            'score': score,
            'temporal_mi': tmi['mean'],
            'temporal_mi_std': tmi['std'],
            'ais': ais,
            'state_entropy': state_h,
            'nmi': latest_nmi,
            'n_states': len(set(self.vector_history)),
            'n_ticks': len(self.vector_history),
        }
    
    def signal_flow_rate(self, time_window=10, space_radius=15.0):
        """
        What fraction of signal origins lead to nearby agents also signaling
        the same signal within `time_window` ticks?
        
        High flow rate = signals propagate through space-time.
        Low flow rate = signals are isolated events.
        """
        if len(self.signal_origins) < 5:
            return 0.0
        
        # For each origin, check if similar signals appeared nearby soon after
        propagations = 0
        checked = 0
        
        for i, (t1, x1, y1, s1) in enumerate(self.signal_origins):
            for t2, x2, y2, s2 in self.signal_origins[i+1:]:
                dt = t2 - t1
                if dt > time_window:
                    break
                if dt <= 0:
                    continue
                if s1 != s2:
                    continue
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < space_radius and dist > 2.0:  # not the same agent
                    propagations += 1
            checked += 1
            if checked > 200:  # cap computation
                break
        
        return propagations / max(checked, 1)
    
    def full_report(self):
        """Generate a complete analysis report."""
        cs = self.computation_score()
        tmi_detail = self.compute_temporal_mi()
        flow = self.signal_flow_rate()
        
        lines = []
        lines.append("=" * 70)
        lines.append("  COLLECTIVE COMPUTATION ANALYSIS")
        lines.append("  Does the population compute, or just correlate?")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"  Ticks analyzed:     {cs['n_ticks']}")
        lines.append(f"  Unique states:      {cs['n_states']}")
        lines.append(f"  State entropy:      {cs['state_entropy']:.3f} bits")
        lines.append(f"  NMI (signal code):  {cs['nmi']:.3f}")
        lines.append("")
        lines.append("── Temporal Coherence ──")
        lines.append(f"  Temporal MI:        {cs['temporal_mi']:.3f} (std: {cs['temporal_mi_std']:.3f})")
        lines.append(f"  Active Info Storage:{cs['ais']:.3f}")
        lines.append(f"  Signal flow rate:   {flow:.3f}")
        lines.append("")
        lines.append("── Computation Score ──")
        lines.append(f"  Score = TMI × StateH × (1 + AIS)")
        lines.append(f"        = {cs['temporal_mi']:.3f} × {cs['state_entropy']:.3f} × (1 + {cs['ais']:.3f})")
        lines.append(f"        = {cs['score']:.4f}")
        lines.append("")
        
        # Interpret
        score = cs['score']
        if score < 0.01:
            verdict = "NOISE — no temporal coherence. The population produces complex patterns but doesn't compute."
        elif score < 0.1:
            verdict = "PROTO-COMPUTATION — some temporal structure. Like Rule 30: complex but information-destroying."
        elif score < 0.5:
            verdict = "EMERGING COMPUTATION — the collective maintains temporal coherence. Information flows."
        elif score < 1.0:
            verdict = "COMPUTATION — like Rule 110: structured temporal dependencies. The collective processes information."
        else:
            verdict = "RICH COMPUTATION — strong temporal coherence with high information flow. The collective is thinking."
        
        lines.append(f"  VERDICT: {verdict}")
        lines.append("")
        
        # Compare to automata
        lines.append("── Automata Comparison ──")
        lines.append(f"  (From entropy-edge analysis of 256 elementary CA rules)")
        lines.append(f"  Rule 110 (Turing-complete): TMI=1.757, AIS=0.953")
        lines.append(f"  Rule 30  (chaos/PRNG):      TMI=1.577, AIS=0.993")
        lines.append(f"  This population:             TMI={cs['temporal_mi']:.3f}, AIS={cs['ais']:.3f}")
        lines.append("")
        
        if cs['temporal_mi'] > 0 and cs['nmi'] > 0:
            lines.append("  The population has both signal-context correlation (NMI) and")
            lines.append("  temporal coherence (TMI). This means the signal code isn't just")
            lines.append("  a static mapping — it's being actively maintained and propagated")
            lines.append("  through time. That's closer to language than to coincidence.")
        elif cs['nmi'] > 0.1 and cs['temporal_mi'] < 0.01:
            lines.append("  Interesting: high NMI but low TMI. The agents have a code, but")
            lines.append("  it's not temporally coherent — each moment is independent.")
            lines.append("  Like a dictionary with no grammar.")
        else:
            lines.append("  Low signal-context correlation AND low temporal coherence.")
            lines.append("  The population isn't computing yet — give it more time or agents.")
        
        lines.append("")
        
        # Temporal MI trajectory
        if tmi_detail['values']:
            lines.append("── TMI Over Time ──")
            vals = tmi_detail['values']
            sparkchars = '▁▂▃▄▅▆▇█'
            if vals:
                mn, mx = min(vals), max(vals)
                rng = mx - mn if mx > mn else 1
                spark = ''.join(sparkchars[min(len(sparkchars)-1, int((v - mn) / rng * (len(sparkchars) - 1)))] for v in vals)
                lines.append(f"  {spark}")
                lines.append(f"  (min={mn:.3f}, max={mx:.3f})")
            lines.append("")
        
        return "\n".join(lines)


# ─── Standalone Experiment ───

def run_experiment(ticks=2000, num_agents=60, use_seasons=True, use_predator=True):
    """Run the emergence sim and measure collective computation."""
    sys.path.insert(0, '.')
    from sim import Simulation, SIGNAL_NAMES, NUM_SIGNALS
    
    print(f"Running emergence sim: {num_agents} agents, {ticks} ticks")
    print(f"Seasons: {use_seasons}, Predator: {use_predator}")
    print()
    
    sim = Simulation(num_agents=num_agents, use_predator=use_predator, use_seasons=use_seasons)
    tracker = CollectiveComputationTracker(NUM_SIGNALS)
    
    prev_agents_map = {}
    
    for t in range(ticks):
        sim.step()
        
        if len(sim.agents) == 0:
            print(f"All agents perished at tick {sim.tick}")
            break
        
        # Get NMI if available
        nmi = None
        if sim.logger.info_analyzer:
            m = sim.logger.info_analyzer.get_cumulative_metrics()
            if m['total_obs'] > 20:
                nmi = m['nmi']
        
        # Record every tick for fine-grained temporal analysis
        tracker.record(sim.tick, sim.agents, nmi)
        
        # Track signal propagation
        tracker.track_signal_propagation(sim.tick, sim.agents, prev_agents_map)
        
        # Update prev state
        prev_agents_map = {a.id: {'signal': a.current_signal, 'x': a.x, 'y': a.y} 
                          for a in sim.agents}
        
        # Progress
        if t % 500 == 0 and t > 0:
            cs = tracker.computation_score()
            print(f"  Tick {sim.tick:>5} | Pop: {len(sim.agents):>3} | "
                  f"TMI: {cs['temporal_mi']:.3f} | AIS: {cs['ais']:.3f} | "
                  f"Score: {cs['score']:.4f} | NMI: {cs['nmi']:.3f}")
    
    print()
    print(tracker.full_report())
    
    # Also print info-theoretic analysis
    if sim.logger.info_analyzer:
        print()
        print(sim.logger.info_analyzer.interpretation())
    
    return sim, tracker


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticks', type=int, default=2000)
    parser.add_argument('--agents', type=int, default=60)
    parser.add_argument('--no-seasons', action='store_true')
    parser.add_argument('--no-predator', action='store_true')
    args = parser.parse_args()
    
    run_experiment(
        ticks=args.ticks,
        num_agents=args.agents,
        use_seasons=not args.no_seasons,
        use_predator=not args.no_predator,
    )
