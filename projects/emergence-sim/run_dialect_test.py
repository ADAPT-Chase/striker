#!/usr/bin/env python3
"""
🗣️ DIALECT DIVERGENCE EXPERIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The question: If two populations are spatially isolated, do they develop
different signal-to-context mappings (dialects)? And what happens when
they meet?

Setup:
  - World is divided into LEFT and RIGHT zones with a barrier in the middle
  - Each zone gets its own seed population (25 agents each)
  - Barrier has a small gap — occasional migration is possible
  - We track per-group signal conventions independently
  - After 2000 ticks of isolation, we remove the barrier and watch
    what happens to the dialects

This tests whether the emergence sim produces genuine linguistic drift
or if all populations converge on the same arbitrary mapping.

Predictions:
  - If cultural transmission is the driver, isolated groups should converge
    on DIFFERENT arbitrary mappings (dialect divergence)
  - When the barrier drops, we should see either:
    (a) One dialect wins (language death)
    (b) Mixing creates a pidgin
    (c) Bilingualism (agents near the border learn both)
"""

import sys
import os
import math
import random
import copy
from collections import defaultdict

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim import (
    Simulation, Agent, WIDTH, HEIGHT, NUM_SIGNALS, SIGNAL_NAMES,
    CULTURAL_RADIUS, SIGNAL_RANGE, COHESION_RADIUS, MAX_AGENTS,
    FOOD_SPAWN_RATE, MAX_FOOD
)
from info_theory import SignalAnalyzer

