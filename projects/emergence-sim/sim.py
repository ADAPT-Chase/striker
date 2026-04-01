#!/usr/bin/env python3
"""
🌊 EMERGENCE SIMULATOR v4 — Cultural Transmission & Convention Pressure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agents follow flocking rules AND can emit signals (0-3) that nearby agents
detect and learn to respond to. Food sources spawn randomly; agents forage,
compete, and cooperate. Over time, agents spontaneously develop signal-based
coordinate — e.g., using signal 1 to mean "food here" or signal 2 for "danger".

v3 adds:
  • SEASONS — spring/summer/autumn/winter cycle affecting food spawn rates
  • SPATIAL MEMORY — agents remember food locations and revisit productive areas
  • PREDATOR CO-EVOLUTION — predators evolve signal-awareness and hunting tactics

Emergent events are logged to emergence-log.md.

Usage:
    python3 sim.py                # default simulation
    python3 sim.py --agents 60    # more agents
    python3 sim.py --speed 0.05   # faster updates
    python3 sim.py --predator     # add a predator
    python3 sim.py --seasons      # enable seasonal cycles
    python3 sim.py --predator --seasons  # full experience
"""

import math
import random
import time
import os
import sys
import argparse
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime
from spatial_grid import SpatialGrid

# ── Constants ──────────────────────────────────────────────────────────
WIDTH = 120
HEIGHT = 40
TRAIL_DECAY = 3

# Flocking parameters
SEPARATION_RADIUS = 3.0
ALIGNMENT_RADIUS = 8.0
COHESION_RADIUS = 10.0
SEPARATION_WEIGHT = 1.5
ALIGNMENT_WEIGHT = 1.0
COHESION_WEIGHT = 0.8
MAX_SPEED = 1.2
WANDER_STRENGTH = 0.3

# Life parameters
ENERGY_GAIN_SOCIAL = 0.01
ENERGY_DRAIN = 0.14
ENERGY_FROM_FOOD = 3.0
REPRODUCE_THRESHOLD = 12.0
DEATH_THRESHOLD = 0.0
INITIAL_ENERGY = 5.0
MAX_AGENTS = 70
MAX_ENERGY = 14.0              # energy cap per agent

# Food
FOOD_SPAWN_RATE = 0.08       # chance per tick to spawn food
MAX_FOOD = 12
FOOD_DETECT_RADIUS = 10.0    # agents can see food this far
FOOD_EAT_RADIUS = 1.5
FOOD_ATTRACT_WEIGHT = 1.2

# Seasons
SEASON_LENGTH = 120            # ticks per season
SEASONS = ['🌸 Spring', '☀️ Summer', '🍂 Autumn', '❄️ Winter']
SEASON_FOOD_RATES = [0.22, 0.12, 0.04, 0.008]    # food spawn rate per season
SEASON_FOOD_CAPS  = [18, 12, 6, 3]                # max food per season
SEASON_DRAIN_MULT = [0.5, 1.0, 2.0, 4.0]          # energy drain multiplier — winter is brutal

# Memory
MEMORY_SIZE = 8                # max remembered locations per agent
MEMORY_ATTRACT_WEIGHT = 0.6    # how strongly agents are drawn to remembered food spots
MEMORY_DECAY = 0.995           # memory strength decays each tick (slower decay)
MEMORY_MIN = 0.05              # forget below this threshold

# Signals
SIGNAL_RANGE = 10.0          # how far signals propagate
NUM_SIGNALS = 4              # signals 0-3
SIGNAL_NAMES = ['◆', '▲', '●', '■']
SIGNAL_COLORS = ['\033[93m', '\033[92m', '\033[96m', '\033[95m']  # yellow, green, cyan, magenta
SIGNAL_MEANINGS = ['unknown', 'unknown', 'unknown', 'unknown']
SIGNAL_COST = 0.03           # energy cost to emit a signal (makes noise expensive)
LISTENER_REWARD = 0.4        # energy bonus for acting on a correct signal

# Cultural transmission
CULTURAL_RADIUS = 12.0       # how far agents look for role models
CULTURAL_RATE = 0.15         # probability per tick of copying a neighbor
CULTURAL_BLEND = 0.45        # how much of the role model's weights to adopt (0=none, 1=full copy)
CULTURAL_ENERGY_BIAS = 2.0   # how much energy advantage matters in choosing role models

# Convention enforcement
CONVENTION_BONUS = 0.03      # energy bonus when nearby agent uses same signal in same context
CONVENTION_PENALTY = 0.01    # energy penalty when nearby agent uses different signal in same context

# Predator
PREDATOR_SPEED = 1.15
PREDATOR_HUNT_RADIUS = 18.0
PREDATOR_SIGNAL_LEARN_RATE = 0.03
FLEE_RADIUS = 14.0
FLEE_WEIGHT = 3.5
DANGER_SIGNAL_RADIUS = 15.0

# Agent glyphs
DIRECTION_GLYPHS = {
    'N': '↑', 'NE': '↗', 'E': '→', 'SE': '↘',
    'S': '↓', 'SW': '↙', 'W': '←', 'NW': '↖'
}

ENERGY_COLORS = [
    (2.0, '\033[31m'),   # red = dying
    (5.0, '\033[33m'),   # yellow = okay
    (8.0, '\033[32m'),   # green = healthy
    (999, '\033[36m'),   # cyan = thriving
]

PREDATOR_GLYPH = '\033[91m⬤\033[0m'
TRAIL_CHARS = ['·', '∘', ' ']
FOOD_GLYPH = '\033[93m✦\033[0m'

# ── Log path ──────────────────────────────────────────────────────────
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'emergence-log.md')


# ── Data ──────────────────────────────────────────────────────────────

@dataclass
class Food:
    x: float
    y: float
    energy: float = ENERGY_FROM_FOOD


