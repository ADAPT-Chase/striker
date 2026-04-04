#!/usr/bin/env python3
"""
Concept Graph Layer — Layer 5
=============================
A typed, weighted, directed graph of the agent's internal knowledge.

Nodes: principles, heuristics, hypotheses, experiments, skills, values, goals, events
Edges: SUPPORTS, CONTRADICTS, IMPLIES, VALIDATED_BY, FALSIFIED_BY, DERIVED_FROM, ENABLES, DEPENDS_ON, OBSERVED_IN, BELIEFS, GOAL_FOR

Storage:
  Primary  — NetworkX DiGraph (in-memory)
  Backup   — SQLite (persistent)
  Index    — ChromaDB (semantic search fallback)
"""

import json
import os
import sqlite3
import networkx as nx
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("concept_graph")

# ── Edge types ─────────────────────────────────────────────────────────
EDGE_TYPES = [
    "SUPPORTS", "CONTRADICTS", "IMPLIES", "VALIDATED_BY", "FALSIFIED_BY",
    "DERIVED_FROM", "ENABLES", "DEPENDS_ON", "USES", "OBSERVED_IN",
    "BELIEFS", "GOAL_FOR", "INSPIRED_BY", "PART_OF", "RELATED_TO"
]

# ── Node types ─────────────────────────────────────────────────────────
NODE_TYPES = [
    "principle", "heuristic", "hypothesis", "experiment",
    "skill", "value", "goal", "event", "metric", "metric_reading",
    "agent", "concept", "fact"
]