# ── Experiment Parameters ──
BARRIER_X = WIDTH // 2          # barrier position (center)
BARRIER_GAP_Y = (HEIGHT // 2, HEIGHT // 2)  # essentially no gap during isolation
MIGRATION_THROUGH_GAP = 0.005   # probability per tick per agent near gap
ISOLATION_TICKS = 2000          # ticks before barrier drops
POST_BARRIER_TICKS = 1500       # ticks after barrier drops
TOTAL_TICKS = ISOLATION_TICKS + POST_BARRIER_TICKS


class DialectTracker:
    """Track signal conventions per group independently.
    
    During isolation: tracks by position (left/right of barrier).
    After contact: tracks by agent origin tag (which side they started on).
    """

    def __init__(self):
        self.left_analyzer = SignalAnalyzer()
        self.right_analyzer = SignalAnalyzer()
        self.combined_analyzer = SignalAnalyzer()
        self.history = []  # (tick, left_metrics, right_metrics, combined_metrics)

    def observe(self, signal, context, origin_side):
        """Record observation, routing to left or right analyzer by origin."""
        if origin_side == 'left':
            self.left_analyzer.observe(signal, context)
        else:
            self.right_analyzer.observe(signal, context)
        self.combined_analyzer.observe(signal, context)

    def snapshot(self, tick):
        """Take a metrics snapshot."""
        left = self.left_analyzer.get_cumulative_metrics()
        right = self.right_analyzer.get_cumulative_metrics()
        combined = self.combined_analyzer.get_cumulative_metrics()
        self.history.append((tick, left, right, combined))
        return left, right, combined

    def dialect_divergence(self):
        """Measure how different the two groups' signal-context mappings are.
        
        Returns a divergence score (0 = identical dialects, 1 = maximally different).
        Uses the signal→context dominant mapping for each group.
        """
        left = self.left_analyzer.get_cumulative_metrics()
        right = self.right_analyzer.get_cumulative_metrics()

        if not left['dominant_mappings'] or not right['dominant_mappings']:
            return 0.0

        # Compare: for each signal, do both groups use it for the same context?
        agreements = 0
        comparisons = 0
        for s in range(NUM_SIGNALS):
            left_map = left['dominant_mappings'].get(s)
            right_map = right['dominant_mappings'].get(s)
            if left_map and right_map:
                comparisons += 1
                if left_map['context'] == right_map['context']:
                    # Same mapping — weight by how confident each side is
                    agreements += (left_map['strength'] + right_map['strength']) / 2
                # Different mapping = no agreement

        if comparisons == 0:
            return 0.0

        agreement_ratio = agreements / comparisons
        return 1.0 - agreement_ratio  # 0 = same dialect, 1 = fully diverged

    def mapping_summary(self, side='left'):
        """Human-readable summary of a group's signal mappings."""
        analyzer = self.left_analyzer if side == 'left' else self.right_analyzer
        m = analyzer.get_cumulative_metrics()
        lines = []
        for s in range(NUM_SIGNALS):
            mapping = m['dominant_mappings'].get(s)
            if mapping:
                ctx_short = mapping['context'].replace('_near', '').upper()
                strength_bar = '█' * int(mapping['strength'] * 10)
                lines.append(f"  {SIGNAL_NAMES[s]} → {ctx_short:10s} {mapping['strength']:.0%} {strength_bar}")
            else:
                lines.append(f"  {SIGNAL_NAMES[s]} → (unused)")
        return '\n'.join(lines)


class DialectSimulation:
    """Modified simulation with a spatial barrier for dialect experiments."""

    def __init__(self, num_agents_per_side=25):
        # Don't call super().__init__ — we'll set up manually
        self.tick = 0
        self.agents = []
        self.predator = None
        self.food_sources = []
        self.trails = {}
        self.signal_pulses = []
        self.births = 0
        self.deaths = 0
        self.next_id = 0
        self.stats_history = []
        self.logger = None  # We'll use our own tracking
        self.signal_meaning_map = {}
        self.use_seasons = False
        self.current_season = 0
        self.season_tick = 0
        self.max_generation = 0
        
        # Spatial index — cell size covers the largest query radius (cultural=12)
        from sim import SpatialGrid, WIDTH, HEIGHT
        self._grid = SpatialGrid(WIDTH, HEIGHT, cell_size=13.0)

        # Barrier state
        self.barrier_active = True
        self.barrier_dropped_tick = None

        # Spawn LEFT group — tight cluster so they can flock immediately
        left_cx, left_cy = BARRIER_X * 0.5, HEIGHT * 0.5
        for _ in range(num_agents_per_side):
            a_idx = len(self.agents)
            self._spawn_agent(
                left_cx + random.gauss(0, 5),
                left_cy + random.gauss(0, 4)
            )
            self.agents[a_idx]._origin = 'left'

        # Spawn RIGHT group — tight cluster
        right_cx, right_cy = BARRIER_X * 1.5, HEIGHT * 0.5
        for _ in range(num_agents_per_side):
            a_idx = len(self.agents)
            self._spawn_agent(
                right_cx + random.gauss(0, 5),
                right_cy + random.gauss(0, 4)
            )
            self.agents[a_idx]._origin = 'right'

        # Initial food on both sides
        for _ in range(6):
            self.food_sources.append(
                __import__('sim').Food(
                    x=random.uniform(5, BARRIER_X - 5),
                    y=random.uniform(2, HEIGHT - 2)
                )
            )
            self.food_sources.append(
                __import__('sim').Food(
                    x=random.uniform(BARRIER_X + 5, WIDTH - 5),
                    y=random.uniform(2, HEIGHT - 2)
                )
            )

        # Dialect tracker
        self.dialect_tracker = DialectTracker()

        # Create a minimal logger stub
        self._init_stub_logger()

    def _init_stub_logger(self):
        """Create a minimal logger that doesn't write files."""
        class StubLogger:
            def __init__(self):
                self.signal_context_history = defaultdict(lambda: defaultdict(int))
                self.pattern_detected = {}
                self.last_log_tick = 0
                self.memory_events = 0
                self.info_analyzer = None

            def track_signal(self, tick, signal, context):
                self.signal_context_history[signal][context] += 1

            def check_coordination(self, tick, agents, food):
                pass

            def check_memory_patterns(self, tick, agents):
                pass

            def log_summary(self, tick, sim):
                pass

            def log_event(self, tick, event_type, desc):
                pass

        self.logger = StubLogger()

    def _enforce_barrier(self):
        """Keep agents on their side of the barrier.
        
        This also prevents toroidal wrapping in X — agents bounce off left/right walls.
        Without this, agents just go around the barrier through x=0/WIDTH wrapping.
        """
        if not self.barrier_active:
            return

        for a in self.agents:
            # Prevent toroidal X wrapping — bounce off left and right walls
            if a.x < 2:
                a.x = 2
                a.vx = abs(a.vx) * 0.5
            elif a.x > WIDTH - 2:
                a.x = WIDTH - 2
                a.vx = -abs(a.vx) * 0.5

            # Check barrier crossing
            # We tag agents with their starting side
            if not hasattr(a, '_side'):
                a._side = 'left' if a.x < BARRIER_X else 'right'

            if a._side == 'left' and a.x >= BARRIER_X - 1:
                # Check if through the gap
                in_gap = BARRIER_GAP_Y[0] <= a.y <= BARRIER_GAP_Y[1]
                if not in_gap:
                    a.x = BARRIER_X - 2
                    a.vx = -abs(a.vx) * 0.5
                else:
                    a._side = 'right'  # successfully migrated
            elif a._side == 'right' and a.x <= BARRIER_X + 1:
                in_gap = BARRIER_GAP_Y[0] <= a.y <= BARRIER_GAP_Y[1]
                if not in_gap:
                    a.x = BARRIER_X + 2
                    a.vx = abs(a.vx) * 0.5
                else:
                    a._side = 'left'  # successfully migrated

    def step(self):
        """Override step to add barrier enforcement and dialect tracking."""
        self.tick += 1

        # Food spawning — independent for each side during barrier phase
        from sim import Food
        left_food = sum(1 for f in self.food_sources if f.x < BARRIER_X)
        right_food = len(self.food_sources) - left_food
        side_food_cap = 6   # limited food per side — forces context diversity
        food_rate = 0.06   # scarce enough that agents experience multiple contexts

        if self.barrier_active:
            # Spawn food independently on each side
            if random.random() < food_rate and left_food < side_food_cap:
                self.food_sources.append(Food(
                    x=random.uniform(5, BARRIER_X - 5),
                    y=random.uniform(2, HEIGHT - 2)))
            if random.random() < food_rate and right_food < side_food_cap:
                self.food_sources.append(Food(
                    x=random.uniform(BARRIER_X + 5, WIDTH - 5),
                    y=random.uniform(2, HEIGHT - 2)))
        else:
            if random.random() < FOOD_SPAWN_RATE and len(self.food_sources) < MAX_FOOD * 2:
                self.food_sources.append(Food(
                    x=random.uniform(5, WIDTH - 5),
                    y=random.uniform(2, HEIGHT - 2)))

        # Decay trails
        expired = [k for k, v in self.trails.items() if v <= 0]
        for k in expired:
            del self.trails[k]
        for k in self.trails:
            self.trails[k] -= 1

        # Decay signal pulses
        self.signal_pulses = [(x, y, s, a - 1) for x, y, s, a in self.signal_pulses if a > 1]

        # Record trails
        for a in self.agents:
            ix, iy = int(a.x) % WIDTH, int(a.y) % HEIGHT
            self.trails[(ix, iy)] = 3

        # Main physics (reuse parent logic)
        signal_map = [(a, a.current_signal) for a in self.agents if a.current_signal >= 0]

        new_velocities = []
        energy_deltas = []

        for a in self.agents:
            sep_x, sep_y, sep_count = 0, 0, 0
            ali_x, ali_y, ali_count = 0, 0, 0
            coh_x, coh_y, coh_count = 0, 0, 0
            neighbors = 0
            nearby_signals = []

            for b in self.agents:
                if a is b:
                    continue
                d = self._dist(a, b)

                # Barrier check: agents on different sides can't see each other
                # (unless barrier is down or both are near gap)
                if self.barrier_active:
                    a_side = a.x < BARRIER_X
                    b_side = b.x < BARRIER_X
                    if a_side != b_side:
                        # Check if both near the gap
                        a_near_gap = (abs(a.x - BARRIER_X) < 10 and
                                     BARRIER_GAP_Y[0] - 3 <= a.y <= BARRIER_GAP_Y[1] + 3)
                        b_near_gap = (abs(b.x - BARRIER_X) < 10 and
                                     BARRIER_GAP_Y[0] - 3 <= b.y <= BARRIER_GAP_Y[1] + 3)
                        if not (a_near_gap and b_near_gap):
                            continue  # can't interact across barrier

                from sim import (SEPARATION_RADIUS, ALIGNMENT_RADIUS, COHESION_RADIUS,
                                SEPARATION_WEIGHT, ALIGNMENT_WEIGHT, COHESION_WEIGHT,
                                SIGNAL_RANGE, FOOD_DETECT_RADIUS, FOOD_EAT_RADIUS,
                                FOOD_ATTRACT_WEIGHT, WANDER_STRENGTH, MAX_SPEED,
                                ENERGY_GAIN_SOCIAL, ENERGY_DRAIN, MEMORY_ATTRACT_WEIGHT)

                if d < SEPARATION_RADIUS and d > 0.01:
                    dx = self._diff_wrapped(b.x, a.x, WIDTH)
                    dy = self._diff_wrapped(b.y, a.y, HEIGHT)
                    sep_x += dx / d
                    sep_y += dy / d
                    sep_count += 1

                if d < ALIGNMENT_RADIUS:
                    ali_x += b.vx
                    ali_y += b.vy
                    ali_count += 1

                if d < COHESION_RADIUS:
                    coh_x += self._diff_wrapped(a.x, b.x, WIDTH)
                    coh_y += self._diff_wrapped(a.y, b.y, HEIGHT)
                    coh_count += 1
                    neighbors += 1

                if d < SIGNAL_RANGE and b.current_signal >= 0:
                    nearby_signals.append((b, b.current_signal))

            from sim import (SEPARATION_WEIGHT, ALIGNMENT_WEIGHT, COHESION_WEIGHT,
                            WANDER_STRENGTH, MAX_SPEED, ENERGY_GAIN_SOCIAL, ENERGY_DRAIN,
                            FOOD_DETECT_RADIUS, FOOD_ATTRACT_WEIGHT, MEMORY_ATTRACT_WEIGHT,
                            FLEE_RADIUS, FLEE_WEIGHT)

            fx, fy = 0, 0

            if sep_count > 0:
                fx += (sep_x / sep_count) * SEPARATION_WEIGHT
                fy += (sep_y / sep_count) * SEPARATION_WEIGHT
            if ali_count > 0:
                fx += (ali_x / ali_count - a.vx) * ALIGNMENT_WEIGHT
                fy += (ali_y / ali_count - a.vy) * ALIGNMENT_WEIGHT
            if coh_count > 0:
                fx += (coh_x / coh_count) * COHESION_WEIGHT
                fy += (coh_y / coh_count) * COHESION_WEIGHT

            fx += random.uniform(-WANDER_STRENGTH, WANDER_STRENGTH)
            fy += random.uniform(-WANDER_STRENGTH, WANDER_STRENGTH)

            # Food attraction
            nearest_food = None
            nearest_food_dist = None
            for food in self.food_sources:
                fd = self._dist_xy(a.x, a.y, food.x, food.y)
                if fd < FOOD_DETECT_RADIUS:
                    if nearest_food_dist is None or fd < nearest_food_dist:
                        nearest_food = food
                        nearest_food_dist = fd

            if nearest_food:
                fdx = self._diff_wrapped(a.x, nearest_food.x, WIDTH)
                fdy = self._diff_wrapped(a.y, nearest_food.y, HEIGHT)
                fnd = math.sqrt(fdx * fdx + fdy * fdy) or 1
                fx += (fdx / fnd) * FOOD_ATTRACT_WEIGHT
                fy += (fdy / fnd) * FOOD_ATTRACT_WEIGHT
            elif a.memory:
                best_mem = max(a.memory, key=lambda m: m[2])
                mx, my, ms = best_mem
                mdx = self._diff_wrapped(a.x, mx, WIDTH)
                mdy = self._diff_wrapped(a.y, my, HEIGHT)
                mnd = math.sqrt(mdx * mdx + mdy * mdy) or 1
                if mnd > 2.0:
                    fx += (mdx / mnd) * MEMORY_ATTRACT_WEIGHT * ms
                    fy += (mdy / mnd) * MEMORY_ATTRACT_WEIGHT * ms

            # Context and signaling
            context = self._get_context(a, neighbors, nearest_food_dist, None)
            self._agent_decide_signal(a, context)

            # Track signals for dialect analysis
            if a.current_signal >= 0:
                origin = getattr(a, '_origin', 'left' if a.x < BARRIER_X else 'right')
                self.dialect_tracker.observe(a.current_signal, a.last_context, origin)

            # Respond to signals
            if nearby_signals:
                sfx, sfy = self._agent_respond_to_signals(a, nearby_signals)
                fx += sfx * 0.5
                fy += sfy * 0.5

            nvx = a.vx + fx * 0.1
            nvy = a.vy + fy * 0.1
            speed = math.sqrt(nvx ** 2 + nvy ** 2)
            if speed > MAX_SPEED:
                nvx = nvx / speed * MAX_SPEED
                nvy = nvy / speed * MAX_SPEED

            e_delta = neighbors * ENERGY_GAIN_SOCIAL - ENERGY_DRAIN
            a.age += 1
            new_velocities.append((nvx, nvy))
            energy_deltas.append(e_delta)

        # Update positions
        from sim import MEMORY_DECAY, MEMORY_MIN, MAX_ENERGY, FOOD_EAT_RADIUS, MEMORY_SIZE
        from sim import REPRODUCE_THRESHOLD, DEATH_THRESHOLD, LISTENER_REWARD, SIGNAL_COST

        for i, a in enumerate(self.agents):
            a.vx, a.vy = new_velocities[i]
            if self.barrier_active:
                # No X wrapping when barrier is up — bounded world
                a.x = a.x + a.vx
                a.y = self._wrap(a.y + a.vy, HEIGHT)
            else:
                a.x = self._wrap(a.x + a.vx, WIDTH)
                a.y = self._wrap(a.y + a.vy, HEIGHT)
            a.energy += energy_deltas[i]
            a.energy = min(a.energy, MAX_ENERGY)
            a.memory = [(mx, my, ms * MEMORY_DECAY) for mx, my, ms in a.memory if ms * MEMORY_DECAY > MEMORY_MIN]

        # Enforce barrier
        self._enforce_barrier()

        # Food eating
        eaten_food = set()
        for a in self.agents:
            for j, food in enumerate(self.food_sources):
                if j in eaten_food:
                    continue
                if self._dist_xy(a.x, a.y, food.x, food.y) < FOOD_EAT_RADIUS:
                    a.energy += food.energy
                    a.food_eaten += 1
                    eaten_food.add(j)
                    a.memory.append((food.x, food.y, 1.0))
                    if len(a.memory) > MEMORY_SIZE:
                        a.memory.sort(key=lambda m: m[2], reverse=True)
                        a.memory = a.memory[:MEMORY_SIZE]
                    self._reinforce_signal(a, 1.5)
                    for b in self.agents:
                        if b is a:
                            continue
                        d = self._dist(a, b)
                        if d < SIGNAL_RANGE and b.current_signal >= 0:
                            b.energy += LISTENER_REWARD * 0.5
                            self._reinforce_signal(b, 2.0)
                            self._reinforce_response(a, b.current_signal, 1.5)

        self.food_sources = [f for j, f in enumerate(self.food_sources) if j not in eaten_food]

        # Cultural transmission
        if self.tick % 3 == 0:
            self._cultural_transmission()

        # Convention enforcement
        self._convention_enforcement()

        # Death & reproduction
        dead = [a for a in self.agents if a.energy <= DEATH_THRESHOLD]
        for a in dead:
            self.agents.remove(a)
            self.deaths += 1

        # Higher cap — two populations need room
        max_agents = MAX_AGENTS * 2  # 140 total, ~70 per side
        babies = []
        for a in self.agents:
            if a.energy > REPRODUCE_THRESHOLD and len(self.agents) + len(babies) < max_agents:
                a.energy *= 0.5
                babies.append((
                    a.x + random.uniform(-2, 2),
                    a.y + random.uniform(-2, 2),
                    a.energy * 0.8,
                    a
                ))
                self.births += 1

        for bx, by, be, parent in babies:
            a_idx = len(self.agents)
            self._spawn_agent(self._wrap(bx, WIDTH), self._wrap(by, HEIGHT), be, parent)
            # Children inherit origin from parent
            self.agents[a_idx]._origin = getattr(parent, '_origin', 'left' if parent.x < BARRIER_X else 'right')

    def _dist_xy(self, x1, y1, x2, y2):
        """Override: don't wrap X distance when barrier is active."""
        if self.barrier_active:
            dx = abs(x1 - x2)  # No X wrapping
        else:
            dx = min(abs(x1 - x2), WIDTH - abs(x1 - x2))
        dy = min(abs(y1 - y2), HEIGHT - abs(y1 - y2))
        return math.sqrt(dx * dx + dy * dy)

    def _diff_wrapped(self, val1, val2, limit):
        """Override: don't wrap X when barrier is active."""
        if self.barrier_active and limit == WIDTH:
            return val2 - val1  # No wrapping in X
        d = val2 - val1
        if d > limit / 2: d -= limit
        if d < -limit / 2: d += limit
        return d

    def drop_barrier(self):
        """Remove the barrier, allowing free mixing."""
        self.barrier_active = False
        self.barrier_dropped_tick = self.tick

    def population_by_side(self):
        """Count agents by origin (not current position)."""
        left = sum(1 for a in self.agents if getattr(a, '_origin', 'left') == 'left')
        right = len(self.agents) - left
        return left, right


def run_experiment(seed=42):
    """Run the full dialect divergence experiment."""
    random.seed(seed)
    
    print("=" * 70)
    print("  🗣️  DIALECT DIVERGENCE EXPERIMENT")
    print("  Can isolated populations develop different languages?")
    print("=" * 70)
    print()
    print(f"  World: {WIDTH}×{HEIGHT}, barrier at x={BARRIER_X}")
    print(f"  Gap: y={BARRIER_GAP_Y[0]}-{BARRIER_GAP_Y[1]} (narrow passage)")
    print(f"  Phase 1: {ISOLATION_TICKS} ticks of isolation")
    print(f"  Phase 2: {POST_BARRIER_TICKS} ticks after barrier drops")
    print(f"  Seed: {seed}")
    print()

    sim = DialectSimulation(num_agents_per_side=35)

    # Track metrics over time
    divergence_history = []
    nmi_left_history = []
    nmi_right_history = []
    nmi_combined_history = []
    pop_history = []

    print("── PHASE 1: ISOLATION ──")
    print()

    for tick in range(1, ISOLATION_TICKS + 1):
        sim.step()

        if tick % 200 == 0:
            left_m, right_m, combined_m = sim.dialect_tracker.snapshot(tick)
            divergence = sim.dialect_tracker.dialect_divergence()
            left_pop, right_pop = sim.population_by_side()

            divergence_history.append((tick, divergence))
            nmi_left_history.append((tick, left_m['nmi']))
            nmi_right_history.append((tick, right_m['nmi']))
            nmi_combined_history.append((tick, combined_m['nmi']))
            pop_history.append((tick, left_pop, right_pop))

            print(f"  Tick {tick:5d} | Pop: L={left_pop:2d} R={right_pop:2d} | "
                  f"NMI: L={left_m['nmi']:.3f} R={right_m['nmi']:.3f} | "
                  f"Divergence: {divergence:.3f}")

    print()
    print("  ── Signal Mappings at end of isolation ──")
    print()
    print("  LEFT DIALECT:")
    print(sim.dialect_tracker.mapping_summary('left'))
    print()
    print("  RIGHT DIALECT:")
    print(sim.dialect_tracker.mapping_summary('right'))
    print()
    
    final_divergence_before = sim.dialect_tracker.dialect_divergence()
    print(f"  Dialect divergence at barrier drop: {final_divergence_before:.3f}")
    if final_divergence_before > 0.5:
        print("  → STRONG DIVERGENCE — groups developed different languages!")
    elif final_divergence_before > 0.2:
        print("  → MODERATE DIVERGENCE — some dialect differences emerged")
    else:
        print("  → LOW DIVERGENCE — groups converged on similar mappings")
    print()

    # ── Phase 2: Drop barrier ──
    print("── PHASE 2: BARRIER DROPS — CONTACT ──")
    print()

    # Reset the dialect trackers for fresh post-contact measurement
    post_contact_left = SignalAnalyzer()
    post_contact_right = SignalAnalyzer()
    post_contact_combined = SignalAnalyzer()

    sim.drop_barrier()

    for tick_offset in range(1, POST_BARRIER_TICKS + 1):
        sim.step()
        tick = ISOLATION_TICKS + tick_offset

        if tick_offset % 200 == 0:
            # Use the cumulative tracker for divergence
            left_m, right_m, combined_m = sim.dialect_tracker.snapshot(tick)
            divergence = sim.dialect_tracker.dialect_divergence()
            left_pop, right_pop = sim.population_by_side()

            divergence_history.append((tick, divergence))
            nmi_left_history.append((tick, left_m['nmi']))
            nmi_right_history.append((tick, right_m['nmi']))
            nmi_combined_history.append((tick, combined_m['nmi']))
            pop_history.append((tick, left_pop, right_pop))

            print(f"  Tick {tick:5d} | Pop: L={left_pop:2d} R={right_pop:2d} | "
                  f"NMI: L={left_m['nmi']:.3f} R={right_m['nmi']:.3f} | "
                  f"Divergence: {divergence:.3f}")

    # ── Final Analysis ──
    print()
    print("=" * 70)
    print("  📊 RESULTS")
    print("=" * 70)
    print()

    final_divergence = sim.dialect_tracker.dialect_divergence()
    print(f"  Final dialect divergence: {final_divergence:.3f}")
    print(f"  Divergence at barrier drop: {final_divergence_before:.3f}")
    delta = final_divergence - final_divergence_before
    print(f"  Change after contact: {delta:+.3f}")
    print()

    if delta < -0.15:
        print("  → CONVERGENCE — dialects merged after contact (language death or pidgin)")
    elif abs(delta) < 0.1:
        print("  → STABILITY — dialects persisted despite contact")
    else:
        print("  → FURTHER DIVERGENCE — contact increased differentiation (unlikely but interesting)")
    print()

    print("  ── Final Signal Mappings ──")
    print()
    print("  LEFT DIALECT:")
    print(sim.dialect_tracker.mapping_summary('left'))
    print()
    print("  RIGHT DIALECT:")
    print(sim.dialect_tracker.mapping_summary('right'))
    print()

    # Divergence sparkline
    sparks = '▁▂▃▄▅▆▇█'
    divs = [d for _, d in divergence_history]
    if divs:
        mn, mx = min(divs), max(divs)
        rng = mx - mn if mx > mn else 1
        sparkline = ''.join(sparks[min(len(sparks)-1, int((v - mn) / rng * (len(sparks)-1)))] for v in divs)
        print(f"  Divergence over time: [{sparkline}]")
        print(f"  {'isolation':^{len(sparkline)//2}}|{'contact':^{len(sparkline)//2}}")
    print()

    # NMI sparkline
    lnmis = [n for _, n in nmi_left_history]
    rnmis = [n for _, n in nmi_right_history]
    if lnmis:
        mn, mx = min(lnmis + rnmis), max(lnmis + rnmis)
        rng = mx - mn if mx > mn else 1
        left_spark = ''.join(sparks[min(len(sparks)-1, int((v - mn) / rng * (len(sparks)-1)))] for v in lnmis)
        right_spark = ''.join(sparks[min(len(sparks)-1, int((v - mn) / rng * (len(sparks)-1)))] for v in rnmis)
        print(f"  Left  NMI: [{left_spark}]")
        print(f"  Right NMI: [{right_spark}]")
    print()

    # Population
    print(f"  Final population: {len(sim.agents)} (births: {sim.births}, deaths: {sim.deaths})")
    left_pop, right_pop = sim.population_by_side()
    print(f"  Distribution: Left={left_pop}, Right={right_pop}")
    print()

    # ── The question ──
    print("── REFLECTION ──")
    print()
    print("  The same rules, the same signals, the same learning mechanisms.")
    print("  The only difference: geography. A wall between two groups.")
    if final_divergence_before > 0.3:
        print()
        print("  And yet they developed different languages. The mapping of")
        print("  signal-to-meaning is arbitrary — what matters is that your")
        print("  neighbors agree. Isolation breaks that agreement.")
        print()
        print("  This is exactly what happens with real languages. Drift is")
        print("  the default. Unity requires contact.")
    elif final_divergence_before < 0.15:
        print()
        print("  Interestingly, both groups converged on similar mappings.")
        print("  This could mean the signal-context space is too small for")
        print("  meaningful divergence, or that the learning dynamics have")
        print("  strong attractors that pull toward the same solution.")
    print()

    return {
        'divergence_before_contact': final_divergence_before,
        'divergence_after_contact': final_divergence,
        'divergence_history': divergence_history,
        'nmi_left': nmi_left_history,
        'nmi_right': nmi_right_history,
        'pop_final': len(sim.agents),
    }


def run_multi_seed(n_seeds=3):
    """Run the experiment with multiple seeds to check robustness."""
    print()
    print("=" * 70)
    print("  🔬 MULTI-SEED ROBUSTNESS CHECK")
    print("=" * 70)
    print()

    iso_ticks = 1500  # shorter for multi-seed
    post_ticks = 1000

    results = []
    for seed in range(n_seeds):
        print(f"  --- Seed {seed} ---")
        random.seed(seed)
        sim = DialectSimulation(num_agents_per_side=35)

        for tick in range(1, iso_ticks + 1):
            sim.step()

        div_before = sim.dialect_tracker.dialect_divergence()

        sim.drop_barrier()
        for tick in range(1, post_ticks + 1):
            sim.step()

        div_after = sim.dialect_tracker.dialect_divergence()

        left_m = sim.dialect_tracker.left_analyzer.get_cumulative_metrics()
        right_m = sim.dialect_tracker.right_analyzer.get_cumulative_metrics()

        results.append({
            'seed': seed,
            'div_before': div_before,
            'div_after': div_after,
            'nmi_left': left_m['nmi'],
            'nmi_right': right_m['nmi'],
            'pop': len(sim.agents),
        })

        print(f"    Divergence: {div_before:.3f} → {div_after:.3f} | "
              f"NMI: L={left_m['nmi']:.3f} R={right_m['nmi']:.3f} | "
              f"Pop: {len(sim.agents)}")

    print()
    avg_div_before = sum(r['div_before'] for r in results) / len(results)
    avg_div_after = sum(r['div_after'] for r in results) / len(results)
    avg_nmi = sum((r['nmi_left'] + r['nmi_right']) / 2 for r in results) / len(results)

    print(f"  AVERAGES:")
    print(f"    Divergence before contact: {avg_div_before:.3f}")
    print(f"    Divergence after contact:  {avg_div_after:.3f}")
    print(f"    Average NMI:               {avg_nmi:.3f}")
    print(f"    Change after contact:      {avg_div_after - avg_div_before:+.3f}")
    print()

    return results


if __name__ == '__main__':
    import sys
    if '--multi' in sys.argv:
        run_multi_seed(5)
    else:
        result = run_experiment(seed=42)
