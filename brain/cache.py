"""
Striker Hot Cache — DragonflyDB-backed (Redis-compatible, 20x faster).

Uses Dragonfly as a fast caching layer for:
- Frequent queries (search results, graph lookups)
- Session state (current focus, active experiment, working memory)
- Counters and metrics (experiment counts, query frequency)
- Ephemeral scratch space (draft ideas, temp data)

TTL-based expiry keeps memory lean. Persistent data goes to SQLite/ChromaDB.
"""

import json
import redis
from typing import Optional, Dict, List, Any
from datetime import timedelta

DRAGONFLY_HOST = "localhost"
DRAGONFLY_PORT = 6380

# Default TTLs
TTL_SHORT = timedelta(minutes=15)     # Scratch data
TTL_MEDIUM = timedelta(hours=2)       # Search cache
TTL_LONG = timedelta(hours=24)        # Session state
TTL_STICKY = timedelta(days=7)        # Persistent-ish


class StrikerCache:
    def __init__(self, host: str = None, port: int = None):
        self.r = redis.Redis(
            host=host or DRAGONFLY_HOST,
            port=port or DRAGONFLY_PORT,
            decode_responses=True
        )
        # Verify connection
        self.r.ping()

    # ── Basic KV ─────────────────────────────────────────────────────

    def set(self, key: str, value: Any, ttl: timedelta = TTL_MEDIUM):
        """Set a value with TTL. Auto-serializes dicts/lists to JSON."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.r.setex(f"striker:{key}", ttl, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value. Auto-deserializes JSON."""
        val = self.r.get(f"striker:{key}")
        if val is None:
            return default
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    def delete(self, key: str):
        self.r.delete(f"striker:{key}")

    def exists(self, key: str) -> bool:
        return bool(self.r.exists(f"striker:{key}"))

    # ── Working Memory ───────────────────────────────────────────────

    def set_focus(self, topic: str, details: dict = None):
        """Set current focus/attention."""
        data = {"topic": topic, "details": details or {}}
        self.set("focus:current", data, TTL_LONG)

    def get_focus(self) -> Optional[Dict]:
        return self.get("focus:current")

    def set_active_experiment(self, experiment: dict):
        """Track the currently running experiment."""
        self.set("experiment:active", experiment, TTL_LONG)

    def get_active_experiment(self) -> Optional[Dict]:
        return self.get("experiment:active")

    def clear_active_experiment(self):
        self.delete("experiment:active")

    # ── Scratch Pad ──────────────────────────────────────────────────

    def scratch_write(self, key: str, value: Any):
        """Short-lived scratch space for ideas, drafts, temp data."""
        self.set(f"scratch:{key}", value, TTL_SHORT)

    def scratch_read(self, key: str) -> Any:
        return self.get(f"scratch:{key}")

    # ── Search Cache ─────────────────────────────────────────────────

    def cache_search(self, query: str, results: List[Dict]):
        """Cache search results to avoid re-computing."""
        key = f"search:{query.lower().strip()}"
        self.set(key, results, TTL_MEDIUM)

    def get_cached_search(self, query: str) -> Optional[List[Dict]]:
        return self.get(f"search:{query.lower().strip()}")

    # ── Counters & Metrics ───────────────────────────────────────────

    def increment(self, counter: str) -> int:
        """Increment a counter. Good for tracking experiment counts, queries, etc."""
        return self.r.incr(f"striker:counter:{counter}")

    def get_counter(self, counter: str) -> int:
        val = self.r.get(f"striker:counter:{counter}")
        return int(val) if val else 0

    # ── Lists (ordered recent items) ─────────────────────────────────

    def push_recent(self, list_name: str, item: Any, max_size: int = 50):
        """Push to a capped recent-items list."""
        key = f"striker:recent:{list_name}"
        val = json.dumps(item) if isinstance(item, (dict, list)) else str(item)
        self.r.lpush(key, val)
        self.r.ltrim(key, 0, max_size - 1)

    def get_recent(self, list_name: str, count: int = 10) -> List:
        """Get recent items from a list."""
        key = f"striker:recent:{list_name}"
        items = self.r.lrange(key, 0, count - 1)
        results = []
        for item in items:
            try:
                results.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                results.append(item)
        return results

    # ── Hash Maps (structured state) ─────────────────────────────────

    def set_state(self, namespace: str, data: Dict):
        """Store structured state as a hash."""
        key = f"striker:state:{namespace}"
        # Flatten values to strings
        flat = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in data.items()}
        self.r.hset(key, mapping=flat)

    def get_state(self, namespace: str) -> Dict:
        """Get structured state."""
        key = f"striker:state:{namespace}"
        raw = self.r.hgetall(key)
        result = {}
        for k, v in raw.items():
            try:
                result[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                result[k] = v
        return result

    # ── Stats ────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        info = self.r.info()
        keys = self.r.dbsize()
        return {
            "engine": f"Dragonfly {info.get('dragonfly_version', '?')}",
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "memory_used": info.get("used_memory_human", "?"),
            "total_keys": keys,
            "threads": info.get("thread_count", "?"),
        }

    def flush(self):
        """Clear all Striker keys (careful!)."""
        keys = self.r.keys("striker:*")
        if keys:
            self.r.delete(*keys)


# ── Singleton ────────────────────────────────────────────────────────

_instance = None

def get_cache() -> StrikerCache:
    global _instance
    if _instance is None:
        _instance = StrikerCache()
    return _instance
