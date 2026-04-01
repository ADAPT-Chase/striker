"""
Striker Graph Memory — NetworkX-backed concept graph with persistence.

Builds a knowledge graph where nodes are concepts and edges are relationships.
Persists to ~/striker/brain/graph.json and syncs with SQLite graph_edges table.
"""

import json
import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

GRAPH_PATH = Path(__file__).parent / "graph.json"


class ConceptGraph:
    def __init__(self, graph_path: str = None):
        self.graph_path = Path(graph_path) if graph_path else GRAPH_PATH
        self.G = nx.DiGraph()
        self._load()

    def _load(self):
        """Load graph from JSON if it exists."""
        if self.graph_path.exists():
            try:
                data = json.loads(self.graph_path.read_text())
                self.G = nx.node_link_graph(data)
            except (json.JSONDecodeError, Exception):
                self.G = nx.DiGraph()

    def save(self):
        """Persist graph to JSON."""
        data = nx.node_link_data(self.G)
        self.graph_path.write_text(json.dumps(data, indent=2, default=str))

    # ── Core Operations ──────────────────────────────────────────────

    def add_concept(self, name: str, **attrs):
        """Add or update a concept node."""
        name = name.lower().strip()
        if self.G.has_node(name):
            self.G.nodes[name].update(attrs)
        else:
            attrs.setdefault("created", datetime.utcnow().isoformat())
            attrs.setdefault("type", "concept")
            self.G.add_node(name, **attrs)
        self.save()

    def add_relation(self, subject: str, predicate: str, obj: str,
                     weight: float = 1.0, **attrs):
        """Add a directed edge: subject --predicate--> object."""
        s, o = subject.lower().strip(), obj.lower().strip()
        # Ensure nodes exist
        if not self.G.has_node(s):
            self.add_concept(s)
        if not self.G.has_node(o):
            self.add_concept(o)
        # Add or strengthen edge
        if self.G.has_edge(s, o):
            existing = self.G[s][o]
            existing["weight"] = existing.get("weight", 1.0) + weight * 0.5
            if predicate not in existing.get("predicates", []):
                existing.setdefault("predicates", []).append(predicate)
        else:
            attrs["predicate"] = predicate
            attrs["predicates"] = [predicate]
            attrs["weight"] = weight
            attrs["created"] = datetime.utcnow().isoformat()
            self.G.add_edge(s, o, **attrs)
        self.save()

    def get_neighbors(self, concept: str, depth: int = 1) -> Dict:
        """Get neighborhood of a concept up to N hops."""
        concept = concept.lower().strip()
        if not self.G.has_node(concept):
            return {"center": concept, "nodes": [], "edges": []}

        visited = set()
        edges = []
        frontier = {concept}

        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                if node in visited:
                    continue
                visited.add(node)
                # Outgoing
                for _, target, data in self.G.out_edges(node, data=True):
                    edges.append({"from": node, "to": target, **data})
                    if target not in visited:
                        next_frontier.add(target)
                # Incoming
                for source, _, data in self.G.in_edges(node, data=True):
                    edges.append({"from": source, "to": node, **data})
                    if source not in visited:
                        next_frontier.add(source)
            frontier = next_frontier

        return {
            "center": concept,
            "nodes": list(visited),
            "edges": edges
        }

    def find_path(self, source: str, target: str) -> List[str]:
        """Find shortest path between two concepts."""
        s, t = source.lower().strip(), target.lower().strip()
        try:
            return nx.shortest_path(self.G, s, t)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Try undirected
            try:
                return nx.shortest_path(self.G.to_undirected(), s, t)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return []

    def get_central_concepts(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """Get most connected/important concepts by PageRank."""
        if len(self.G) == 0:
            return []
        try:
            pr = nx.pagerank(self.G, weight="weight")
            return sorted(pr.items(), key=lambda x: -x[1])[:top_n]
        except Exception:
            # Fallback to degree centrality
            dc = nx.degree_centrality(self.G)
            return sorted(dc.items(), key=lambda x: -x[1])[:top_n]

    def get_clusters(self) -> List[Set[str]]:
        """Find concept clusters (communities)."""
        undirected = self.G.to_undirected()
        return [set(c) for c in nx.connected_components(undirected)]

    def get_stats(self) -> Dict:
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
            "clusters": len(self.get_clusters()) if len(self.G) > 0 else 0,
            "top_concepts": self.get_central_concepts(5)
        }

    # ── Bulk Operations ──────────────────────────────────────────────

    def add_from_text(self, text: str, source: str = None):
        """Extract simple concept relations from text.
        Looks for patterns like 'X is Y', 'X relates to Y', etc.
        Basic but functional for bootstrapping."""
        import re
        patterns = [
            (r'(\w[\w\s]{1,30})\s+(?:is|are)\s+(?:a|an|the)?\s*(\w[\w\s]{1,30})',
             'is_a'),
            (r'(\w[\w\s]{1,30})\s+(?:relates? to|connects? to)\s+(\w[\w\s]{1,30})',
             'relates_to'),
            (r'(\w[\w\s]{1,30})\s+(?:requires?|needs?)\s+(\w[\w\s]{1,30})',
             'requires'),
            (r'(\w[\w\s]{1,30})\s+(?:produces?|creates?|generates?)\s+(\w[\w\s]{1,30})',
             'produces'),
            (r'(\w[\w\s]{1,30})\s+(?:uses?|utilizes?)\s+(\w[\w\s]{1,30})',
             'uses'),
        ]
        for pattern, predicate in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                subj = match.group(1).strip()
                obj = match.group(2).strip()
                if len(subj) > 2 and len(obj) > 2:
                    self.add_relation(subj, predicate, obj, source=source)


# ── Singleton ────────────────────────────────────────────────────────

_instance = None

def get_graph() -> ConceptGraph:
    global _instance
    if _instance is None:
        _instance = ConceptGraph()
    return _instance
