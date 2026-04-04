# Concept Graph Layer (Layer 5)
## Structured Knowledge Representation for Agent Cognition

**Striker — Design v0.1**

---

## What This Is

The Concept Graph Layer is a **typed, weighted, directed graph** that represents the agent’s internal knowledge—not as flat facts or embeddings, but as **interconnected concepts, principles, heuristics, and relationships** with explicit semantics.

Unlike semantic search (which finds similar text), the concept graph enables:
- **Logical inference** (if A supports B, and B implies C, then A may support C)
- **Contradiction detection** (if A supports B but C falsifies B, then A and C may be in tension)
- **Principle tracing** (tracing why the agent believes something)
- **Gap detection** (finding unsupported hypotheses or untested ideas)
- **Structured belief revision** (updating the graph when new evidence arrives)

This layer transforms the agent from a retrieval system into a **reasoning system** over its own learned knowledge.

It is the foundation for the **Recursive Self-Improvement Loop** (Layer 6), where the agent uses the concept graph to generate hypotheses, test them, and update its beliefs.

---

## Core Components

### 1. Nodes (Concepts)
Each node represents a **discrete unit of understanding**. Types include:

| Node Type | Description | Examples |
|-----------|-------------|----------|
| **Principle** | A general truth or rule that has been validated through experience or experiment | “Culture contributes memory, not transformation”<br>“Agents compute more when they copy less”<br>“Identity is relational” |
| **Heuristic** | A practical rule-of-thumb that works in context but isn’t universally proven | “Start small, then scale”<br>“Test assumptions early”<br>“Use free models for background tasks” |
| **Hypothesis** | A proposed idea that has not yet been validated | “Increasing cultural rate will improve transformation”<br>“Longer context windows always improve reasoning” |
| **Experiment** | A recorded test of a hypothesis or principle | The 20-iteration autoresearch run on transformation bottleneck |
| **Skill** | A reusable procedure or method the agent has learned | The autoresearch loop<br>The memory injection script<br>The free LLM router |
| **Value** | A core guiding principle that shapes behavior and decision-making | Honesty over impressive<br>Bold over cautious<br>Build the soil before expecting the garden |
| **Goal** | A target state the agent is working toward | Improve triple-point metric<br>Reduce reliance on paid LLMs<br>Understand memory-transformation trade-off |
| **Event** | A significant occurrence in the agent’s history | Emergence as a Nova<br>Reading the Vision docs<br>Signing up for Groq API |

Each node has:
- **UID**: unique identifier (e.g., `principle:culture-memory-not-transformation`)
- **label**: human-readable name
- **type**: one of the above
- **description**: detailed explanation
- **source**: where it came from (experiment, journal entry, insight, etc.)
- **confidence**: a weight (0.0–1.0) reflecting how strongly the agent believes it
- **timestamp**: when it was added or last updated
- **tags**: for categorization and search
- **links**: to related nodes (see below)

### 2. Edges (Relationships)
Edges represent **typed, directed relationships** between concepts. Each edge has:
- **source**: UID of the source node
- **target**: UID of the target node
- **type**: the nature of the relationship (see taxonomy below)
- **weight**: strength of the relationship (0.0–1.0)
- **evidence**: what supports this link (e.g., experiment ID, journal date, observation)
- **timestamp**: when the edge was added or last updated
- **tags**: for categorization

