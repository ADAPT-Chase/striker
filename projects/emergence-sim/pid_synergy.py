#!/usr/bin/env python3
"""
🧠 PID-BASED SYNERGY MEASUREMENT FOR EMERGENCE SIM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Partial Information Decomposition (PID) breaks down the information
that two source variables provide about a target into four atoms:

  I(S1, S2 → T) = Redundancy + Unique_1 + Unique_2 + Synergy

Where:
  Redundancy = info both sources share about target
  Unique_1   = info only source 1 has about target
  Unique_2   = info only source 2 has about target
  Synergy    = info NEITHER source has alone, but TOGETHER they provide

Synergy is the transformation metric we want. If synergy is high,
agents are genuinely computing — combining inputs to produce
outputs that neither input contained alone. If synergy is low
but MI is high, agents are just copying/relaying (redundancy dominates).

Implementation: I_min (Williams & Beer 2010) for redundancy estimation.
It's the simplest PID framework and sufficient for discrete signals.

Applied to emergence sim:
  Source 1 = signal state of cluster A at time t
  Source 2 = signal state of cluster B at time t  
  Target   = signal state of cluster C at time t+1 (where C neighbors both A and B)

If C's future signal is predictable from A alone OR B alone = redundancy/unique.
If C's future signal requires knowing BOTH A and B = synergy = computation.

Striker, April 2026
"""

import math
from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Optional
from itertools import combinations


def entropy(seq):
    """Shannon entropy of a discrete sequence."""
    if not seq:
        return 0.0
    counts = Counter(seq)
    total = len(seq)
    return -sum((c/total) * math.log2(c/total) for c in counts.values() if c > 0)


def conditional_entropy(target, given):
    """H(T|G) = H(T,G) - H(G)"""
    if len(target) != len(given) or not target:
        return 0.0
    joint = Counter(zip(target, given))
    h_joint = entropy(list(zip(target, given)))
    h_given = entropy(given)
    return max(0.0, h_joint - h_given)


def mutual_information(x, y):
    """I(X;Y) = H(X) + H(Y) - H(X,Y)"""
    if len(x) != len(y) or not x:
        return 0.0
    return max(0.0, entropy(x) + entropy(y) - entropy(list(zip(x, y))))


def conditional_mutual_information(x, y, z):
    """I(X;Y|Z) = H(X,Z) + H(Y,Z) - H(X,Y,Z) - H(Z)"""
    if len(x) != len(y) or len(x) != len(z) or not x:
        return 0.0
    xz = list(zip(x, z))
    yz = list(zip(y, z))
    xyz = list(zip(x, y, z))
    return max(0.0, entropy(xz) + entropy(yz) - entropy(xyz) - entropy(z))


def specific_information(target_seq, source_seq, source_val):
    """
    Specific information: I(T; S=s) = sum_t P(t|s) * log2(P(t|s) / P(t))
    
    How much does knowing S=s tell you about T?
    """
    # P(t)
    t_counts = Counter(target_seq)
    t_total = len(target_seq)
    p_t = {t: c/t_total for t, c in t_counts.items()}
    
    # P(t|s)
    conditional_counts = Counter()
    s_count = 0
    for t, s in zip(target_seq, source_seq):
        if s == source_val:
            conditional_counts[t] += 1
            s_count += 1
    
    if s_count == 0:
        return 0.0
    
    p_t_given_s = {t: c/s_count for t, c in conditional_counts.items()}
    
    # Specific info
    si = 0.0
    for t, p_ts in p_t_given_s.items():
        if p_ts > 0 and p_t.get(t, 0) > 0:
            si += p_ts * math.log2(p_ts / p_t[t])
    
    return si


def i_min_redundancy(target_seq, source1_seq, source2_seq):
    """
    I_min redundancy (Williams & Beer 2010).
    
    Redundancy = sum_t P(t) * min(I_spec(T;S1=s1→t), I_spec(T;S2=s2→t))
    
    For each target value, the redundant information is the MINIMUM
    specific information that either source provides about it.
    
    This is conservative — it only counts information that BOTH sources
    carry about the same target outcome.
    """
    n = len(target_seq)
    if n == 0:
        return 0.0
    
    # Get unique target values and their probabilities
    t_counts = Counter(target_seq)
    t_total = len(target_seq)
    
    # For each target value t, compute min specific info from either source
    redundancy = 0.0
    
    for t_val, t_count in t_counts.items():
        p_t = t_count / t_total
        
        # Specific info from source 1 about this target value
        # I_spec(t; S1) = sum_s1 P(s1|t) * log2(P(t|s1) / P(t))
        # Simplified: for each s1 value, what does it tell about t?
        si_s1 = _min_specific_info_for_target(target_seq, source1_seq, t_val)
        si_s2 = _min_specific_info_for_target(target_seq, source2_seq, t_val)
        
        redundancy += p_t * min(si_s1, si_s2)
    
    return max(0.0, redundancy)