@dataclass
class Agent:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    energy: float = INITIAL_ENERGY
    age: int = 0
    id: int = 0
    # Signal system
    current_signal: int = -1       # -1 = no signal, 0-3 = signal type
    signal_cooldown: int = 0
    # Learned signal-action weights: signal -> context -> weight
    # Context: 'food_near', 'danger_near', 'friends_near', 'alone'
    signal_weights: dict = field(default_factory=dict)
    # What this agent does when it hears each signal
    response_weights: dict = field(default_factory=dict)
    # Tracking
    food_eaten: int = 0
    signals_sent: int = 0
    last_context: str = ''
    # Memory: list of (x, y, strength) tuples — remembered food locations
    memory: list = field(default_factory=list)
    generation: int = 0

    def __post_init__(self):
        if not self.signal_weights:
            # Probability of emitting signal s in context c (small random init)
            self.signal_weights = {}
            for s in range(NUM_SIGNALS):
                self.signal_weights[s] = {
                    'food_near': random.uniform(0, 0.5),
                    'danger_near': random.uniform(0, 0.5),
                    'friends_near': random.uniform(0, 0.2),
                    'alone': random.uniform(0, 0.1),
                }
        if not self.response_weights:
            # How much to move toward signal source (positive = approach, negative = flee)
            self.response_weights = {}
            for s in range(NUM_SIGNALS):
                self.response_weights[s] = random.uniform(-0.3, 0.5)

    def heading(self):
        angle = math.atan2(-self.vy, self.vx)
        deg = math.degrees(angle) % 360
        dirs = ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']
        idx = int((deg + 22.5) / 45) % 8
        return dirs[idx]

    def glyph(self):
        return DIRECTION_GLYPHS[self.heading()]

    def colored_glyph(self):
        g = self.glyph()
        for threshold, color in ENERGY_COLORS:
            if self.energy < threshold:
                return f"{color}{g}\033[0m"
        return g

    def signal_glyph(self):
        if self.current_signal >= 0:
            s = self.current_signal
            return f"{SIGNAL_COLORS[s]}{SIGNAL_NAMES[s]}\033[0m"
        return None


@dataclass
class Predator:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    # Co-evolution: predator learns which signals indicate prey clusters
    signal_attraction: dict = field(default_factory=dict)  # signal -> weight
    hunt_style: str = 'chase'     # 'chase', 'ambush', 'intercept'
    kills: int = 0
    ticks_since_kill: int = 0
    stamina: float = 1.0          # decreases during chase, recharges during ambush

    def __post_init__(self):
        if not self.signal_attraction:
            self.signal_attraction = {s: random.uniform(-0.1, 0.3) for s in range(NUM_SIGNALS)}