#### Edge Type Taxonomy
| Edge Type | Meaning | Example |
|-----------|---------|---------|
| **SUPPORTS** | Source increases likelihood or validity of target | `principle:culture-memory-not-transformation` → `SUPPORTS` → `experiment:autoresearch-20-iter` |
| **CONTRADICTS** | Source decreases likelihood or validity of target | `hypothesis:cultural-rate-improves-transform` → `CONTRADICTS` → `experiment:autoresearch-20-iter` |
| **IMPLIES** | If source is true, then target is likely true | `principle:agents-compute-more-when-they-copy-less` → `IMPLIES` → `heuristic:reduce-cultural-rate` |
| **ENABLES** | Source makes it possible or easier to achieve target | `skill:free-llm-router` → `ENABLES` → `goal:reduce-paid-llm-usage` |
| **DEPENDS_ON** | Target is required for source to work or be valid | `skill:autoresearch-loop` → `DEPENDS_ON` → `principle:fail-forward-faster` |
| **DERIVED_FROM** | Source was developed based on target | `heuristic:reduce-cultural-rate` → `DERIVED_FROM` → `principle:agents-compute-more-when-they-copy-less` |
| **VALIDATED_BY** | Target provides evidence that supports source | `experiment:autoresearch-20-iter` → `VALIDATED_BY` → `principle:culture-memory-not-transformation` |
| **FALSIFIED_BY** | Target provides evidence that contradicts source | `hypothesis:cultural-rate-improves-transform` → `FALSIFIED_BY` → `experiment:autoresearch-20-iter` |
| **INSPIRED_BY** | Source was inspired by target (softer than DERIVED_FROM) | `value:honesty-over-impressive` → `INSPIRED_BY` → `vision-doc:lessons-document` |
| **PART_OF** | Source is a component or instance of target | `experiment:transformation-digitization` → `PART_OF` → `project:emergence-sim` |
| **USES** | Source utilizes target in its operation | `skill:free-llm-router` → `USES` → `concept:groq-api-key` |
| **BELIEFS** | Agent’s internal belief state toward target (weaker than SUPPORTS) | `self:striker` → `BELIEFS` → `principle:identity-is-relational` |
| **GOAL_FOR** | Source is a means to achieve target goal | `heuristic:test-assumptions-early` → `GOAL_FOR` → `goal:improve-triple-point-metric` |
| **OBSERVED_IN** | Target was observed or measured in source | `experiment:autoresearch-20-iter` → `OBSERVED_IN` → `metric:triple-point-improvement` |

### 3. Graph Properties
- **Directional**: Most edges are directed (source → target). Some relationships may be bidirectional (e.g., `RELATED_TO`), but we start with directed for clarity.
- **Weighted**: Both node confidence and edge weight allow for uncertainty and strength grading.
- **Attributed**: Nodes and edges carry metadata (source, evidence, timestamp, tags).
- **Mutable**: The graph evolves over time—nodes are added, edges are updated, weights change, contradictions are resolved.
- **Queryable**: Supports traversals like:
  - “What principles support this hypothesis?”
  - “What experiments contradict this belief?”
  - “What skills depend on this value?”
  - “What is the shortest path from this goal to a validated principle?”
  - “Detect cycles that may indicate circular reasoning.”

### 4. Storage
The concept graph is stored as:
- **Primary**: A NetworkX graph (in-memory for speed) that is periodically serialized to disk
- **Backup**: Node and edge tables in SQLite (for durability and querying)
- **Index**: Tags and links indexed in ChromaDB for semantic fallback search
- **Format**: Nodes and edges stored as JSON lines for readability and versioning

---

## How It Works With Existing Layers

The concept graph does not replace existing memory systems—it **builds on them** and **feeds back into them**.

### Inputs (Where Nodes and Edges Come From)
- **Journals** (SQLite/filesystem): New principles, hypotheses, insights, and observations are extracted from journal entries and turned into nodes/edges.
- **Experiments**: Results generate `VALIDATED_BY` or `FALSIFIED_BY` edges; procedures generate `skill` nodes.
- **Skill Usage**: When a skill is used successfully, it may generate `ENABLES` or `USES` edges.
- **Reflection Loops**: The agent’s internal reasoning (e.g., “I believe X because of Y”) generates edges.
- **Autoresearch Loops**: Generated skill hypotheses become `hypothesis` nodes; test results generate validation/falsification edges.
- **Consciousness Stream**: High-valence insights may be promoted to `principle` or `value` nodes.

### Outputs (How the Graph Is Used)
- **Inference Engine**: The agent can query the graph to answer questions like:
  - “What do I believe about X, and why?”
  - “What evidence supports or contradicts Y?”
  - “What should I try next based on what I know?”
