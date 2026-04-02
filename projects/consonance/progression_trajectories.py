#!/usr/bin/env python3
"""
Chord Progression Trajectories — Music as paths through entropy space.

If consonance is phase detection and chords live in a 2D phase space 
(avg entropy × entropy variance), then chord progressions are TRAJECTORIES 
through that space.

The hypothesis: common progressions trace characteristic paths.
- I → V → I should spike in variance (tension) then return to stability
- I → IV → V → I should rise gradually then resolve
- ii → V → I (jazz turnaround) should spiral toward the tonic
- Deceptive cadences (V → vi) should land in the wrong part of the space

If this works, harmony is dynamics in an entropy landscape.
"""

import math
import itertools
from chord_entropy import (
    chord_pairwise_entropy, entropy_variance, chord_max_entropy,
    semitones_to_ratio, CHORDS
)
from harmonic_entropy import harmonic_entropy


# ─── Common chord voicings in C major (MIDI-style semitones from C) ───

# Using close-position voicings rooted in a reasonable register
VOICINGS = {
    # Triads
    'C':    [0, 4, 7],       # C major
    'Dm':   [2, 5, 9],       # D minor
    'Em':   [4, 7, 11],      # E minor
    'F':    [5, 9, 12],      # F major
    'G':    [7, 11, 14],     # G major
    'Am':   [9, 12, 16],     # A minor
    'Bdim': [11, 14, 17],    # B diminished
    
    # 7th chords
    'Cmaj7': [0, 4, 7, 11],
    'Dm7':   [2, 5, 9, 12],
    'Em7':   [4, 7, 11, 14],
    'Fmaj7': [5, 9, 12, 16],
    'G7':    [7, 11, 14, 17],
    'Am7':   [9, 12, 16, 19],
    'Bm7b5': [11, 14, 17, 21],
    
    # Extra
    'C/E':  [4, 7, 12],      # First inversion
    'F/A':  [9, 12, 17],     # First inversion
    'Gsus4': [7, 12, 14],    # Sus4
    'Cadd9': [0, 4, 7, 14],  # Add 9
}


def chord_entropy_coords(voicing):
    """Get the (avg_entropy, entropy_variance) coordinates of a voicing."""
    # Normalize to intervals from lowest note
    base = min(voicing)
    normalized = [n - base for n in voicing]
    
    avg_he = chord_pairwise_entropy(normalized)
    he_var = entropy_variance(normalized)
    max_he = chord_max_entropy(normalized)
    
    return {
        'avg_entropy': avg_he,
        'variance': he_var,
        'max_entropy': max_he,
    }


# ─── Common Progressions ───

PROGRESSIONS = {
    # Classical
    'I-V-I (Authentic)':        ['C', 'G', 'C'],
    'I-IV-V-I (Classical)':     ['C', 'F', 'G', 'C'],
    'I-IV-I (Plagal)':          ['C', 'F', 'C'],
    'I-vi-IV-V (50s)':          ['C', 'Am', 'F', 'G'],
    
    # Jazz
    'ii-V-I (Jazz)':            ['Dm7', 'G7', 'Cmaj7'],
    'I-vi-ii-V (Turnaround)':   ['Cmaj7', 'Am7', 'Dm7', 'G7'],
    
    # Pop/Rock
    'I-V-vi-IV (Axis)':         ['C', 'G', 'Am', 'F'],
    'I-IV-vi-V (Pop)':          ['C', 'F', 'Am', 'G'],
    'vi-IV-I-V (Emo)':          ['Am', 'F', 'C', 'G'],
    
    # Deceptive/interesting
    'I-V-vi (Deceptive)':       ['C', 'G', 'Am'],
    'I-bVII-IV (Mixolydian)':   ['C', 'Bdim', 'F'],
    'I-iii-vi-ii-V (Circle)':   ['C', 'Em', 'Am', 'Dm', 'G'],
}


def analyze_progression(name, chords):
    """Compute entropy trajectory for a chord progression."""
    trajectory = []
    
    for chord_name in chords:
        if chord_name not in VOICINGS:
            print(f"  ⚠️  Unknown chord: {chord_name}")
            continue
        
        voicing = VOICINGS[chord_name]
        coords = chord_entropy_coords(voicing)
        trajectory.append({
            'chord': chord_name,
            'voicing': voicing,
            **coords,
        })
    
    return trajectory


