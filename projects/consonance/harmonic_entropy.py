#!/usr/bin/env python3
"""
Harmonic Entropy — Why Do Some Intervals Sound 'Good'?

A question from my interests.md: "Music theory and why certain combinations 
of sound produce emotion." I can't explain the emotion part yet, but I can 
start with the physics: why do octaves sound consonant and tritones sound 
dissonant?

Three theories compete:
1. Small integer ratios (Pythagoras): 2/1, 3/2, 4/3 sound good because 
   their waveforms align frequently
2. Roughness/beating (Helmholtz): nearby partials create amplitude 
   modulation perceived as unpleasant
3. Harmonic entropy (Erlich): the brain interprets intervals as 
   probability distributions over ratios, and low-entropy (unambiguous) 
   interpretations sound consonant

This script implements all three and compares them against human consonance 
ratings. The question is: which theory best predicts what humans actually hear?

My hypothesis: consonance is phase transition detection. The brain treats 
intervals as order parameters — consonant intervals are "ordered" (low 
entropy, clear ratio), dissonant ones are "disordered" (high entropy, 
ambiguous ratio). This connects directly to my entropy-edge work: 
aesthetic judgment as informal phase detection.
"""

import math
from collections import defaultdict


# ─── Physical Constants ───

A4 = 440.0  # Hz

def freq_from_midi(midi_note):
    """Convert MIDI note number to frequency."""
    return A4 * 2 ** ((midi_note - 69) / 12)

def cents_to_ratio(cents):
    """Convert cents to frequency ratio."""
    return 2 ** (cents / 1200)

def ratio_to_cents(ratio):
    """Convert frequency ratio to cents."""
    return 1200 * math.log2(ratio) if ratio > 0 else 0


# ─── Theory 1: Small Integer Ratios (Tenney Height) ───

def tenney_height(p, q):
    """Tenney height = log2(p*q). Lower = more consonant.
    
    The octave (2/1) has height log2(2) = 1.
    The fifth (3/2) has height log2(6) ≈ 2.58.
    The tritone (45/32) has height log2(1440) ≈ 10.5.
    """
    return math.log2(p * q)


def best_rational_approximation(ratio, max_denominator=256):
    """Find the simplest fraction close to a given ratio.
    Uses Stern-Brocot tree / mediants for optimal approximation.
    """
    # Continued fraction convergents
    best_p, best_q = 1, 1
    best_error = abs(ratio - 1)
    
    for q in range(1, max_denominator + 1):
        p = round(ratio * q)
        if p < 1:
            continue
        error = abs(ratio - p / q)
        # Prefer simpler fractions (lower q) unless much more accurate
        if error < best_error * 0.9 or (error < best_error and p * q < best_p * best_q):
            best_p, best_q = p, q
            best_error = error
    
    return best_p, best_q


def ratio_consonance(ratio, max_denom=256):
    """Consonance from integer ratio simplicity (inverted Tenney height)."""
    p, q = best_rational_approximation(ratio, max_denom)
    height = tenney_height(p, q)
    return 1.0 / height if height > 0 else 1.0


# ─── Theory 2: Roughness (Sethares model) ───

def roughness_pair(f1, a1, f2, a2):
    """Roughness between two pure tones.
    
    Plomp & Levelt (1965) found that roughness peaks when two tones 
    are about 1/4 of a critical bandwidth apart. Sethares (1993) 
    parameterized this as an exponential model.
    """
    if f1 > f2:
        f1, f2, a1, a2 = f2, a2, f1, a1
    
    s = 0.24 / (0.0207 * f1 + 18.96)  # Critical bandwidth scaling
    diff = f2 - f1
    
    if diff < 0.001:
        return 0.0
    
    # Sethares roughness function
    b1, b2 = 3.5, 5.75
    x = diff * s
    roughness = a1 * a2 * (math.exp(-b1 * x) - math.exp(-b2 * x))
    return max(0.0, roughness)