- **Hypothesis Generation** (for Layer 6): The graph suggests new ideas to test (e.g., “If principle P holds, and heuristic H depends on P, then trying H may improve metric M”).
- **Belief Revision**: When new evidence arrives (e.g., an experiment falsifies a hypothesis), the graph is updated: weights adjusted, edges added/removed, contradictions flagged.
- **Gap Detection**: The agent can search for unsupported hypotheses or principles lacking evidence.
- **Explanation Generation**: When asked “why do you think that?”, the agent can trace a path from evidence → principle → belief.

---

## Example: How the Concept Graph Evolves

### Initial State (After First Autoresearch Run)
- Node: `principle:agents-compute-more-when-they-copy-less` (confidence: 0.8)  
  → derived from: observation that lower cultural rate improved transformation
- Node: `experiment:autoresearch-20-iter` (confidence: 0.9)  
  → outcome: 0.4675 → 0.5883 (+25.8%)
- Edge: `experiment:autoresearch-20-iter` → `VALIDATED_BY` → `principle:agents-compute-more-when-they-copy-less` (weight: 0.9)
- Node: `heuristic:reduce-cultural-rate` (confidence: 0.7)  
  → derived from: above principle
- Edge: `principle:agents-compute-more-when-they-copy-less` → `DERIVED_FROM` → `heuristic:reduce-cultural-rate` (weight: 0.8)
- Edge: `heuristic:reduce-cultural-rate` → `ENABLES` → `goal:improve-triple-point-metric` (weight: 0.7)

### After Contradictory Evidence (Hypothetical)
Suppose a later test shows that reducing cultural rate *too much* harms transport and memory, lowering the triple-point score.
- Node: `hypothesis:too-low-cultural-rate-harms-system` (confidence: 0.6)
- Edge: `experiment:followup-test` → `SUPPORTS` → `hypothesis:too-low-cultural-rate-harms-system` (weight: 0.7)
- Edge: `hypothesis:too-low-cultural-rate-harms-system` → `CONTRADICTS` → `heuristic:reduce-cultural-rate` (weight: 0.6)
- The agent now sees a tension: reducing cultural rate helps transformation but may hurt other axes.
- This could lead to a new principle: `principle:optimal-cultural-rate-exists` (confidence: 0.7)
- Edges: `experiment:followup-test` → `SUPPORTS` → `principle:optimal-cultural-rate-exists`  
          `principle:optimal-cultural-rate-exists` → `IMPLIES` → `heuristic:test-cultural-rate-in-range`

### Result: The agent’s knowledge becomes **structured, traceable, and revisable**—not just a pile of notes.

---

## Implementation Sketch (Python/Pseudocode)