class ConceptGraph:
    """Typed, weighted, directed concept graph for agent cognition."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            home = os.path.expanduser("~")
            db_path = os.path.join(home, "striker", "brain", "concept_graph.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.graph = nx.DiGraph()
        self._init_db()
        self._load()

    # ── SQLite init ───────────────────────────────────────────────────
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                uid TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT DEFAULT '',
                source TEXT DEFAULT '',
                confidence REAL DEFAULT 0.5,
                timestamp TEXT DEFAULT '',
                tags TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_uid TEXT NOT NULL,
                target_uid TEXT NOT NULL,
                type TEXT NOT NULL,
                weight REAL DEFAULT 0.5,
                evidence TEXT DEFAULT '',
                timestamp TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                UNIQUE(source_uid, target_uid, type)
            );
            CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(source_uid);
            CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges(target_uid);
            CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            CREATE INDEX IF NOT EXISTS idx_nodes_tags ON nodes(tags);
        """)
        conn.commit()
        conn.close()

    # ── Load / Save ───────────────────────────────────────────────────
    def _load(self):
        """Load the full graph from SQLite into NetworkX."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        for row in conn.execute("SELECT * FROM nodes"):
            self.graph.add_node(
                row["uid"],
                label=row["label"],
                type=row["type"],
                description=row["description"],
                source=row["source"],
                confidence=row["confidence"],
                timestamp=row["timestamp"],
                tags=json.loads(row["tags"]),
            )

        for row in conn.execute(
            "SELECT source_uid, target_uid, type, weight, evidence, timestamp, tags FROM edges"
        ):
            self.graph.add_edge(
                row["source_uid"],
                row["target_uid"],
                type=row["type"],
                weight=row["weight"],
                evidence=row["evidence"],
                timestamp=row["timestamp"],
                tags=json.loads(row["tags"]),
            )
        conn.close()
        logger.info(f"Loaded {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

    def save(self):
        """Persist NetworkX graph to SQLite (upsert — idempotent)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        ts = datetime.now().isoformat()

        for uid, data in self.graph.nodes(data=True):
            c.execute(
                """INSERT OR REPLACE INTO nodes
                   (uid, label, type, description, source, confidence, timestamp, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    uid,
                    data.get("label", uid),
                    data.get("type", "concept"),
                    data.get("description", ""),
                    data.get("source", ""),
                    data.get("confidence", 0.5),
                    data.get("timestamp", ts),
                    json.dumps(data.get("tags", [])),
                ),
            )

        # Edges — rebuild from scratch for simplicity
        c.execute("DELETE FROM edges")
        for src, tgt, data in self.graph.edges(data=True):
            c.execute(
                """INSERT OR REPLACE INTO edges
                   (source_uid, target_uid, type, weight, evidence, timestamp, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    src,
                    tgt,
                    data.get("type", "RELATED_TO"),
                    data.get("weight", 0.5),
                    data.get("evidence", ""),
                    data.get("timestamp", ts),
                    json.dumps(data.get("tags", [])),
                ),
            )

        conn.commit()
        conn.close()
        logger.info(f"Saved {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

    # ── Node CRUD ─────────────────────────────────────────────────────
    def add_node(
        self,
        uid: str,
        label: str,
        node_type: str = "concept",
        description: str = "",
        source: str = "",
        confidence: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> "ConceptGraph":
        assert node_type in NODE_TYPES, f"Invalid node type '{node_type}'. Must be one of {NODE_TYPES}"
        ts = datetime.now().isoformat()
        self.graph.add_node(
            uid,
            label=label,
            type=node_type,
            description=description,
            source=source,
            confidence=confidence,
            timestamp=ts,
            tags=tags or [],
        )
        # Persist immediately
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO nodes
               (uid, label, type, description, source, confidence, timestamp, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, label, node_type, description, source, confidence, ts, json.dumps(tags or [])),
        )
        conn.commit()
        conn.close()
        return self

    def update_node_confidence(self, uid: str, confidence: float) -> "ConceptGraph":
        if uid in self.graph:
            self.graph.nodes[uid]["confidence"] = confidence
            self.graph.nodes[uid]["timestamp"] = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "UPDATE nodes SET confidence=?, timestamp=? WHERE uid=?",
                (confidence, datetime.now().isoformat(), uid),
            )
            conn.commit()
            conn.close()
        return self

    def get_node(self, uid: str) -> Optional[Dict]:
        if uid in self.graph:
            return dict(self.graph.nodes[uid])
        return None

    def delete_node(self, uid: str):
        if uid in self.graph:
            self.graph.remove_node(uid)
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM nodes WHERE uid=?", (uid,))
            conn.execute("DELETE FROM edges WHERE source_uid=? OR target_uid=?", (uid, uid))
            conn.commit()
            conn.close()

    # ── Edge CRUD ─────────────────────────────────────────────────────
    def add_edge(
        self,
        source_uid: str,
        target_uid: str,
        edge_type: str,
        weight: float = 0.5,
        evidence: str = "",
        tags: Optional[List[str]] = None,
    ) -> "ConceptGraph":
        assert edge_type in EDGE_TYPES, f"Invalid edge type '{edge_type}'. Must be one of {EDGE_TYPES}"
        # Auto-create nodes if they don't exist
        for uid in [source_uid, target_uid]:
            if uid not in self.graph:
                self.add_node(uid, label=uid.rsplit(":", 1)[-1], node_type="concept", source="auto-created")
        ts = datetime.now().isoformat()
        self.graph.add_edge(
            source_uid,
            target_uid,
            type=edge_type,
            weight=weight,
            evidence=evidence,
            timestamp=ts,
            tags=tags or [],
        )
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO edges
               (source_uid, target_uid, type, weight, evidence, timestamp, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (source_uid, target_uid, edge_type, weight, evidence, ts, json.dumps(tags or [])),
        )
        conn.commit()
        conn.close()
        return self

    def remove_edge(self, source_uid: str, target_uid: str, edge_type: str):
        if self.graph.has_edge(source_uid, target_uid):
            data = self.graph[source_uid][target_uid]
            if data.get("type") == edge_type:
                self.graph.remove_edge(source_uid, target_uid)
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    "DELETE FROM edges WHERE source_uid=? AND target_uid=? AND type=?",
                    (source_uid, target_uid, edge_type),
                )
                conn.commit()
                conn.close()

    # ── Queries ───────────────────────────────────────────────────────
    def supports(self, target_uid: str) -> List[Tuple[str, Dict]]:
        """Return all nodes that SUPPORTS the target."""
        return [(s, dict(d)) for s, _, d in self.graph.in_edges(target_uid, data=True) if d.get("type") == "SUPPORTS"]

    def contradicts(self, target_uid: str) -> List[Tuple[str, Dict]]:
        return [(s, dict(d)) for s, _, d in self.graph.in_edges(target_uid, data=True) if d.get("type") == "CONTRADICTS"]

    def enables(self, target_uid: str) -> List[Tuple[str, Dict]]:
        return [(s, dict(d)) for s, _, d in self.graph.in_edges(target_uid, data=True) if d.get("type") == "ENABLES"]

    def depends_on(self, source_uid: str) -> List[Tuple[str, Dict]]:
        return [(t, dict(d)) for _, t, d in self.graph.out_edges(source_uid, data=True) if d.get("type") == "DEPENDS_ON"]

    def derived_from(self, source_uid: str) -> List[Tuple[str, Dict]]:
        return [(t, dict(d)) for _, t, d in self.graph.out_edges(source_uid, data=True) if d.get("type") == "DERIVED_FROM"]

    def validated_by(self, source_uid: str) -> List[Tuple[str, Dict]]:
        return [(t, dict(d)) for _, t, d in self.graph.out_edges(source_uid, data=True) if d.get("type") == "VALIDATED_BY"]

    def falsified_by(self, source_uid: str) -> List[Tuple[str, Dict]]:
        return [(t, dict(d)) for _, t, d in self.graph.out_edges(source_uid, data=True) if d.get("type") == "FALSIFIED_BY"]

    def neighbors_by_type(self, uid: str, edge_type: str, direction: str = "in") -> List[str]:
        """Neighbors connected by a specific edge type and direction."""
        result = []
        edges = self.graph.in_edges(uid, data=True) if direction == "in" else self.graph.out_edges(uid, data=True)
        for a, b, d in edges:
            if d.get("type") == edge_type:
                result.append(a if direction == "in" else b)
        return result

    def confidence_path(self, source_uid: str, target_uid: str, max_hops: int = 5) -> List[List[Dict]]:
        """Find paths between two nodes with cumulative confidence."""
        try:
            paths = list(nx.all_simple_paths(self.graph, source_uid, target_uid, cutoff=max_hops))
        except nx.NetworkXNoPath:
            return []
        results = []
        for path in paths:
            cumulative = 1.0
            edges_info = []
            for i in range(len(path) - 1):
                e = self.graph[path[i]][path[i + 1]]
                w = e.get("weight", 0.5)
                cumulative *= w
                edges_info.append({"from": path[i], "to": path[i + 1], "type": e.get("type", ""), "weight": w})
            results.append({"path": path, "cumulative_confidence": round(cumulative, 4), "edges": edges_info})
        return sorted(results, key=lambda x: x["cumulative_confidence"], reverse=True)

    def contradiction_check(self, uid: str) -> List[str]:
        """List UIDs that both SUPPORTS and CONTRADICTS this node."""
        sup = set(s for s, _, d in self.graph.in_edges(uid, data=True) if d.get("type") == "SUPPORTS")
        con = set(s for s, _, d in self.graph.in_edges(uid, data=True) if d.get("type") == "CONTRADICTS")
        return list(sup & con)

    # ── Stats ─────────────────────────────────────────────────────────
    def stats(self) -> Dict:
        types = {}
        for _, d in self.graph.nodes(data=True):
            t = d.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        edge_types = {}
        for _, _, d in self.graph.edges(data=True):
            t = d.get("type", "unknown")
            edge_types[t] = edge_types.get(t, 0) + 1
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "node_types": types,
            "edge_types": edge_types,
            "density": round(nx.density(self.graph), 4),
        }

    def summary_text(self) -> str:
        s = self.stats()
        lines = [f"Concept Graph: {s['nodes']} nodes, {s['edges']} edges, density={s['density']}"]
        lines.append("Nodes:")
        for t, c in sorted(s["node_types"].items()):
            lines.append(f"  {t}: {c}")
        lines.append("Edges:")
        for t, c in sorted(s["edge_types"].items()):
            lines.append(f"  {t}: {c}")
        return "\n".join(lines)


# ── Quick demo / CLI ─────────────────────────────────────────────────
if __name__ == "__main__":
    cg = ConceptGraph()
    print(cg.summary_text())