def _min_specific_info_for_target(target_seq, source_seq, t_val):
    """
    Minimum specific information that source provides about target value t_val.
    
    For I_min: we want the minimum over source values of the 
    positive part of the pointwise MI.
    
    Simplified version: compute I(T=t; S) using the approach from
    Williams & Beer — sum over source values of P(s) * max(0, log(P(t|s)/P(t)))
    weighted to give the specific surprise reduction.
    """
    n = len(target_seq)
    p_t = sum(1 for t in target_seq if t == t_val) / n
    
    if p_t == 0 or p_t == 1:
        return 0.0
    
    # Group by source values
    source_groups = defaultdict(lambda: {'total': 0, 't_count': 0})
    for t, s in zip(target_seq, source_seq):
        source_groups[s]['total'] += 1
        if t == t_val:
            source_groups[s]['t_count'] += 1
    
    # Specific info: sum over source values of P(s) * max(0, log(P(t|s)/P(t)))
    # This gives the information the source provides specifically about this t
    si = 0.0
    for s_val, group in source_groups.items():
        p_s = group['total'] / n
        p_t_given_s = group['t_count'] / group['total'] if group['total'] > 0 else 0
        
        if p_t_given_s > 0 and p_t > 0:
            # Positive specific information only (I_min definition)
            pointwise = math.log2(p_t_given_s / p_t)
            if pointwise > 0:
                si += p_s * pointwise
    
    return si


def pid_decompose(target_seq, source1_seq, source2_seq):
    """
    Full PID decomposition using I_min.
    
    Returns dict with:
      - total_mi: I(S1,S2 → T)
      - redundancy: information both sources share about target
      - unique_1: information only source 1 has
      - unique_2: information only source 2 has
      - synergy: information requiring BOTH sources
      - synergy_ratio: synergy / total_mi (our key metric)
    """
    n = len(target_seq)
    if n < 20:
        return {'total_mi': 0, 'redundancy': 0, 'unique_1': 0, 
                'unique_2': 0, 'synergy': 0, 'synergy_ratio': 0}
    
    # Joint source
    joint_source = list(zip(source1_seq, source2_seq))
    
    # Total MI: I(S1,S2; T)
    total_mi = mutual_information(joint_source, target_seq)
    
    # Individual MIs
    mi_s1 = mutual_information(source1_seq, target_seq)
    mi_s2 = mutual_information(source2_seq, target_seq)
    
    # Redundancy via I_min
    redundancy = i_min_redundancy(target_seq, source1_seq, source2_seq)
    
    # PID identities:
    # mi_s1 = redundancy + unique_1
    # mi_s2 = redundancy + unique_2
    # total_mi = redundancy + unique_1 + unique_2 + synergy
    unique_1 = max(0.0, mi_s1 - redundancy)
    unique_2 = max(0.0, mi_s2 - redundancy)
    synergy = max(0.0, total_mi - redundancy - unique_1 - unique_2)
    
    synergy_ratio = synergy / total_mi if total_mi > 0.01 else 0.0
    
    return {
        'total_mi': round(total_mi, 4),
        'redundancy': round(redundancy, 4),
        'unique_1': round(unique_1, 4),
        'unique_2': round(unique_2, 4),
        'synergy': round(synergy, 4),
        'synergy_ratio': round(synergy_ratio, 4),
        'mi_s1': round(mi_s1, 4),
        'mi_s2': round(mi_s2, 4),
    }


# ── Agent-level PID measurement ──────────────────────────────────────

def discretize_signal_state(agents, num_signals=4):
    """Convert agent signals to a discrete population state."""
    counts = [0] * num_signals
    for a in agents:
        if hasattr(a, 'current_signal') and a.current_signal is not None and a.current_signal >= 0:
            counts[a.current_signal] += 1
    total = sum(counts)
    if total == 0:
        return 'silent'
    # Return dominant signal (coarse discretization)
    return max(range(num_signals), key=lambda i: counts[i])


def cluster_dominant_signal(cluster_agents, num_signals=4):
    """Dominant signal in a spatial cluster."""
    counts = [0] * num_signals
    for a in cluster_agents:
        if hasattr(a, 'current_signal') and a.current_signal is not None and a.current_signal >= 0:
            counts[a.current_signal] += 1
    total = sum(counts)
    if total == 0:
        return -1
    return max(range(num_signals), key=lambda i: counts[i])