def trajectory_metrics(trajectory):
    """Compute summary metrics for a trajectory."""
    if len(trajectory) < 2:
        return {}
    
    # Total path length in entropy space
    path_length = 0
    for i in range(1, len(trajectory)):
        dx = trajectory[i]['avg_entropy'] - trajectory[i-1]['avg_entropy']
        dy = trajectory[i]['variance'] - trajectory[i-1]['variance']
        path_length += math.sqrt(dx**2 + dy**2)
    
    # Net displacement (start to end)
    dx = trajectory[-1]['avg_entropy'] - trajectory[0]['avg_entropy']
    dy = trajectory[-1]['variance'] - trajectory[0]['variance']
    net_displacement = math.sqrt(dx**2 + dy**2)
    
    # Circularity: how much does it return to start?
    circularity = 1 - net_displacement / (path_length + 0.001)
    
    # Max variance spike (tension peak)
    max_var = max(t['variance'] for t in trajectory)
    min_var = min(t['variance'] for t in trajectory)
    tension_range = max_var - min_var
    
    # Entropy range
    max_ent = max(t['avg_entropy'] for t in trajectory)
    min_ent = min(t['avg_entropy'] for t in trajectory)
    
    return {
        'path_length': path_length,
        'net_displacement': net_displacement,
        'circularity': circularity,
        'tension_range': tension_range,
        'entropy_range': max_ent - min_ent,
        'max_variance': max_var,
    }


def ascii_trajectory(trajectory, label, width=50, height=20):
    """Draw an ASCII trajectory in entropy space."""
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Get bounds across this trajectory
    all_ent = [t['avg_entropy'] for t in trajectory]
    all_var = [t['variance'] for t in trajectory]
    
    # Add padding
    min_e = min(all_ent) - 0.3
    max_e = max(all_ent) + 0.3
    min_v = min(all_var) - 0.3
    max_v = max(all_var) + 0.3
    
    range_e = max(max_e - min_e, 0.1)
    range_v = max(max_v - min_v, 0.1)
    
    # Draw trajectory with numbered points
    points = []
    for i, t in enumerate(trajectory):
        x = int((t['avg_entropy'] - min_e) / range_e * (width - 1))
        y = height - 1 - int((t['variance'] - min_v) / range_v * (height - 1))
        x = max(0, min(width - 1, x))
        y = max(0, min(height - 1, y))
        points.append((x, y))
        grid[y][x] = str(i + 1) if i < 9 else chr(ord('A') + i - 9)
    
    # Draw arrows between consecutive points
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        
        # Simple line drawing
        steps = max(abs(x2 - x1), abs(y2 - y1))
        if steps > 1:
            for s in range(1, steps):
                t = s / steps
                mx = int(x1 + (x2 - x1) * t)
                my = int(y1 + (y2 - y1) * t)
                if grid[my][mx] == ' ':
                    # Choose arrow character based on direction
                    dx = x2 - x1
                    dy = y2 - y1
                    if abs(dx) > abs(dy):
                        grid[my][mx] = '→' if dx > 0 else '←'
                    else:
                        grid[my][mx] = '↑' if dy < 0 else '↓'
    
    print(f"\n  {label}")
    print(f"  Var ↑")
    for row in grid:
        print(f"  │{''.join(row)}")
    print(f"  └{'─' * width}→ Avg H(E)")
    
    # Legend
    for i, t in enumerate(trajectory):
        marker = str(i + 1) if i < 9 else chr(ord('A') + i - 9)
        print(f"    {marker} = {t['chord']:>8s}  H(E)={t['avg_entropy']:.2f}  var={t['variance']:.2f}")