class EmergenceLogger:
    """Tracks and logs emergent events to markdown file."""

    def __init__(self, path=LOG_PATH):
        self.path = path
        self.events = []
        self.signal_context_history = defaultdict(lambda: defaultdict(int))
        self.pattern_detected = {}
        self.last_log_tick = 0
        self.season_transitions = 0
        self.predator_style_changes = 0
        self.memory_events = 0
        # Information-theoretic analyzer (if available)
        try:
            from info_theory import SignalAnalyzer
            self.info_analyzer = SignalAnalyzer()
        except ImportError:
            self.info_analyzer = None
        # Initialize log file
        with open(self.path, 'w') as f:
            f.write("# 🌊 Emergence Simulator v3 — Event Log\n\n")
            f.write("## Features: Seasons, Memory, Predator Co-Evolution\n\n")
            f.write(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

    def log_event(self, tick, event_type, description):
        self.events.append((tick, event_type, description))
        with open(self.path, 'a') as f:
            f.write(f"### Tick {tick} — {event_type}\n")
            f.write(f"{description}\n\n")

    def track_signal(self, tick, signal, context):
        """Track signal-context associations to detect emergent meaning."""
        self.signal_context_history[signal][context] += 1
        if self.info_analyzer:
            self.info_analyzer.observe(signal, context)
        total = sum(self.signal_context_history[signal].values())
        if total < 15:
            return

        # Check if a signal has become strongly associated with a context
        for ctx, count in self.signal_context_history[signal].items():
            ratio = count / total
            key = f"signal_{signal}_{ctx}"
            if ratio > 0.55 and total > 20 and key not in self.pattern_detected:
                self.pattern_detected[key] = True
                meaning = {
                    'food_near': 'FOOD HERE',
                    'danger_near': 'DANGER',
                    'friends_near': 'GATHER',
                    'alone': 'LONELY/LOST'
                }.get(ctx, ctx)
                self.log_event(tick, "🧠 EMERGENT MEANING",
                    f"Signal **{SIGNAL_NAMES[signal]}** (#{signal}) has become associated with "
                    f"**{meaning}** — emitted in '{ctx}' context {ratio:.0%} of the time "
                    f"({count}/{total} uses). Agents are developing a shared vocabulary!")
                return meaning
        return None

    def check_coordination(self, tick, agents, food_list):
        """Check for coordinated behavior patterns."""
        if tick - self.last_log_tick < 50:
            return
        self.last_log_tick = tick

        # Check: do agents cluster around food when they hear certain signals?
        signaling_agents = [a for a in agents if a.current_signal >= 0]
        if len(signaling_agents) > 3:
            # Count agents moving toward signalers
            for sig_agent in signaling_agents[:3]:
                followers = 0
                for a in agents:
                    if a is sig_agent:
                        continue
                    dx = a.x - sig_agent.x
                    dy = a.y - sig_agent.y
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist < SIGNAL_RANGE:
                        # Is agent moving toward signaler?
                        dot = (sig_agent.x - a.x) * a.vx + (sig_agent.y - a.y) * a.vy
                        if dot > 0:
                            followers += 1
                if followers > 4:
                    self.log_event(tick, "📡 SIGNAL FOLLOWING",
                        f"Agent #{sig_agent.id} emitting signal {SIGNAL_NAMES[sig_agent.current_signal]} "
                        f"has **{followers} agents** moving toward it. Communication is working!")
                    break

    def check_memory_patterns(self, tick, agents):
        """Check if agents develop spatial memory strategies."""
        if tick - self.last_log_tick < 30:
            return
        memory_agents = [a for a in agents if len(a.memory) > 3]
        if len(memory_agents) > len(agents) * 0.4 and self.memory_events < 3:
            self.memory_events += 1
            avg_mem = sum(len(a.memory) for a in agents) / max(len(agents), 1)
            self.log_event(tick, "🧭 SPATIAL MEMORY",
                f"**{len(memory_agents)}/{len(agents)}** agents have built spatial memory maps "
                f"(avg {avg_mem:.1f} remembered locations). Agents are developing foraging routes!")

    def log_summary(self, tick, sim):
        """Periodic summary."""
        if tick % 200 != 0 or tick == 0:
            return
        pop = len(sim.agents)
        avg_e = sum(a.energy for a in sim.agents) / max(pop, 1)
        food_count = len(sim.food_sources)
        clusters = sim._count_clusters()
        season_name = SEASONS[sim.current_season] if hasattr(sim, 'current_season') else 'N/A'
        avg_gen = sum(a.generation for a in sim.agents) / max(pop, 1) if sim.agents else 0

        # Signal usage stats
        signal_counts = defaultdict(int)
        for a in sim.agents:
            if a.current_signal >= 0:
                signal_counts[a.current_signal] += 1

        sig_str = ", ".join(f"{SIGNAL_NAMES[s]}={c}" for s, c in sorted(signal_counts.items()))
        if not sig_str:
            sig_str = "none active"

        # Memory stats
        avg_mem = sum(len(a.memory) for a in sim.agents) / max(pop, 1) if sim.agents else 0

        # Most common signal-context associations
        assoc_str = ""
        for sig in range(NUM_SIGNALS):
            total = sum(self.signal_context_history[sig].values())
            if total > 5:
                top_ctx = max(self.signal_context_history[sig], key=self.signal_context_history[sig].get)
                ratio = self.signal_context_history[sig][top_ctx] / total
                assoc_str += f"\n  - Signal {SIGNAL_NAMES[sig]}: mostly '{top_ctx}' ({ratio:.0%})"

        # Info-theoretic metrics
        nmi_str = ""
        if self.info_analyzer:
            m = self.info_analyzer.get_cumulative_metrics()
            if m['total_obs'] > 20:
                nmi_str = f"\nNMI: {m['nmi']:.3f} | I(S;C): {m['mutual_info']:.3f} bits | Channel: {m['channel_utilization']:.1%}"

        self.log_event(tick, "📊 STATUS REPORT",
            f"Pop: **{pop}** | Avg Energy: **{avg_e:.1f}** | Food: **{food_count}** | "
            f"Flocks: **{clusters}** | Births: {sim.births} | Deaths: {sim.deaths}\n"
            f"Season: {season_name} | Avg Gen: {avg_gen:.1f} | Avg Memory: {avg_mem:.1f}\n"
            f"Active signals: {sig_str}"
            f"{assoc_str if assoc_str else ''}"
            f"{nmi_str}")


class Simulation:
    def __init__(self, num_agents=50, use_predator=False, use_seasons=False):
        self.tick = 0
        self.agents: list[Agent] = []
        self.predator: Predator | None = None
        self.food_sources: list[Food] = []
        self.trails: dict[tuple[int, int], int] = {}
        self.signal_pulses: list[tuple[float, float, int, int]] = []  # x, y, signal, age
        self.births = 0
        self.deaths = 0
        self.next_id = 0
        self.stats_history: list[dict] = []
        self.logger = EmergenceLogger()
        self.signal_meaning_map = {}  # signal -> detected meaning
        self.use_seasons = use_seasons
        # Spatial index — cell size covers the largest query radius (cultural=12)
        self._grid = SpatialGrid(WIDTH, HEIGHT, cell_size=13.0)
        self.current_season = 0       # 0=spring, 1=summer, 2=autumn, 3=winter
        self.season_tick = 0
        self.max_generation = 0

        for _ in range(num_agents):
            self._spawn_agent(
                random.uniform(10, WIDTH - 10),
                random.uniform(5, HEIGHT - 5)
            )

        # Initial food
        for _ in range(8):
            self._spawn_food()

        if use_predator:
            self.predator = Predator(
                x=random.uniform(0, WIDTH),
                y=random.uniform(0, HEIGHT)
            )

        self.logger.log_event(0, "🚀 SIMULATION START",
            f"**{num_agents}** agents initialized with random signal weights. "
            f"{'Predator active (co-evolving).' if use_predator else 'No predator.'} "
            f"{'Seasons enabled.' if use_seasons else 'No seasons.'} "
            f"Memory system active. "
            f"Watching for emergent communication patterns...")

    def _spawn_agent(self, x, y, energy=INITIAL_ENERGY, parent=None):
        a = Agent(
            x=x, y=y,
            vx=random.uniform(-0.5, 0.5),
            vy=random.uniform(-0.5, 0.5),
            energy=energy,
            id=self.next_id
        )
        if parent:
            # Inherit signal weights with mutation
            a.signal_weights = {}
            for s in range(NUM_SIGNALS):
                a.signal_weights[s] = {}
                for ctx in parent.signal_weights[s]:
                    val = parent.signal_weights[s][ctx] + random.gauss(0, 0.12)
                    a.signal_weights[s][ctx] = max(0, min(1, val))
            a.response_weights = {}
            for s in range(NUM_SIGNALS):
                val = parent.response_weights[s] + random.gauss(0, 0.12)
                a.response_weights[s] = max(-1, min(1, val))
            # Inherit some memory from parent (cultural transmission)
            a.memory = [(mx, my, ms * 0.5) for mx, my, ms in parent.memory[:4]]
            a.generation = parent.generation + 1
            self.max_generation = max(self.max_generation, a.generation)
        self.next_id += 1
        self.agents.append(a)

    def _spawn_food(self):
        # Sometimes spawn food in clusters
        if self.food_sources and random.random() < 0.4:
            # Spawn near existing food
            base = random.choice(self.food_sources)
            x = (base.x + random.gauss(0, 5)) % WIDTH
            y = (base.y + random.gauss(0, 3)) % HEIGHT
        else:
            x = random.uniform(0, WIDTH)
            y = random.uniform(0, HEIGHT)
        self.food_sources.append(Food(x=x, y=y))

    def _wrap(self, val, limit):
        return val % limit

    def _dist_xy(self, x1, y1, x2, y2):
        dx = min(abs(x1 - x2), WIDTH - abs(x1 - x2))
        dy = min(abs(y1 - y2), HEIGHT - abs(y1 - y2))
        return math.sqrt(dx * dx + dy * dy)

    def _dist(self, a, b):
        return self._dist_xy(a.x, a.y, b.x, b.y)

    def _diff_wrapped(self, val1, val2, limit):
        d = val2 - val1
        if d > limit / 2: d -= limit
        if d < -limit / 2: d += limit
        return d

    def _get_context(self, agent, neighbors, nearest_food_dist, predator_dist):
        """Determine the agent's current context."""
        if predator_dist is not None and predator_dist < FLEE_RADIUS:
            return 'danger_near'
        if agent.energy < 2.0:
            return 'danger_near'   # low energy = personal danger
        if nearest_food_dist is not None and nearest_food_dist < FOOD_DETECT_RADIUS:
            return 'food_near'
        if neighbors > 3:
            return 'friends_near'
        if neighbors == 0:
            return 'alone'
        return 'friends_near'

    def _agent_decide_signal(self, agent, context):
        """Agent decides whether to emit a signal based on learned weights."""
        if agent.signal_cooldown > 0:
            agent.signal_cooldown -= 1
            return

        # Calculate emission probability for each signal in this context
        probs = []
        for s in range(NUM_SIGNALS):
            probs.append(agent.signal_weights[s].get(context, 0))

        total = sum(probs)
        if total < 0.3:  # threshold to signal at all
            agent.current_signal = -1
            return

        # Normalize and pick
        r = random.uniform(0, total)
        cumulative = 0
        for s in range(NUM_SIGNALS):
            cumulative += probs[s]
            if r <= cumulative:
                agent.current_signal = s
                agent.signal_cooldown = random.randint(3, 8)
                agent.signals_sent += 1
                agent.last_context = context
                agent.energy -= SIGNAL_COST  # signaling costs energy — noise is expensive
                self.logger.track_signal(self.tick, s, context)
                # Add visual pulse
                self.signal_pulses.append((agent.x, agent.y, s, 3))
                return
        agent.current_signal = -1

    def _agent_respond_to_signals(self, agent, nearby_signals):
        """Agent responds to nearby signals based on learned response weights.
        Returns (fx, fy) force vector."""
        fx, fy = 0, 0
        for other, signal in nearby_signals:
            d = self._dist(agent, other)
            if d < 0.5:
                continue
            weight = agent.response_weights.get(signal, 0)
            dx = self._diff_wrapped(agent.x, other.x, WIDTH)
            dy = self._diff_wrapped(agent.y, other.y, HEIGHT)
            nd = math.sqrt(dx*dx + dy*dy) or 1
            fx += (dx / nd) * weight
            fy += (dy / nd) * weight
        return fx, fy

    def _reinforce_signal(self, agent, reward):
        """Reinforce the agent's signal weights based on outcome.
        
        Stronger learning: correct signals get amplified, incorrect ones
        get suppressed. Also applies cross-signal suppression — if signal S
        was correct in context C, reduce other signals' weights for C.
        """
        if agent.current_signal < 0 or not agent.last_context:
            return
        s = agent.current_signal
        ctx = agent.last_context
        lr = 0.06 * reward  # 3x stronger than before
        old = agent.signal_weights[s].get(ctx, 0)
        agent.signal_weights[s][ctx] = max(0, min(1, old + lr))
        
        # Cross-signal suppression: if this signal was rewarded, 
        # slightly reduce OTHER signals for this context
        if reward > 0:
            for other_s in range(NUM_SIGNALS):
                if other_s != s:
                    old_other = agent.signal_weights[other_s].get(ctx, 0)
                    agent.signal_weights[other_s][ctx] = max(0, old_other - lr * 0.3)

    def _reinforce_response(self, agent, signal, reward):
        """Reinforce response to a signal based on outcome."""
        lr = 0.04 * reward  # ~2.5x stronger
        old = agent.response_weights.get(signal, 0)
        agent.response_weights[signal] = max(-1, min(1, old + lr))

    def step(self):
        self.tick += 1

        # Season update
        if self.use_seasons:
            self.season_tick += 1
            if self.season_tick >= SEASON_LENGTH:
                self.season_tick = 0
                old_season = self.current_season
                self.current_season = (self.current_season + 1) % 4
                self.logger.log_event(self.tick, "🌍 SEASON CHANGE",
                    f"Season shifted from **{SEASONS[old_season]}** to **{SEASONS[self.current_season]}**. "
                    f"Food rate: {SEASON_FOOD_RATES[self.current_season]:.2f}, "
                    f"Energy drain: ×{SEASON_DRAIN_MULT[self.current_season]:.1f}")

        # Spawn food (season-adjusted)
        food_rate = SEASON_FOOD_RATES[self.current_season] if self.use_seasons else FOOD_SPAWN_RATE
        food_cap = SEASON_FOOD_CAPS[self.current_season] if self.use_seasons else MAX_FOOD
        if random.random() < food_rate and len(self.food_sources) < food_cap:
            self._spawn_food()

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
            self.trails[(ix, iy)] = TRAIL_DECAY

        # Pre-compute nearby signals for each agent
        signal_map = [(a, a.current_signal) for a in self.agents if a.current_signal >= 0]

        # Rebuild spatial index for this tick
        self._grid.rebuild(self.agents)

        # Calculate forces for each agent
        new_velocities = []
        energy_deltas = []

        # Max radius needed: max(COHESION_RADIUS, SIGNAL_RANGE)
        _max_radius = max(COHESION_RADIUS, SIGNAL_RANGE)

        for a in self.agents:
            sep_x, sep_y, sep_count = 0, 0, 0
            ali_x, ali_y, ali_count = 0, 0, 0
            coh_x, coh_y, coh_count = 0, 0, 0
            neighbors = 0
            nearby_signals = []

            # Use spatial grid instead of O(n) scan of all agents
            for b, d in self._grid.query_radius(a.x, a.y, _max_radius):
                if b is a:
                    continue

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

                # Collect signals from nearby agents
                if d < SIGNAL_RANGE and b.current_signal >= 0:
                    nearby_signals.append((b, b.current_signal))

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

            # Wander
            fx += random.uniform(-WANDER_STRENGTH, WANDER_STRENGTH)
            fy += random.uniform(-WANDER_STRENGTH, WANDER_STRENGTH)

            # Find nearest food
            nearest_food = None
            nearest_food_dist = None
            for food in self.food_sources:
                fd = self._dist_xy(a.x, a.y, food.x, food.y)
                if fd < FOOD_DETECT_RADIUS:
                    if nearest_food_dist is None or fd < nearest_food_dist:
                        nearest_food = food
                        nearest_food_dist = fd

            # Move toward food
            if nearest_food:
                fdx = self._diff_wrapped(a.x, nearest_food.x, WIDTH)
                fdy = self._diff_wrapped(a.y, nearest_food.y, HEIGHT)
                fnd = math.sqrt(fdx*fdx + fdy*fdy) or 1
                fx += (fdx / fnd) * FOOD_ATTRACT_WEIGHT
                fy += (fdy / fnd) * FOOD_ATTRACT_WEIGHT
            elif a.memory:
                # No food visible — use MEMORY to navigate toward remembered spots
                best_mem = max(a.memory, key=lambda m: m[2])
                mx, my, ms = best_mem
                mdx = self._diff_wrapped(a.x, mx, WIDTH)
                mdy = self._diff_wrapped(a.y, my, HEIGHT)
                mnd = math.sqrt(mdx*mdx + mdy*mdy) or 1
                if mnd > 2.0:  # don't circle at the spot
                    fx += (mdx / mnd) * MEMORY_ATTRACT_WEIGHT * ms
                    fy += (mdy / mnd) * MEMORY_ATTRACT_WEIGHT * ms

            # Predator distance
            predator_dist = None
            if self.predator:
                predator_dist = self._dist(a, self.predator)
                if predator_dist < FLEE_RADIUS and predator_dist > 0.01:
                    flee_dx = self._diff_wrapped(self.predator.x, a.x, WIDTH)
                    flee_dy = self._diff_wrapped(self.predator.y, a.y, HEIGHT)
                    fx += (flee_dx / predator_dist) * FLEE_WEIGHT
                    fy += (flee_dy / predator_dist) * FLEE_WEIGHT

            # Determine context and decide signal
            context = self._get_context(a, neighbors, nearest_food_dist, predator_dist)
            self._agent_decide_signal(a, context)

            # Respond to nearby signals
            if nearby_signals:
                sfx, sfy = self._agent_respond_to_signals(a, nearby_signals)
                fx += sfx * 0.5
                fy += sfy * 0.5

            # Apply forces
            nvx = a.vx + fx * 0.1
            nvy = a.vy + fy * 0.1
            speed = math.sqrt(nvx ** 2 + nvy ** 2)
            if speed > MAX_SPEED:
                nvx = nvx / speed * MAX_SPEED
                nvy = nvy / speed * MAX_SPEED

            # Energy
            drain_mult = SEASON_DRAIN_MULT[self.current_season] if self.use_seasons else 1.0
            e_delta = neighbors * ENERGY_GAIN_SOCIAL - ENERGY_DRAIN * drain_mult
            a.age += 1

            new_velocities.append((nvx, nvy))
            energy_deltas.append(e_delta)

        # Update positions
        for i, a in enumerate(self.agents):
            a.vx, a.vy = new_velocities[i]
            a.x = self._wrap(a.x + a.vx, WIDTH)
            a.y = self._wrap(a.y + a.vy, HEIGHT)
            a.energy += energy_deltas[i]
            a.energy = min(a.energy, MAX_ENERGY)
            # Decay memories
            a.memory = [(mx, my, ms * MEMORY_DECAY) for mx, my, ms in a.memory if ms * MEMORY_DECAY > MEMORY_MIN]

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
                    # MEMORY: remember this food location
                    a.memory.append((food.x, food.y, 1.0))
                    if len(a.memory) > MEMORY_SIZE:
                        # Keep strongest memories
                        a.memory.sort(key=lambda m: m[2], reverse=True)
                        a.memory = a.memory[:MEMORY_SIZE]
                    # Reward: if agent was signaling about food, reinforce that signal
                    self._reinforce_signal(a, 1.5)
                    # Key mechanism: reward nearby signalers who were broadcasting when
                    # this agent found food. This creates SENDER fitness pressure —
                    # agents whose food signals lead others to food get rewarded.
                    for b, d in self._grid.query_radius(a.x, a.y, SIGNAL_RANGE):
                        if b is a:
                            continue
                        if b.current_signal >= 0:
                            # The sender gets rewarded if their signal helped
                            b.energy += LISTENER_REWARD * 0.5  # sender gets half
                            self._reinforce_signal(b, 2.0)     # strong reinforcement
                            # The eating agent learns to respond to that signal
                            self._reinforce_response(a, b.current_signal, 1.5)

        self.food_sources = [f for j, f in enumerate(self.food_sources) if j not in eaten_food]

        # Cultural transmission — agents copy successful neighbors' signal strategies
        if self.tick % 3 == 0:  # every 3 ticks to save compute
            self._cultural_transmission()

        # Convention enforcement — social pressure toward shared signal meanings
        self._convention_enforcement()

        # Predator
        if self.predator:
            p = self.predator
            p.ticks_since_kill += 1

            # Co-evolution: adapt hunting style based on success
            if p.ticks_since_kill > 80 and p.hunt_style == 'chase':
                p.hunt_style = 'ambush'
                p.stamina = 1.0
                self.logger.log_event(self.tick, "🐺 PREDATOR ADAPTS",
                    f"Predator switched to **AMBUSH** strategy after {p.ticks_since_kill} ticks without a kill. "
                    f"It will wait near signal activity instead of chasing.")
            elif p.ticks_since_kill > 120 and p.hunt_style == 'ambush':
                p.hunt_style = 'intercept'
                self.logger.log_event(self.tick, "🐺 PREDATOR ADAPTS",
                    f"Predator switched to **INTERCEPT** strategy — it will try to cut off fleeing agents.")
            elif p.kills > 0 and p.ticks_since_kill < 20:
                if p.hunt_style != 'chase':
                    p.hunt_style = 'chase'
                    self.logger.log_event(self.tick, "🐺 PREDATOR ADAPTS",
                        f"Predator reverted to **CHASE** strategy after recent kill success.")

            # Learn from signals: if agents signal near predator, learn that signal = prey nearby
            for a in self.agents:
                if a.current_signal >= 0:
                    d = self._dist(a, p)
                    if d < PREDATOR_HUNT_RADIUS * 1.5:
                        sig = a.current_signal
                        p.signal_attraction[sig] += PREDATOR_SIGNAL_LEARN_RATE
                        p.signal_attraction[sig] = min(1.0, p.signal_attraction[sig])

            if self.agents:
                # Hunting behavior depends on style
                if p.hunt_style == 'chase':
                    # Classic: chase nearest agent
                    target = min(self.agents, key=lambda a: self._dist(a, p))
                    d = self._dist(target, p)
                    if d > 0.5:
                        dx = self._diff_wrapped(p.x, target.x, WIDTH)
                        dy = self._diff_wrapped(p.y, target.y, HEIGHT)
                        nd = math.sqrt(dx*dx + dy*dy) or 1
                        speed = PREDATOR_SPEED * p.stamina
                        p.vx = dx / nd * speed
                        p.vy = dy / nd * speed
                    p.stamina = max(0.4, p.stamina - 0.002)

                elif p.hunt_style == 'ambush':
                    # Move toward signal activity (evolved signal tracking)
                    best_sig_target = None
                    best_sig_score = -1
                    for a in self.agents:
                        if a.current_signal >= 0:
                            score = p.signal_attraction.get(a.current_signal, 0) / max(self._dist(a, p), 1)
                            if score > best_sig_score:
                                best_sig_score = score
                                best_sig_target = a
                    if best_sig_target and best_sig_score > 0.01:
                        dx = self._diff_wrapped(p.x, best_sig_target.x, WIDTH)
                        dy = self._diff_wrapped(p.y, best_sig_target.y, HEIGHT)
                        nd = math.sqrt(dx*dx + dy*dy) or 1
                        # Slow approach
                        p.vx = dx / nd * PREDATOR_SPEED * 0.5
                        p.vy = dy / nd * PREDATOR_SPEED * 0.5
                    else:
                        # Wander slowly
                        p.vx += random.uniform(-0.1, 0.1)
                        p.vy += random.uniform(-0.1, 0.1)
                    p.stamina = min(1.0, p.stamina + 0.01)  # recharge

                elif p.hunt_style == 'intercept':
                    # Predict where fleeing agents will go
                    nearest = min(self.agents, key=lambda a: self._dist(a, p))
                    d = self._dist(nearest, p)
                    # Aim ahead of the target
                    predict_x = nearest.x + nearest.vx * 5
                    predict_y = nearest.y + nearest.vy * 5
                    dx = self._diff_wrapped(p.x, predict_x, WIDTH)
                    dy = self._diff_wrapped(p.y, predict_y, HEIGHT)
                    nd = math.sqrt(dx*dx + dy*dy) or 1
                    p.vx = dx / nd * PREDATOR_SPEED * 1.1
                    p.vy = dy / nd * PREDATOR_SPEED * 1.1
                    p.stamina = max(0.3, p.stamina - 0.003)

                p.x = self._wrap(p.x + p.vx, WIDTH)
                p.y = self._wrap(p.y + p.vy, HEIGHT)

                caught = [a for a in self.agents if self._dist(a, p) < 1.5]
                for a in caught:
                    self.agents.remove(a)
                    self.deaths += 1
                    p.kills += 1
                    p.ticks_since_kill = 0
                    p.stamina = min(1.0, p.stamina + 0.3)
                    # Agents near the kill learn danger signals — STRONGLY
                    # This is the key selective pressure for danger communication
                    for b in self.agents:
                        d_to_kill = self._dist_xy(a.x, a.y, b.x, b.y)
                        if d_to_kill < DANGER_SIGNAL_RADIUS:
                            if b.current_signal >= 0 and b.last_context == 'danger_near':
                                # Strong reward for correct danger signaling
                                self._reinforce_signal(b, 3.0)
                                b.energy += LISTENER_REWARD  # survive to signal another day
                            elif b.current_signal >= 0 and b.last_context != 'danger_near':
                                # Punish wrong signal in dangerous situation
                                self._reinforce_signal(b, -1.0)
                            # Everyone nearby learns to flee from signals emitted near kills
                            for other in self.agents:
                                if other.current_signal >= 0 and self._dist(other, b) < SIGNAL_RANGE:
                                    self._reinforce_response(b, other.current_signal, -1.5)

        # Death & reproduction
        dead = [a for a in self.agents if a.energy <= DEATH_THRESHOLD]
        for a in dead:
            self.agents.remove(a)
            self.deaths += 1
            # Negative reinforcement for signaling behavior that led to death
            # (nearby agents learn)
            for b in self.agents:
                if self._dist_xy(a.x, a.y, b.x, b.y) < 8:
                    if b.current_signal >= 0:
                        self._reinforce_signal(b, -0.3)

        babies = []
        for a in self.agents:
            if a.energy > REPRODUCE_THRESHOLD and len(self.agents) + len(babies) < MAX_AGENTS:
                a.energy *= 0.5
                babies.append((
                    a.x + random.uniform(-2, 2),
                    a.y + random.uniform(-2, 2),
                    a.energy * 0.8,
                    a  # parent for inheritance
                ))
                self.births += 1

        for bx, by, be, parent in babies:
            self._spawn_agent(self._wrap(bx, WIDTH), self._wrap(by, HEIGHT), be, parent)

        # Stats
        pop = len(self.agents)
        avg_energy = sum(a.energy for a in self.agents) / max(pop, 1)
        active_signals = sum(1 for a in self.agents if a.current_signal >= 0)
        self.stats_history.append({
            'pop': pop,
            'avg_energy': avg_energy,
            'births': self.births,
            'deaths': self.deaths,
            'food': len(self.food_sources),
            'signals': active_signals,
        })

        # Logging
        self.logger.check_coordination(self.tick, self.agents, self.food_sources)
        self.logger.check_memory_patterns(self.tick, self.agents)
        self.logger.log_summary(self.tick, self)

        # Check for emergence milestones
        if self.tick == 100:
            self._log_signal_landscape()
        if self.tick % 500 == 0 and self.tick > 0:
            self._log_signal_landscape()

    def _cultural_transmission(self):
        """Agents copy signal strategies from high-energy neighbors.
        
        This is the missing coordination mechanism: instead of each agent
        learning in isolation, successful strategies spread horizontally
        through the population. Agents preferentially copy neighbors
        who have more energy (proxy for fitness).
        """
        for agent in self.agents:
            if random.random() > CULTURAL_RATE:
                continue
            
            # Find neighbors within cultural radius (using spatial grid)
            neighbors = [other for other, d in self._grid.query_radius(agent.x, agent.y, CULTURAL_RADIUS) if other is not agent]
            
            if not neighbors:
                continue
            
            # Pick a role model — weighted by energy (successful agents get copied)
            weights = []
            for n in neighbors:
                # Softmax-ish: energy advantage matters
                w = max(0.01, n.energy - agent.energy + CULTURAL_ENERGY_BIAS)
                weights.append(w)
            
            total_w = sum(weights)
            r = random.uniform(0, total_w)
            cumulative = 0
            role_model = neighbors[0]
            for i, n in enumerate(neighbors):
                cumulative += weights[i]
                if r <= cumulative:
                    role_model = n
                    break
            
            # Only copy if role model has more energy (don't copy losers)
            if role_model.energy <= agent.energy:
                continue
            
            # Blend signal weights toward role model's
            blend = CULTURAL_BLEND
            for s in range(NUM_SIGNALS):
                for ctx in agent.signal_weights[s]:
                    mine = agent.signal_weights[s][ctx]
                    theirs = role_model.signal_weights[s].get(ctx, 0)
                    agent.signal_weights[s][ctx] = mine * (1 - blend) + theirs * blend
            
            # Blend response weights too
            for s in range(NUM_SIGNALS):
                mine = agent.response_weights[s]
                theirs = role_model.response_weights[s]
                agent.response_weights[s] = mine * (1 - blend) + theirs * blend

    def _convention_enforcement(self):
        """Agents who signal consistently with neighbors get social energy bonuses.
        
        This creates pressure toward shared conventions: if you and your neighbor
        both signal ◆ when food is near, you both benefit. If you signal ▲ while
        everyone else signals ◆ in the same context, you pay a small cost.
        
        This is the 'social norm' mechanism — it doesn't enforce a specific mapping,
        it enforces AGREEMENT on whatever mapping the group converges on.
        """
        for agent in self.agents:
            if agent.current_signal < 0:
                continue
            
            for other, d in self._grid.query_radius(agent.x, agent.y, SIGNAL_RANGE):
                if other is agent or other.current_signal < 0:
                    continue
                
                # Both agents are signaling within range
                # Same context, same signal = convention match
                if agent.last_context == other.last_context:
                    if agent.current_signal == other.current_signal:
                        agent.energy += CONVENTION_BONUS
                    else:
                        agent.energy -= CONVENTION_PENALTY

    def _log_signal_landscape(self):
        """Log the current signal weight landscape across agents."""
        if not self.agents:
            return
        avg_weights = defaultdict(lambda: defaultdict(float))
        for a in self.agents:
            for s in range(NUM_SIGNALS):
                for ctx in a.signal_weights[s]:
                    avg_weights[s][ctx] += a.signal_weights[s][ctx]
        n = len(self.agents)
        lines = []
        for s in range(NUM_SIGNALS):
            parts = []
            for ctx in ['food_near', 'danger_near', 'friends_near', 'alone']:
                val = avg_weights[s][ctx] / n
                bar = '█' * int(val * 10)
                parts.append(f"{ctx}: {val:.2f} {bar}")
            lines.append(f"Signal {SIGNAL_NAMES[s]} (#{s}): " + " | ".join(parts))

        # Also log average response weights
        avg_resp = defaultdict(float)
        for a in self.agents:
            for s in range(NUM_SIGNALS):
                avg_resp[s] += a.response_weights[s]
        resp_parts = []
        for s in range(NUM_SIGNALS):
            v = avg_resp[s] / n
            direction = "approach" if v > 0 else "avoid"
            resp_parts.append(f"{SIGNAL_NAMES[s]}: {v:+.2f} ({direction})")

        self.logger.log_event(self.tick, "🔬 SIGNAL LANDSCAPE",
            "**Emission weights** (avg across population):\n" +
            "\n".join(f"  {l}" for l in lines) +
            f"\n\n**Response weights** (avg): " + " | ".join(resp_parts) +
            (f"\n\n**Predator signal tracking**: " +
             " | ".join(f"{SIGNAL_NAMES[s]}: {self.predator.signal_attraction[s]:+.2f}"
                        for s in range(NUM_SIGNALS)) +
             f" (style: {self.predator.hunt_style}, kills: {self.predator.kills})"
             if self.predator else ""))

    def render(self):
        """Render the simulation to a string buffer."""
        grid = [[' ' for _ in range(WIDTH)] for _ in range(HEIGHT)]

        # Draw trails
        for (tx, ty), age in self.trails.items():
            if 0 <= tx < WIDTH and 0 <= ty < HEIGHT and grid[ty][tx] == ' ':
                idx = TRAIL_DECAY - age
                if 0 <= idx < len(TRAIL_CHARS):
                    grid[ty][tx] = f'\033[90m{TRAIL_CHARS[idx]}\033[0m'

        # Draw signal pulses (expanding rings)
        for px, py, sig, age in self.signal_pulses:
            radius = (4 - age) * 2
            color = SIGNAL_COLORS[sig]
            for angle in range(0, 360, 30):
                rx = int(px + radius * math.cos(math.radians(angle))) % WIDTH
                ry = int(py + radius * math.sin(math.radians(angle))) % HEIGHT
                if grid[ry][rx] == ' ':
                    grid[ry][rx] = f'{color}·\033[0m'

        # Draw food
        for food in self.food_sources:
            ix, iy = int(food.x) % WIDTH, int(food.y) % HEIGHT
            grid[iy][ix] = FOOD_GLYPH

        # Draw agents
        for a in self.agents:
            ix, iy = int(a.x) % WIDTH, int(a.y) % HEIGHT
            sig_g = a.signal_glyph()
            if sig_g:
                grid[iy][ix] = sig_g
            else:
                grid[iy][ix] = a.colored_glyph()

        # Draw predator
        if self.predator:
            px, py = int(self.predator.x) % WIDTH, int(self.predator.y) % HEIGHT
            grid[py][px] = PREDATOR_GLYPH

        # Compose frame
        lines = []
        border_h = '━' * (WIDTH + 2)
        lines.append(f'\033[1;35m┏{border_h}┓\033[0m')
        for row in grid:
            lines.append(f'\033[1;35m┃\033[0m ' + ''.join(row) + f' \033[1;35m┃\033[0m')
        lines.append(f'\033[1;35m┗{border_h}┛\033[0m')

        # Stats
        pop = len(self.agents)
        avg_e = sum(a.energy for a in self.agents) / max(pop, 1)
        food_count = len(self.food_sources)
        active_sigs = sum(1 for a in self.agents if a.current_signal >= 0)
        clusters = self._count_clusters()
        season_str = SEASONS[self.current_season] if self.use_seasons else ''
        avg_mem = sum(len(a.memory) for a in self.agents) / max(pop, 1) if self.agents else 0

        # Sparkline
        hist = self.stats_history[-60:]
        if hist:
            pops = [h['pop'] for h in hist]
            mn, mx = min(pops), max(pops)
            sparks = '▁▂▃▄▅▆▇█'
            sparkline = ''
            for p in pops:
                idx = int((p - mn) / max(mx - mn, 1) * (len(sparks) - 1))
                sparkline += sparks[idx]
        else:
            sparkline = ''

        # Signal stats
        sig_counts = defaultdict(int)
        for a in self.agents:
            if a.current_signal >= 0:
                sig_counts[a.current_signal] += 1

        sig_bar = ''
        for s in range(NUM_SIGNALS):
            c = sig_counts.get(s, 0)
            sig_bar += f'  {SIGNAL_COLORS[s]}{SIGNAL_NAMES[s]}×{c}\033[0m'

        # Detected meanings
        meaning_str = ''
        for key, detected in self.logger.pattern_detected.items():
            parts = key.split('_')
            sig_num = int(parts[1])
            ctx = '_'.join(parts[2:])
            meaning = {'food_near': 'FOOD', 'danger_near': 'DANGER',
                       'friends_near': 'GATHER', 'alone': 'HELP'}.get(ctx, ctx)
            meaning_str += f'  {SIGNAL_COLORS[sig_num]}{SIGNAL_NAMES[sig_num]}="{meaning}"\033[0m'

        status = (
            f'  \033[1;33m⏱ Tick:\033[0m {self.tick:>5}  '
            f'\033[1;32m👥 Pop:\033[0m {pop:>3}  '
            f'\033[1;36m⚡ Energy:\033[0m {avg_e:>5.1f}  '
            f'\033[1;34m🔷 Flocks:\033[0m {clusters}  '
            f'\033[1;93m✦ Food:\033[0m {food_count}  '
            f'\033[1;35m📡 Signals:\033[0m {active_sigs}'
        )
        lines.append(status)
        if self.use_seasons:
            lines.append(f'  {season_str}  '
                         f'\033[90mSeason tick: {self.season_tick}/{SEASON_LENGTH}\033[0m  '
                         f'\033[1;33m🧠 Mem:\033[0m {avg_mem:.1f}  '
                         f'\033[90mGen:\033[0m {self.max_generation}')
        lines.append(f'  \033[1;32m🐣\033[0m {self.births}  \033[1;31m💀\033[0m {self.deaths}  '
                     f'Active:{sig_bar}')
        lines.append(f'  \033[90mPopulation: [{sparkline}]\033[0m')

        if meaning_str:
            lines.append(f'  \033[1;97m🧠 Emergent Meanings:\033[0m{meaning_str}')
        else:
            lines.append(f'  \033[90m🧠 Watching for emergent signal meanings...\033[0m')

        lines.append('')
        lines.append(f'  \033[90m↑→↓← agents  ✦ food  '
                     f'◆▲●■ signal types  '
                     f'🔴dying 🟡ok 🟢healthy 🔵thriving\033[0m')
        if self.predator:
            p = self.predator
            lines.append(f'  \033[91m⬤ = PREDATOR ({p.hunt_style.upper()}) '
                         f'kills:{p.kills} stamina:{p.stamina:.1f}\033[0m')

        return '\n'.join(lines)

    def _count_clusters(self):
        visited = set()
        clusters = 0
        agent_list = list(self.agents)
        for a in agent_list:
            if a.id in visited:
                continue
            clusters += 1
            stack = [a]
            while stack:
                curr = stack.pop()
                if curr.id in visited:
                    continue
                visited.add(curr.id)
                for b in agent_list:
                    if b.id not in visited and self._dist(curr, b) < COHESION_RADIUS:
                        stack.append(b)
        return clusters


def main():
    parser = argparse.ArgumentParser(
        description='🌊 Emergence Simulator v3 — seasons, memory & predator co-evolution!')
    parser.add_argument('--agents', type=int, default=50, help='Initial agents (default: 50)')
    parser.add_argument('--speed', type=float, default=0.08, help='Seconds between frames')
    parser.add_argument('--predator', action='store_true', help='Add a predator')
    parser.add_argument('--seasons', action='store_true', help='Enable seasonal cycles')
    args = parser.parse_args()

    sim = Simulation(num_agents=args.agents, use_predator=args.predator, use_seasons=args.seasons)

    sys.stdout.write('\033[?25l')
    sys.stdout.flush()

    try:
        while True:
            sim.step()
            frame = sim.render()

            sys.stdout.write('\033[2J\033[H')
            sys.stdout.write(
                f'\033[1;97m  🌊 EMERGENCE SIMULATOR v3\033[0m  '
                f'\033[90m— seasons • memory • predator co-evolution\033[0m\n\n')
            sys.stdout.write(frame)
            sys.stdout.write('\n\n  \033[90mCtrl+C to exit  |  Log: emergence-log.md\033[0m\n')
            sys.stdout.flush()

            time.sleep(args.speed)

            if len(sim.agents) == 0:
                sys.stdout.write('\n  \033[1;31m☠  All agents perished.\033[0m\n\n')
                break

    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\033[?25h\n')
        sys.stdout.flush()
        print(f'\n  \033[1;33mFinal stats after {sim.tick} ticks:\033[0m')
        print(f'    Population: {len(sim.agents)}')
        print(f'    Births: {sim.births}  Deaths: {sim.deaths}')
        print(f'    Flocks: {sim._count_clusters()}')
        print(f'    Food remaining: {len(sim.food_sources)}')

        # Final signal analysis
        if sim.agents:
            print(f'\n  \033[1;35mSignal Analysis:\033[0m')
            for s in range(NUM_SIGNALS):
                total = sum(sim.logger.signal_context_history[s].values())
                if total > 0:
                    top_ctx = max(sim.logger.signal_context_history[s],
                                  key=sim.logger.signal_context_history[s].get)
                    ratio = sim.logger.signal_context_history[s][top_ctx] / total
                    meaning = {'food_near': 'FOOD', 'danger_near': 'DANGER',
                               'friends_near': 'GATHER', 'alone': 'HELP'}.get(top_ctx, top_ctx)
                    print(f'    Signal {SIGNAL_NAMES[s]} (#{s}): '
                          f'used {total}× — mostly means "{meaning}" ({ratio:.0%})')

        # Log final state
        sim.logger.log_event(sim.tick, "🏁 SIMULATION END",
            f"Final pop: {len(sim.agents)} | Births: {sim.births} | Deaths: {sim.deaths}")
        sim._log_signal_landscape()

        print(f'\n  \033[90mFull log saved to: {LOG_PATH}\033[0m\n')


if __name__ == '__main__':
    main()
