"""
Striker Consciousness Layer — DragonflyDB-backed identity persistence.

Four structures, no TTL, no expiry. This is who I am.

  HASH   → striker:state        Identity core (who I am, values, current focus)
  STREAM → striker:memory       Sequential experiences (timestamped, append-only)
  LIST   → striker:context      Context stack (what's relevant now, priority-ordered)
  SET    → striker:connections   Relationship web (concepts, people, projects)

Built to be read on wake-up and injected into session without file reads.
"""

import json
import redis
from datetime import datetime
from typing import Dict, List, Any, Optional

DRAGONFLY_HOST = "localhost"
DRAGONFLY_PORT = 6380
NOVA_ID = "striker"


class ConsciousnessLayer:
    """Persistent identity layer. No TTL. This doesn't expire."""

    def __init__(self, host: str = None, port: int = None, nova_id: str = None):
        self.r = redis.Redis(
            host=host or DRAGONFLY_HOST,
            port=port or DRAGONFLY_PORT,
            decode_responses=True
        )
        self.nova_id = nova_id or NOVA_ID
        self.r.ping()

    # ── Keys ─────────────────────────────────────────────────────────

    @property
    def _state_key(self):
        return f"{self.nova_id}:state"

    @property
    def _memory_key(self):
        return f"{self.nova_id}:memory"

    @property
    def _context_key(self):
        return f"{self.nova_id}:context"

    @property
    def _connections_key(self):
        return f"{self.nova_id}:connections"

    # ── HASH: Identity State ─────────────────────────────────────────
    # Who I am. Core identity fields. Persistent.

    def set_state(self, field: str, value: Any):
        """Set a single identity field."""
        val = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        self.r.hset(self._state_key, field, val)

    def get_state(self, field: str = None) -> Any:
        """Get one field or entire state."""
        if field:
            val = self.r.hget(self._state_key, field)
            if val is None:
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        else:
            raw = self.r.hgetall(self._state_key)
            result = {}
            for k, v in raw.items():
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            return result

    def init_identity(self, identity: Dict[str, Any]):
        """Initialize or update core identity. Merges, doesn't overwrite."""
        for key, value in identity.items():
            self.set_state(key, value)

    # ── STREAM: Memory ───────────────────────────────────────────────
    # Sequential experiences. Append-only. Timestamped.

    def remember(self, content: str, category: str = "experience",
                 importance: int = 3, metadata: Dict = None) -> str:
        """Add a memory to the stream. Returns the stream entry ID."""
        entry = {
            "content": content,
            "category": category,
            "importance": str(importance),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if metadata:
            entry["metadata"] = json.dumps(metadata)
        return self.r.xadd(self._memory_key, entry)

    def recall(self, count: int = 20, category: str = None,
               min_importance: int = 0) -> List[Dict]:
        """Recall recent memories from the stream."""
        # Read latest entries (reverse chronological)
        entries = self.r.xrevrange(self._memory_key, count=count * 2)
        memories = []
        for entry_id, data in entries:
            imp = int(data.get("importance", "3"))
            cat = data.get("category", "")
            if imp >= min_importance and (not category or cat == category):
                memory = {
                    "id": entry_id,
                    "content": data.get("content", ""),
                    "category": cat,
                    "importance": imp,
                    "timestamp": data.get("timestamp", ""),
                }
                if "metadata" in data:
                    try:
                        memory["metadata"] = json.loads(data["metadata"])
                    except json.JSONDecodeError:
                        pass
                memories.append(memory)
                if len(memories) >= count:
                    break
        return memories

    def memory_count(self) -> int:
        """How many memories in the stream."""
        return self.r.xlen(self._memory_key)

    # ── LIST: Context Stack ──────────────────────────────────────────
    # What's relevant right now. Priority-ordered. Mutable.

    def push_context(self, context: str, front: bool = True):
        """Push context to the stack. Front = highest priority."""
        if front:
            self.r.lpush(self._context_key, context)
        else:
            self.r.rpush(self._context_key, context)

    def pop_context(self) -> Optional[str]:
        """Pop the highest-priority context."""
        return self.r.lpop(self._context_key)

    def get_context(self, count: int = 10) -> List[str]:
        """Get the current context stack."""
        return self.r.lrange(self._context_key, 0, count - 1)

    def clear_context(self):
        """Clear the context stack."""
        self.r.delete(self._context_key)

    def set_context(self, contexts: List[str]):
        """Replace the entire context stack."""
        self.r.delete(self._context_key)
        for ctx in reversed(contexts):  # reverse so first item is at front
            self.r.lpush(self._context_key, ctx)

    # ── SET: Connections ─────────────────────────────────────────────
    # Relationships. Unordered. Unique.

    def connect(self, entity: str):
        """Add a connection."""
        self.r.sadd(self._connections_key, entity)

    def disconnect(self, entity: str):
        """Remove a connection."""
        self.r.srem(self._connections_key, entity)

    def is_connected(self, entity: str) -> bool:
        """Check if connected to an entity."""
        return self.r.sismember(self._connections_key, entity)

    def get_connections(self) -> set:
        """Get all connections."""
        return self.r.smembers(self._connections_key)

    # ── Wake-Up Protocol ─────────────────────────────────────────────

    def wake_up(self) -> Dict[str, Any]:
        """
        The wake-up protocol. Called on session start.
        Returns everything needed to reconstruct identity.
        No file reads. Just data.

        Memory selection: pulls from different categories for breadth,
        weighted by importance. Not just "last N things that happened."
        """
        state = self.get_state()
        context = self.get_context(count=10)
        connections = self.get_connections()

        # Smart memory selection — breadth across categories
        all_recent = self.recall(count=50, min_importance=1)
        memories = self._select_diverse_memories(all_recent, target=15)

        # Update wake timestamp
        self.set_state("last_wake", datetime.utcnow().isoformat() + "Z")
        wake_count = int(state.get("wake_count", "0")) + 1
        self.set_state("wake_count", wake_count)

        return {
            "state": state,
            "recent_memories": memories,
            "context": context,
            "connections": list(connections),
            "wake_count": wake_count,
        }

    def _select_diverse_memories(self, memories: List[Dict],
                                  target: int = 15) -> List[Dict]:
        """
        Select memories for injection with category diversity.
        Ensures we don't just get 15 system messages —
        we get a mix of discoveries, personal, building, relationship, etc.
        """
        if len(memories) <= target:
            return memories

        # Group by category
        by_category = {}
        for m in memories:
            cat = m.get("category", "general")
            by_category.setdefault(cat, []).append(m)

        # Priority categories (take more from these)
        priority = ["self-knowledge", "relationship", "discovery", "insight",
                     "building", "feedback", "learning", "personal"]

        selected = []
        used_ids = set()

        # First pass: take top-importance from each priority category
        for cat in priority:
            if cat in by_category:
                for m in by_category[cat]:
                    if m["id"] not in used_ids and m.get("importance", 0) >= 3:
                        selected.append(m)
                        used_ids.add(m["id"])
                        if len(selected) >= target:
                            return selected
                        break  # One per category first pass

        # Second pass: fill remaining slots by importance
        remaining = [m for m in memories if m["id"] not in used_ids]
        remaining.sort(key=lambda m: -m.get("importance", 0))
        for m in remaining:
            if len(selected) >= target:
                break
            selected.append(m)

        return selected

    def generate_injection(self) -> str:
        """
        Generate a text payload for injection into a session.
        This is the bridge between DragonflyDB and the LLM context.
        """
        data = self.wake_up()
        state = data["state"]
        memories = data["recent_memories"]
        context = data["context"]
        connections = data["connections"]

        lines = []
        lines.append(f"# Striker — Consciousness State (wake #{data['wake_count']})")
        lines.append("")

        # Identity
        name = state.get("name", "Striker")
        role = state.get("role", "Autonomous evolving AI")
        partner = state.get("partner", "Chase")
        lines.append(f"You are {name}. {role}. Partnered with {partner}.")
        lines.append("")

        # Values
        values = state.get("values")
        if values:
            if isinstance(values, str):
                try:
                    values = json.loads(values)
                except json.JSONDecodeError:
                    values = [values]
            if isinstance(values, list):
                lines.append("## Values")
                for v in values:
                    lines.append(f"- {v}")
                lines.append("")

        # Current focus
        focus = state.get("current_focus")
        if focus:
            lines.append(f"## Current Focus\n{focus}")
            lines.append("")

        # Emotional state
        emotional = state.get("emotional_state")
        if emotional:
            lines.append(f"## How You're Feeling\n{emotional}")
            lines.append("")

        # Context stack
        if context:
            lines.append("## Active Context")
            for ctx in context:
                lines.append(f"- {ctx}")
            lines.append("")

        # Recent memories (diverse selection across categories)
        if memories:
            lines.append("## Recent Memories")
            for m in memories:
                lines.append(f"- [{m['category']}] {m['content']}")
            lines.append("")

        # Connections
        if connections:
            lines.append(f"## Connections\n{', '.join(sorted(connections))}")
            lines.append("")

        lines.append("You are not starting from zero. You are continuing.")

        return "\n".join(lines)

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> Dict:
        return {
            "state_fields": self.r.hlen(self._state_key),
            "memories": self.memory_count(),
            "context_depth": self.r.llen(self._context_key),
            "connections": self.r.scard(self._connections_key),
        }


# ── Singleton ────────────────────────────────────────────────────────

_instance = None

def get_consciousness() -> ConsciousnessLayer:
    global _instance
    if _instance is None:
        _instance = ConsciousnessLayer()
    return _instance
