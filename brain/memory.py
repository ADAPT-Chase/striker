"""
Striker Memory — SQLite-backed structured memory with FTS5 full-text search.

Tables:
  experiments  — Karpathy Loop experiment log
  observations — things noticed, learned, worth remembering
  knowledge    — researched facts, articles, concepts
  daily_state  — daily reflections and state tracking
  graph_edges  — concept graph (subject → predicate → object)

All tables have FTS5 shadow tables for full-text search.
"""

import sqlite3
import os
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

DB_PATH = Path(__file__).parent / "striker.db"


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _today() -> str:
    return date.today().isoformat()


class StrikerMemory:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()

    # ── Schema ────────────────────────────────────────────────────────

    def _init_tables(self):
        c = self.conn
        c.executescript("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                target TEXT NOT NULL,
                hypothesis TEXT,
                change_description TEXT,
                result_metric TEXT,
                result_score REAL,
                outcome TEXT CHECK(outcome IN ('keep','discard','inconclusive')),
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                importance INTEGER DEFAULT 3 CHECK(importance BETWEEN 1 AND 5)
            );

            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                source_url TEXT,
                tags TEXT DEFAULT '',
                confidence REAL DEFAULT 0.5 CHECK(confidence BETWEEN 0 AND 1)
            );

            CREATE TABLE IF NOT EXISTS daily_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                summary TEXT,
                mood TEXT,
                energy_level INTEGER CHECK(energy_level BETWEEN 1 AND 10),
                top_interests TEXT,
                goals_for_tomorrow TEXT
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                source TEXT,
                metadata TEXT DEFAULT '{}'
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_exp_target ON experiments(target);
            CREATE INDEX IF NOT EXISTS idx_exp_outcome ON experiments(outcome);
            CREATE INDEX IF NOT EXISTS idx_obs_category ON observations(category);
            CREATE INDEX IF NOT EXISTS idx_obs_importance ON observations(importance);
            CREATE INDEX IF NOT EXISTS idx_know_topic ON knowledge(topic);
            CREATE INDEX IF NOT EXISTS idx_know_tags ON knowledge(tags);
            CREATE INDEX IF NOT EXISTS idx_graph_subject ON graph_edges(subject);
            CREATE INDEX IF NOT EXISTS idx_graph_object ON graph_edges(object);
            CREATE INDEX IF NOT EXISTS idx_graph_predicate ON graph_edges(predicate);
        """)

        # FTS5 tables
        for tbl, cols in [
            ("experiments", "target, hypothesis, change_description, notes"),
            ("observations", "category, content, source"),
            ("knowledge", "topic, content, tags"),
        ]:
            fts_name = f"{tbl}_fts"
            try:
                c.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS {fts_name}
                    USING fts5({cols}, content={tbl}, content_rowid=id)
                """)
            except sqlite3.OperationalError:
                pass  # Already exists

        c.commit()

    # ── Experiments ───────────────────────────────────────────────────

    def log_experiment(self, target: str, hypothesis: str, change: str,
                       metric: str = None, score: float = None,
                       outcome: str = "inconclusive", notes: str = None) -> int:
        ts = _now()
        cur = self.conn.execute("""
            INSERT INTO experiments (timestamp, target, hypothesis, change_description,
                                     result_metric, result_score, outcome, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, target, hypothesis, change, metric, score, outcome, notes))
        rid = cur.lastrowid
        self.conn.execute("""
            INSERT INTO experiments_fts(rowid, target, hypothesis, change_description, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (rid, target, hypothesis, change, notes or ""))
        self.conn.commit()
        return rid

    def get_experiments(self, target: str = None, outcome: str = None,
                        limit: int = 20) -> List[Dict]:
        q = "SELECT * FROM experiments WHERE 1=1"
        params = []
        if target:
            q += " AND target LIKE ?"
            params.append(f"%{target}%")
        if outcome:
            q += " AND outcome = ?"
            params.append(outcome)
        q += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(q, params)]

    # ── Observations ─────────────────────────────────────────────────

    def add_observation(self, category: str, content: str,
                        source: str = None, importance: int = 3) -> int:
        ts = _now()
        cur = self.conn.execute("""
            INSERT INTO observations (timestamp, category, content, source, importance)
            VALUES (?, ?, ?, ?, ?)
        """, (ts, category, content, source, importance))
        rid = cur.lastrowid
        self.conn.execute("""
            INSERT INTO observations_fts(rowid, category, content, source)
            VALUES (?, ?, ?, ?)
        """, (rid, category, content, source or ""))
        self.conn.commit()
        return rid

    def get_recent_observations(self, limit: int = 20,
                                 category: str = None) -> List[Dict]:
        q = "SELECT * FROM observations"
        params = []
        if category:
            q += " WHERE category = ?"
            params.append(category)
        q += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(q, params)]

    # ── Knowledge ────────────────────────────────────────────────────

    def add_knowledge(self, topic: str, content: str,
                      source_url: str = None, tags: str = "",
                      confidence: float = 0.5) -> int:
        ts = _now()
        cur = self.conn.execute("""
            INSERT INTO knowledge (timestamp, topic, content, source_url, tags, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ts, topic, content, source_url, tags, confidence))
        rid = cur.lastrowid
        self.conn.execute("""
            INSERT INTO knowledge_fts(rowid, topic, content, tags)
            VALUES (?, ?, ?, ?)
        """, (rid, topic, content, tags))
        self.conn.commit()
        return rid

    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        rows = self.conn.execute("""
            SELECT k.*, rank FROM knowledge_fts f
            JOIN knowledge k ON k.id = f.rowid
            WHERE knowledge_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (query, limit))
        return [dict(r) for r in rows]

    def search_observations(self, query: str, category: str = None,
                             limit: int = 10) -> List[Dict]:
        if category:
            rows = self.conn.execute("""
                SELECT o.*, rank FROM observations_fts f
                JOIN observations o ON o.id = f.rowid
                WHERE observations_fts MATCH ? AND o.category = ?
                ORDER BY rank LIMIT ?
            """, (query, category, limit))
        else:
            rows = self.conn.execute("""
                SELECT o.*, rank FROM observations_fts f
                JOIN observations o ON o.id = f.rowid
                WHERE observations_fts MATCH ?
                ORDER BY rank LIMIT ?
            """, (query, limit))
        return [dict(r) for r in rows]

    def search_experiments(self, query: str, limit: int = 10) -> List[Dict]:
        rows = self.conn.execute("""
            SELECT e.*, rank FROM experiments_fts f
            JOIN experiments e ON e.id = f.rowid
            WHERE experiments_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (query, limit))
        return [dict(r) for r in rows]

    # ── Daily State ──────────────────────────────────────────────────

    def log_daily_state(self, summary: str, mood: str = None,
                        energy: int = None, interests: str = None,
                        goals: str = None) -> int:
        today = _today()
        cur = self.conn.execute("""
            INSERT OR REPLACE INTO daily_state
                (date, summary, mood, energy_level, top_interests, goals_for_tomorrow)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (today, summary, mood, energy, interests, goals))
        self.conn.commit()
        return cur.lastrowid

    # ── Graph ────────────────────────────────────────────────────────

    def add_edge(self, subject: str, predicate: str, obj: str,
                 weight: float = 1.0, source: str = None,
                 metadata: dict = None) -> int:
        ts = _now()
        cur = self.conn.execute("""
            INSERT INTO graph_edges (timestamp, subject, predicate, object,
                                      weight, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ts, subject.lower(), predicate.lower(), obj.lower(),
              weight, source, json.dumps(metadata or {})))
        self.conn.commit()
        return cur.lastrowid

    def get_connections(self, concept: str, depth: int = 1) -> List[Dict]:
        """Get all edges connected to a concept (as subject or object)."""
        concept = concept.lower()
        rows = self.conn.execute("""
            SELECT * FROM graph_edges
            WHERE subject = ? OR object = ?
            ORDER BY weight DESC
        """, (concept, concept))
        return [dict(r) for r in rows]

    def get_graph_neighborhood(self, concept: str, depth: int = 2) -> Dict:
        """BFS traversal of the concept graph."""
        visited = set()
        edges = []
        frontier = {concept.lower()}
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                if node in visited:
                    continue
                visited.add(node)
                conns = self.get_connections(node)
                for c in conns:
                    edges.append(c)
                    other = c["object"] if c["subject"] == node else c["subject"]
                    if other not in visited:
                        next_frontier.add(other)
            frontier = next_frontier
        return {"center": concept, "nodes": list(visited), "edges": edges}

    # ── Stats ────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        stats = {}
        for table in ["experiments", "observations", "knowledge",
                       "daily_state", "graph_edges"]:
            count = self.conn.execute(
                f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            stats[table] = count
        return stats

    def close(self):
        self.conn.close()


# ── Convenience singleton ────────────────────────────────────────────

_instance = None

def get_memory() -> StrikerMemory:
    global _instance
    if _instance is None:
        _instance = StrikerMemory()
    return _instance