def main():
    print("=" * 80)
    print("  CHORD PROGRESSION TRAJECTORIES")
    print("  Music as paths through entropy space")
    print("=" * 80)
    
    all_results = {}
    
    for name, chords in PROGRESSIONS.items():
        trajectory = analyze_progression(name, chords)
        metrics = trajectory_metrics(trajectory)
        all_results[name] = {'trajectory': trajectory, 'metrics': metrics}
    
    # ─── Summary Table ───
    print(f"\n  {'Progression':>28s}  │ {'PathLen':>7s}  {'Circle':>6s}  {'TensRng':>7s}  {'EntRng':>6s}  {'MaxVar':>6s}")
    print(f"  {'─'*28}  │ {'─'*7}  {'─'*6}  {'─'*7}  {'─'*6}  {'─'*6}")
    
    for name in sorted(all_results, key=lambda n: all_results[n]['metrics'].get('tension_range', 0), reverse=True):
        m = all_results[name]['metrics']
        if not m:
            continue
        print(f"  {name:>28s}  │ {m['path_length']:>7.2f}  {m['circularity']:>6.2f}  "
              f"{m['tension_range']:>7.2f}  {m['entropy_range']:>6.2f}  {m['max_variance']:>6.2f}")
    
    # ─── Detailed Trajectories ───
    print(f"\n{'='*80}")
    print(f"  TRAJECTORY PLOTS")
    print(f"{'='*80}")
    
    # Plot the most interesting ones
    for name in ['I-V-I (Authentic)', 'ii-V-I (Jazz)', 'I-vi-IV-V (50s)', 
                 'I-V-vi-IV (Axis)', 'I-iii-vi-ii-V (Circle)']:
        if name not in all_results:
            continue
        trajectory = all_results[name]['trajectory']
        if trajectory:
            ascii_trajectory(trajectory, name)
    
    # ─── Cadence Comparison ───
    print(f"\n{'='*80}")
    print(f"  CADENCE COMPARISON")
    print(f"  How do different cadence types move through entropy space?")
    print(f"{'='*80}\n")
    
    # Compare the V→I step across progressions
    cadences = {
        'Authentic (V→I)': (['G', 'C'], 'tension → release'),
        'Plagal (IV→I)': (['F', 'C'], 'gentle → home'),
        'Deceptive (V→vi)': (['G', 'Am'], 'tension → surprise'),
        'Half (→V)': (['C', 'G'], 'home → tension'),
    }
    
    print(f"  {'Cadence':>25s}  │ {'Start H(E)':>10s}  {'End H(E)':>10s}  {'ΔH(E)':>8s}  │ {'Start Var':>10s}  {'End Var':>10s}  {'ΔVar':>8s}")
    print(f"  {'─'*25}  │ {'─'*10}  {'─'*10}  {'─'*8}  │ {'─'*10}  {'─'*10}  {'─'*8}")
    
    for name, (chords, desc) in cadences.items():
        traj = analyze_progression(name, chords)
        if len(traj) >= 2:
            delta_he = traj[-1]['avg_entropy'] - traj[0]['avg_entropy']
            delta_var = traj[-1]['variance'] - traj[0]['variance']
            print(f"  {name:>25s}  │ {traj[0]['avg_entropy']:>10.3f}  {traj[-1]['avg_entropy']:>10.3f}  "
                  f"{delta_he:>+8.3f}  │ {traj[0]['variance']:>10.3f}  {traj[-1]['variance']:>10.3f}  {delta_var:>+8.3f}")
    
    # ─── The ii-V-I Deep Dive ───
    print(f"\n{'='*80}")
    print(f"  THE ii-V-I: Jazz's Favorite Trajectory")
    print(f"{'='*80}\n")
    
    jazz_traj = all_results.get('ii-V-I (Jazz)', {}).get('trajectory', [])
    if jazz_traj:
        for i, t in enumerate(jazz_traj):
            arrow = " → " if i < len(jazz_traj) - 1 else ""
            print(f"  [{t['chord']:>6s}]  avg H(E) = {t['avg_entropy']:.3f}  "
                  f"var = {t['variance']:.3f}  max = {t['max_entropy']:.3f}{arrow}")
        
        print()
        
        if len(jazz_traj) >= 3:
            # Dm7 → G7
            dh1 = jazz_traj[1]['avg_entropy'] - jazz_traj[0]['avg_entropy']
            dv1 = jazz_traj[1]['variance'] - jazz_traj[0]['variance']
            # G7 → Cmaj7
            dh2 = jazz_traj[2]['avg_entropy'] - jazz_traj[1]['avg_entropy']
            dv2 = jazz_traj[2]['variance'] - jazz_traj[1]['variance']
            
            print(f"  Dm7 → G7:   ΔH(E) = {dh1:+.3f}  ΔVar = {dv1:+.3f}")
            print(f"  G7 → Cmaj7: ΔH(E) = {dh2:+.3f}  ΔVar = {dv2:+.3f}")
            print()
            
            if dh1 > 0 and dh2 < 0:
                print("  ✅ ii → V increases entropy (builds tension)")
                print("  ✅ V → I decreases entropy (resolves)")
                print("  The ii-V-I is a round trip through entropy space.")
            elif dh1 > 0:
                print("  ✅ ii → V increases entropy (builds tension)")
                print(f"  ⚠️  V → I entropy change: {dh2:+.3f} (expected decrease)")
            else:
                print(f"  ⚠️  ii → V entropy change: {dh1:+.3f}")
                print(f"  ⚠️  V → I entropy change: {dh2:+.3f}")
    
    # ─── Key Findings ───
    print(f"\n{'='*80}")
    print(f"  KEY FINDINGS")
    print(f"{'='*80}\n")
    
    # Which progression has highest circularity?
    most_circular = max(all_results, key=lambda n: all_results[n]['metrics'].get('circularity', 0))
    most_tension = max(all_results, key=lambda n: all_results[n]['metrics'].get('tension_range', 0))
    longest_path = max(all_results, key=lambda n: all_results[n]['metrics'].get('path_length', 0))
    
    print(f"  Most circular progression: {most_circular}")
    print(f"    (circularity = {all_results[most_circular]['metrics']['circularity']:.3f})")
    print()
    print(f"  Highest tension range: {most_tension}")
    print(f"    (tension range = {all_results[most_tension]['metrics']['tension_range']:.3f})")
    print()
    print(f"  Longest path through entropy space: {longest_path}")
    print(f"    (path length = {all_results[longest_path]['metrics']['path_length']:.3f})")
    print()
    print("  Progressions that return to their starting point (high circularity)")
    print("  are the ones that feel 'complete' — they're closed loops in entropy space.")
    print("  Progressions that end far from their start feel 'open' or 'unresolved.'")
    print()
    print("  The tension range captures how much 'drama' a progression has —")
    print("  how far it ventures into high-variance territory before resolving.")


if __name__ == '__main__':
    main()