def spatial_clusters(agents, cell_size=20.0):
    """Group agents into grid cells."""
    grid = defaultdict(list)
    for a in agents:
        gx = int(a.x / cell_size)
        gy = int(a.y / cell_size)
        grid[(gx, gy)].append(a)
    return dict(grid)


def neighboring_cells(cell_id):
    """Get Moore neighborhood of a grid cell."""
    gx, gy = cell_id
    neighbors = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            neighbors.append((gx + dx, gy + dy))
    return neighbors


class PIDSynergyAnalyzer:
    """
    Measures synergy in agent communication using PID.
    
    For each spatial cluster C with neighbors A and B:
      Source 1 = signal state of A at time t
      Source 2 = signal state of B at time t
      Target   = signal state of C at time t+1
    
    High synergy means C's future depends on the COMBINATION of A and B,
    not either alone. That's genuine computation.
    """
    
    def __init__(self, num_signals=4, cell_size=20.0):
        self.num_signals = num_signals
        self.cell_size = cell_size
        
        # Time series per cluster
        self.cluster_history = defaultdict(list)  # cell_id -> [dominant_signal_per_tick]
        self.tick_count = 0
        
        # Window params
        self.window = 100
        self.stride = 50
    
    def record_tick(self, agents):
        """Record cluster states for one tick."""
        self.tick_count += 1
        clusters = spatial_clusters(agents, self.cell_size)
        
        # Record dominant signal per cluster
        active_cells = set()
        for cell_id, cell_agents in clusters.items():
            dom = cluster_dominant_signal(cell_agents, self.num_signals)
            self.cluster_history[cell_id].append(dom)
            active_cells.add(cell_id)
        
        # Cells that existed before but have no agents now
        for cell_id in list(self.cluster_history.keys()):
            if cell_id not in active_cells:
                self.cluster_history[cell_id].append(-1)
    
    def analyze(self) -> Dict:
        """
        Run PID analysis on recorded data.
        
        For each window, find triplets of neighboring clusters (A, B, C)
        and decompose I(A_t, B_t → C_{t+1}) into PID atoms.
        """
        if self.tick_count < self.window + 1:
            return {'error': f'Need {self.window+1}+ ticks, have {self.tick_count}'}
        
        # Find all valid triplets: C has neighbors A, B
        all_cells = [c for c, hist in self.cluster_history.items() 
                     if len(hist) >= self.window and sum(1 for h in hist if h >= 0) > self.window * 0.3]
        
        if len(all_cells) < 3:
            return {'error': 'Too few active clusters', 'cells': len(all_cells)}
        
        # Build neighbor map
        neighbor_map = {}
        for cell in all_cells:
            nbrs = [n for n in neighboring_cells(cell) if n in set(all_cells)]
            if len(nbrs) >= 2:
                neighbor_map[cell] = nbrs
        
        if not neighbor_map:
            return {'error': 'No cells with 2+ active neighbors'}
        
        # Analyze windows
        window_results = []
        
        for start in range(0, self.tick_count - self.window, self.stride):
            end = start + self.window
            
            synergy_scores = []
            redundancy_scores = []
            pid_decomps = []
            
            for target_cell, neighbors in neighbor_map.items():
                # Try pairs of neighbors as sources
                for a_cell, b_cell in combinations(neighbors[:4], 2):  # limit combos
                    # Source sequences at time t
                    s1 = self.cluster_history[a_cell][start:end]
                    s2 = self.cluster_history[b_cell][start:end]
                    # Target at time t+1
                    target = self.cluster_history[target_cell][start+1:end+1]
                    
                    # Filter out ticks where any is inactive
                    valid = [(s1[i], s2[i], target[i]) for i in range(len(target))
                             if s1[i] >= 0 and s2[i] >= 0 and target[i] >= 0]
                    
                    if len(valid) < 20:
                        continue
                    
                    s1_clean = [v[0] for v in valid]
                    s2_clean = [v[1] for v in valid]
                    t_clean = [v[2] for v in valid]
                    
                    pid = pid_decompose(t_clean, s1_clean, s2_clean)
                    
                    if pid['total_mi'] > 0.01:
                        synergy_scores.append(pid['synergy'])
                        redundancy_scores.append(pid['redundancy'])
                        pid_decomps.append(pid)
            
            if synergy_scores:
                mean_synergy = sum(synergy_scores) / len(synergy_scores)
                mean_redundancy = sum(redundancy_scores) / len(redundancy_scores)
                mean_ratio = sum(p['synergy_ratio'] for p in pid_decomps) / len(pid_decomps)
                
                window_results.append({
                    'window_start': start,
                    'n_triplets': len(synergy_scores),
                    'mean_synergy': round(mean_synergy, 4),
                    'mean_redundancy': round(mean_redundancy, 4),
                    'mean_synergy_ratio': round(mean_ratio, 4),
                    'max_synergy': round(max(synergy_scores), 4),
                })
        
        if not window_results:
            return {'error': 'No valid triplets in any window'}
        
        # Summary
        summary = {
            'n_windows': len(window_results),
            'n_active_cells': len(all_cells),
            'n_triplet_cells': len(neighbor_map),
            'mean_synergy': round(sum(w['mean_synergy'] for w in window_results) / len(window_results), 4),
            'mean_redundancy': round(sum(w['mean_redundancy'] for w in window_results) / len(window_results), 4),
            'mean_synergy_ratio': round(sum(w['mean_synergy_ratio'] for w in window_results) / len(window_results), 4),
            'max_synergy': round(max(w['max_synergy'] for w in window_results), 4),
            'synergy_trend': self._compute_trend([w['mean_synergy'] for w in window_results]),
        }
        
        return {
            'summary': summary,
            'windows': window_results,
        }
    
    def _compute_trend(self, values):
        """Simple linear trend: positive = increasing, negative = decreasing."""
        if len(values) < 3:
            return 0.0
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        
        if den == 0:
            return 0.0
        return round(num / den, 6)