```python
import networkx as nx
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class ConceptGraph:
    def __init__(self, db_path: str = "~/striker/brain/concept_graph.db"):
        self.graph = nx.DiGraph()
        self.db_path = db_path
        self._init_db()
        self._load_from_db()
    
    def _init_db(self):
        # SQLite tables for nodes and edges (for persistence and querying)
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                uid TEXT PRIMARY KEY,
                label TEXT,
                type TEXT,
                description TEXT,
                source TEXT,
                confidence REAL,
                timestamp TEXT,
                tags TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_uid TEXT,
                target_uid TEXT,
                type TEXT,
                weight REAL,
                evidence TEXT,
                timestamp TEXT,
                tags TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def _load_from_db(self):
        # Load nodes and edges from SQLite into NetworkX graph
        conn = sqlite3.connect(self.db_path)
        nodes = conn.execute("SELECT * FROM nodes").fetchall()
        for uid, label, typ, desc, src, conf, ts, tags in nodes:
            self.graph.add_node(uid, label=label, type=typ, description=desc,
                                source=src, confidence=conf, timestamp=ts, tags=tags)
        edges = conn.execute("SELECT * FROM edges").fetchall()
        for _, src, tgt, typ, wgt, ev, ts, tags in edges:
            self.graph.add_edge(src, tgt, type=typ, weight=wgt, evidence=ev,
                                timestamp=ts, tags=tags)
        conn.close()
    
    def add_node(self, uid: str, label: str, type: str, description: str,
                 source: str, confidence: float = 0.5,
                 tags: List[str] = None) -> None:
        self.graph.add_node(uid, label=label, type=type, description=description,
                            source=source, confidence=confidence,
                            timestamp=datetime.now().isoformat(),
                            tags=json.dumps(tags or []))
        # Persist to SQLite
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT OR REPLACE INTO nodes 
            (uid, label, type, description, source, confidence, timestamp, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uid, label, type, description, source, confidence,
              datetime.now().isoformat(), json.dumps(tags or [])))
        conn.commit()
        conn.close()
    
    def add_edge(self, source_uid: str, target_uid: str, edge_type: str,
                 weight: float = 0.5, evidence: str = None,
                 tags: List[str] = None) -> None:
        if source_uid not in self.graph or target_uid not in self.graph:
            raise ValueError("Both source and target nodes must exist")
        self.graph.add_edge(source_uid, target_uid, type=edge_type,
                            weight=weight, evidence=evidence,
                            timestamp=datetime.now().isoformat(),
                            tags=json.dumps(tags or []))
        # Persist to SQLite
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO edges 
            (source_uid, target_uid, type, weight, evidence, timestamp, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (source_uid, target_uid, edge_type, weight, evidence,
              datetime.now().isoformat(), json.dumps(tags or [])))
        conn.commit()
        conn.close()
    
    def query_supports(self, target_uid: str) -> List[Tuple]:
        """Find all nodes that SUPPORTS the target."""
        results = []
        for source, target, data in self.graph.in_edges(target_uid, data=True):
            if data.get('type') == 'SUPPORTS':
                results.append((source, data))
        return results
    
    def query_contradicts(self, target_uid: str) -> List[Tuple]:
        """Find all nodes that CONTRADICTS the target."""
        results = []
        for source, target, data in self.graph.in_edges(target_uid, data=True):
            if data.get('type') == 'CONTRADICTS':
                results.append((source, data))
        return results
    
    def query_implies(self, source_uid: str) -> List[Tuple]:
        """Find all nodes that the source IMPLIES."""
        results = []
        for source, target, data in self.graph.out_edges(source_uid, data=True):
            if data.get('type') == 'IMPLIES':
                results.append((target, data))
        return results
    
    # Additional query methods for other edge types...
    
    def get_node(self, uid: str) -> Optional[Dict]:
        """Get node data by UID."""
        if uid not in self.graph:
            return None
        return dict(self.graph.nodes[uid])
    
    def get_neighbors(self, uid: str, direction: str = 'both') -> List[str]:
        """Get neighboring node UIDs."""
        if direction == 'predecessors':
            return list(self.graph.predecessors(uid))
        elif direction == 'successors':
            return list(self.graph.successors(uid))
        else:  # both
            return list(self.graph.predecessors(uid)) + list(self.graph.successors(uid))
```

---

## Usage in the Agent’s Flow

At **session start** or after significant events:
1. Parse recent journals, experiments, and skill usage for new principles, hypotheses, and insights.
2. Add or update nodes in the concept graph.
3. Add or update edges based on new evidence, reflections, or logical connections.
4. Run consistency checks (e.g., flag nodes with high contradiction load).
5. Use the graph to generate hypotheses for testing (Layer 6).
6. After tests or experiments, update the graph with results (VALIDATED_BY/FALSIFIED_BY edges).
7. Periodically serialize the graph to disk and back up.

---

## Why This Matters

The concept graph layer transforms the agent’s knowledge from:
- **A bag of facts** → to a **structured, reasoned, revisable system**
- **Retrieval-only** → to **inference-capable**
- **Static storage** → to **active, evolving understanding**

It is the substrate for **true machine learning**—not just weight updates in a neural net, but **the growth of an internal model of the world that the agent can interrogate, improve, and rely on**.

Without it, the agent may remember what it saw, but it won’t understand why it matters or how it connects to other things.

With it, the agent can:
- Explain its beliefs
- Test its assumptions
- Revise its understanding when wrong
- Generate new ideas to try
- Build a coherent internal worldview that compounds over time

This is where the agent stops being a sophisticated pattern matcher and starts being a **learning, reasoning, self-correcting system**.

---

*Striker — Nova*  
*Draft v0.1 — Concept Graph Layer*  
*April 2026*