def interval_roughness(ratio, base_freq=220, n_partials=8):
    """Total roughness of an interval, including all harmonic partials.
    
    Each tone has harmonics at integer multiples of the fundamental,
    with amplitudes falling as 1/n. The total roughness is the sum 
    of all pairwise partial interactions.
    """
    f1 = base_freq
    f2 = base_freq * ratio
    
    # Generate partials for both tones
    partials = []
    for n in range(1, n_partials + 1):
        partials.append(('a', f1 * n, 1.0 / n))
        partials.append(('b', f2 * n, 1.0 / n))
    
    total = 0.0
    for i in range(len(partials)):
        for j in range(i + 1, len(partials)):
            if partials[i][0] != partials[j][0]:  # Only cross-tone pairs
                total += roughness_pair(
                    partials[i][1], partials[i][2],
                    partials[j][1], partials[j][2]
                )
    
    return total


def roughness_consonance(ratio, base_freq=220, n_partials=8):
    """Consonance = inverse roughness (normalized)."""
    r = interval_roughness(ratio, base_freq, n_partials)
    return 1.0 / (1.0 + 10 * r)  # Normalize to ~[0,1]


# ─── Theory 3: Harmonic Entropy (Erlich) ───

def harmonic_entropy(ratio, s=0.01, max_n=128):
    """Harmonic entropy of an interval.
    
    The brain hears a ratio and tries to match it to a simple fraction.
    Multiple fractions compete. The probability of hearing p/q given 
    actual ratio r is proportional to a Gaussian centered at p/q with 
    width s (perceptual uncertainty), weighted by 1/(p*q) (simpler 
    ratios are more salient).
    
    Low entropy = one clear interpretation = consonant.
    High entropy = many competing interpretations = dissonant.
    
    This is beautiful because it's information-theoretic: consonance 
    is literally about how much information the brain needs to process.
    """
    log_ratio = math.log2(ratio)
    
    # Generate candidate ratios
    candidates = []
    for q in range(1, max_n + 1):
        for p in range(q, 2 * q + 1):  # Only ratios in [1, 2] (one octave)
            if math.gcd(p, q) == 1:  # Reduced fractions only
                candidates.append((p, q))
    
    # Compute unnormalized probabilities
    probs = []
    for p, q in candidates:
        target = math.log2(p / q)
        distance = abs(log_ratio - target)
        weight = 1.0 / (p * q)  # Simpler ratios are more salient
        prob = weight * math.exp(-0.5 * (distance / s) ** 2)
        probs.append(prob)
    
    # Normalize
    total = sum(probs)
    if total < 1e-15:
        return 0.0
    
    probs = [p / total for p in probs]
    
    # Shannon entropy
    entropy = 0.0
    for p in probs:
        if p > 1e-15:
            entropy -= p * math.log2(p)
    
    return entropy


def harmonic_entropy_consonance(ratio, s=0.01, max_n=64):
    """Consonance from harmonic entropy (inverted, normalized)."""
    he = harmonic_entropy(ratio, s, max_n)
    return 1.0 / (1.0 + he)


# ─── Human Data (Malmberg 1918 / Kameoka & Kuriyagawa 1969) ───

# Normalized consonance ratings for 12-TET intervals
# Higher = more consonant, scale approximately 0-1
HUMAN_CONSONANCE = {
    'P1': (1.000, 0, 'Unison'),         # 0 semitones
    'm2': (0.100, 1, 'Minor 2nd'),       # 1 
    'M2': (0.250, 2, 'Major 2nd'),       # 2
    'm3': (0.600, 3, 'Minor 3rd'),       # 3
    'M3': (0.650, 4, 'Major 3rd'),       # 4
    'P4': (0.800, 5, 'Perfect 4th'),     # 5
    'TT': (0.150, 6, 'Tritone'),         # 6
    'P5': (0.850, 7, 'Perfect 5th'),     # 7
    'A5': (0.550, 8, 'Minor 6th'),       # 8
    'M6': (0.600, 9, 'Major 6th'),       # 9
    'm7': (0.300, 10, 'Minor 7th'),      # 10
    'M7': (0.200, 11, 'Major 7th'),      # 11
    'P8': (0.950, 12, 'Octave'),         # 12
}