# ── Quick validation ──────────────────────────────────────────────────

def test_pid_basic():
    """Verify PID on known cases."""
    import random
    random.seed(42)
    n = 1000
    
    # Case 1: XOR — pure synergy
    # Target = S1 XOR S2. Neither source alone predicts target.
    s1 = [random.choice([0, 1]) for _ in range(n)]
    s2 = [random.choice([0, 1]) for _ in range(n)]
    t_xor = [a ^ b for a, b in zip(s1, s2)]
    
    pid_xor = pid_decompose(t_xor, s1, s2)
    
    # Case 2: COPY — pure redundancy
    # Target = S1 = S2. Both sources carry identical info.
    s_same = [random.choice([0, 1]) for _ in range(n)]
    t_copy = list(s_same)
    
    pid_copy = pid_decompose(t_copy, s_same, s_same)
    
    # Case 3: UNIQUE — target depends on only one source
    s1_u = [random.choice([0, 1]) for _ in range(n)]
    s2_u = [random.choice([0, 1]) for _ in range(n)]  # irrelevant
    t_unique = list(s1_u)
    
    pid_unique = pid_decompose(t_unique, s1_u, s2_u)
    
    # Case 4: NOISE — no structure
    t_noise = [random.choice([0, 1]) for _ in range(n)]
    pid_noise = pid_decompose(t_noise, s1, s2)
    
    print("=" * 60)
    print("PID VALIDATION")
    print("=" * 60)
    
    cases = [
        ("XOR (pure synergy)", pid_xor),
        ("COPY (pure redundancy)", pid_copy),
        ("UNIQUE (one source)", pid_unique),
        ("NOISE (no structure)", pid_noise),
    ]
    
    for name, pid in cases:
        print(f"\n  {name}:")
        print(f"    Total MI:    {pid['total_mi']:.4f}")
        print(f"    Redundancy:  {pid['redundancy']:.4f}")
        print(f"    Unique 1:    {pid['unique_1']:.4f}")
        print(f"    Unique 2:    {pid['unique_2']:.4f}")
        print(f"    Synergy:     {pid['synergy']:.4f}")
        print(f"    Syn ratio:   {pid['synergy_ratio']:.4f}")
    
    # Validate expectations
    checks = []
    checks.append(("XOR synergy > redundancy", pid_xor['synergy'] > pid_xor['redundancy']))
    checks.append(("COPY redundancy > synergy", pid_copy['redundancy'] > pid_copy['synergy']))
    checks.append(("UNIQUE has unique_1 >> unique_2", pid_unique['unique_1'] > pid_unique['unique_2'] * 2))
    checks.append(("NOISE total MI ≈ 0", pid_noise['total_mi'] < 0.1))
    
    print(f"\n{'─' * 60}")
    print("CHECKS:")
    all_pass = True
    for desc, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_pass = False
    
    return all_pass


if __name__ == '__main__':
    test_pid_basic()