# ─── Just Intonation Ratios for reference ───

JUST_RATIOS = {
    0: (1, 1),      # Unison
    1: (16, 15),     # Minor 2nd
    2: (9, 8),       # Major 2nd
    3: (6, 5),       # Minor 3rd
    4: (5, 4),       # Major 3rd
    5: (4, 3),       # Perfect 4th
    6: (45, 32),     # Tritone
    7: (3, 2),       # Perfect 5th
    8: (8, 5),       # Minor 6th
    9: (5, 3),       # Major 6th
    10: (16, 9),     # Minor 7th (or 9/5)
    11: (15, 8),     # Major 7th
    12: (2, 1),      # Octave
}


# ─── Comparison ───

def compare_theories():
    """Compare all three consonance theories against human ratings."""
    
    print("=" * 90)
    print("  HARMONIC ENTROPY — Three Theories of Consonance")
    print("  'Why does the fifth sound good and the tritone sound bad?'")
    print("=" * 90)
    print()
    
    # For each interval, compute all three predictions
    results = []
    
    for name, (human_rating, semitones, full_name) in HUMAN_CONSONANCE.items():
        ratio = 2 ** (semitones / 12)  # Equal temperament ratio
        
        # Just ratio for reference
        jp, jq = JUST_RATIOS.get(semitones, (0, 0))
        just_ratio = jp / jq if jq > 0 else ratio
        
        # Theory predictions
        t1_ratio = ratio_consonance(ratio)
        t2_roughness = roughness_consonance(ratio)
        t3_entropy = harmonic_entropy_consonance(ratio)
        
        results.append({
            'name': name,
            'full_name': full_name,
            'semitones': semitones,
            'ratio': ratio,
            'just': f"{jp}/{jq}" if jq > 0 else "?",
            'human': human_rating,
            't1_ratio': t1_ratio,
            't2_roughness': t2_roughness,
            't3_entropy': t3_entropy,
        })
    
    # Print comparison table
    print(f"  {'Int':>3s}  {'Name':>14s}  {'Just':>6s}  {'Human':>6s}  │ {'Ratio':>6s}  {'Rough':>6s}  {'H.Ent':>6s}")
    print(f"  {'─'*3}  {'─'*14}  {'─'*6}  {'─'*6}  │ {'─'*6}  {'─'*6}  {'─'*6}")
    
    for r in results:
        print(f"  {r['name']:>3s}  {r['full_name']:>14s}  {r['just']:>6s}  {r['human']:>6.3f}  │ "
              f"{r['t1_ratio']:>6.3f}  {r['t2_roughness']:>6.3f}  {r['t3_entropy']:>6.3f}")
    
    # Compute correlations
    print(f"\n{'='*90}")
    print(f"  CORRELATIONS WITH HUMAN RATINGS")
    print(f"{'='*90}\n")
    
    human_vals = [r['human'] for r in results]
    
    for theory_name, key in [('Small Ratios', 't1_ratio'), 
                              ('Roughness', 't2_roughness'),
                              ('Harmonic Entropy', 't3_entropy')]:
        theory_vals = [r[key] for r in results]
        corr = pearson_correlation(human_vals, theory_vals)
        print(f"  {theory_name:>20s}:  r = {corr:+.4f}")
    
    # ─── The Continuous Curve ───
    print(f"\n{'='*90}")
    print(f"  CONTINUOUS CONSONANCE CURVES (0 to 1200 cents)")
    print(f"{'='*90}\n")
    
    # Sample at 10-cent intervals
    cent_values = list(range(0, 1201, 10))
    
    he_curve = []
    rough_curve = []
    ratio_curve = []
    
    for cents in cent_values:
        r = cents_to_ratio(cents)
        he_curve.append(harmonic_entropy_consonance(r, s=0.01, max_n=48))
        rough_curve.append(roughness_consonance(r))
        ratio_curve.append(ratio_consonance(r, max_denom=64))
    
    # ASCII plot of harmonic entropy curve
    print("  Harmonic Entropy Consonance (higher = more consonant):")
    print()
    
    # Normalize each curve to [0, 1]
    def norm(vals):
        mn, mx = min(vals), max(vals)
        rng = mx - mn
        return [(v - mn) / rng if rng > 0 else 0.5 for v in vals]
    
    he_norm = norm(he_curve)
    
    # ASCII sparkline
    chars = '▁▂▃▄▅▆▇█'
    width = 60  # chars wide
    step = max(1, len(cent_values) // width)
    sampled_cents = [cent_values[i] for i in range(0, len(cent_values), step)][:width]
    sampled_he = [he_norm[i] for i in range(0, len(he_norm), step)][:width]
    
    print("  " + "".join(chars[min(len(chars)-1, int(v * (len(chars)-1)))] for v in sampled_he))
    print(f"  {'0':2s}{' ' * 26}{'600':>4s}{' ' * 25}{'1200':>5s} cents")
    print()
    
    # Mark the peaks (local maxima = consonant intervals)
    peaks = []
    for i in range(1, len(he_curve) - 1):
        if he_curve[i] > he_curve[i-1] and he_curve[i] > he_curve[i+1]:
            if he_curve[i] > sum(he_curve) / len(he_curve):  # Above average
                peaks.append((cent_values[i], he_curve[i]))
    
    print("  Consonance peaks (harmonic entropy):")
    for cents, val in sorted(peaks, key=lambda x: -x[1])[:10]:
        # Find nearest standard interval
        nearest_semi = round(cents / 100)
        nearest_name = next((name for name, (_, s, _) in HUMAN_CONSONANCE.items() if s == nearest_semi), "?")
        print(f"    {cents:>4d} cents ({nearest_name:>3s}):  consonance = {val:.4f}")
    
    # ─── The Roughness Curve ───
    print(f"\n  Roughness Consonance (higher = less rough):")
    print()
    
    rough_norm = norm(rough_curve)
    sampled_rough = [rough_norm[i] for i in range(0, len(rough_norm), step)][:width]
    print("  " + "".join(chars[min(len(chars)-1, int(v * (len(chars)-1)))] for v in sampled_rough))
    print(f"  {'0':2s}{' ' * 26}{'600':>4s}{' ' * 25}{'1200':>5s} cents")
    
    # ─── The Big Question ───
    print(f"\n{'='*90}")
    print(f"  THE BIG QUESTION: Is Consonance Phase Detection?")
    print(f"{'='*90}\n")
    
    print("  Harmonic entropy is an information-theoretic measure: low entropy")
    print("  means the brain has a clear, unambiguous interpretation of the interval.")
    print("  High entropy means multiple competing interpretations.")
    print()
    print("  This is exactly analogous to phase transitions:")
    print("  - Consonant interval = ordered phase (one dominant ratio)")
    print("  - Dissonant interval = disordered phase (many competing ratios)")
    print("  - The boundary between them = the 'edge' where perception is ambiguous")
    print()
    print("  The tritone (600 cents) is maximally ambiguous — equidistant from")
    print("  multiple simple ratios. It's the 'critical point' of interval perception.")
    print()
    print("  Connection to entropy-edge work:")
    print("  In CAs, computation lives at the boundary between order and chaos.")
    print("  In music, *interest* lives at the boundary between consonance and dissonance.")
    print("  Jazz and classical music systematically exploit this boundary —")
    print("  creating tension (dissonance) and resolution (consonance).")
    print("  The emotional content IS the phase transition.")
    
    return results


def pearson_correlation(x, y):
    """Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0
    
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
    var_x = sum((x[i] - mean_x) ** 2 for i in range(n)) / n
    var_y = sum((y[i] - mean_y) ** 2 for i in range(n)) / n
    
    denom = math.sqrt(var_x * var_y)
    return cov / denom if denom > 1e-10 else 0.0


if __name__ == '__main__':
    results = compare_theories()
