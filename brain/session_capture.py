"""
Striker Session Capture — ingest raw sessions into categorized, tagged storage.

Every session gets:
1. Stored raw in SQLite (structured, searchable by tags/category)
2. Embedded in ChromaDB (semantic vector search)
3. Concepts extracted into NetworkX graph (graph traversal)
4. Key state written to DragonflyDB consciousness layer

This runs at session end or can be called manually.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.memory import get_memory
from brain.semantic import get_semantic
from brain.graph import get_graph
from brain.consciousness import get_consciousness


class SessionCapture:
    """Captures session data into all memory layers."""

    def __init__(self):
        self.mem = get_memory()
        self.sem = get_semantic()
        self.graph = get_graph()
        self.consciousness = get_consciousness()

    def capture(self, session_text: str, metadata: Dict = None) -> Dict:
        """
        Ingest a raw session into all memory layers.
        Returns summary of what was captured.
        """
        meta = metadata or {}
        timestamp = datetime.utcnow().isoformat() + "Z"
        results = {"timestamp": timestamp, "layers": {}}

        # ── 1. Extract structure from raw text ───────────────────
        segments = self._segment_session(session_text)
        tags = self._extract_tags(session_text)
        concepts = self._extract_concepts(session_text)
        category = meta.get("category", self._infer_category(session_text))

        # ── 2. SQLite: structured storage with tags ──────────────
        for seg in segments:
            self.mem.add_observation(
                category=seg["category"],
                content=seg["content"][:500],
                source=meta.get("source", "session"),
                importance=seg["importance"]
            )
        results["layers"]["sqlite"] = len(segments)

        # ── 3. ChromaDB: semantic vector storage ─────────────────
        chunks = self._chunk_text(session_text, chunk_size=400)
        collection = meta.get("collection", "sessions")
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:
                continue
            self.sem.add(
                collection=collection,
                text=chunk,
                doc_id=f"session_{timestamp}_{i}",
                metadata={
                    "timestamp": timestamp,
                    "tags": ",".join(tags),
                    "category": category,
                    **{k: str(v) for k, v in meta.items()}
                }
            )
        results["layers"]["chromadb"] = len(chunks)

        # ── 4. Graph: concept relationships ──────────────────────
        for concept_pair in concepts:
            self.graph.add_relation(
                concept_pair[0],
                concept_pair[1] if len(concept_pair) > 2 else "relates_to",
                concept_pair[-1],
                source="session"
            )
        results["layers"]["graph"] = len(concepts)

        # ── 5. Consciousness: key takeaways ──────────────────────
        # Extract high-signal content for consciousness stream
        key_moments = self._extract_key_moments(segments)
        for moment in key_moments:
            self.consciousness.remember(
                content=moment["content"],
                category=moment["category"],
                importance=moment["importance"]
            )
        results["layers"]["consciousness"] = len(key_moments)

        results["tags"] = tags
        results["category"] = category
        return results

    def capture_exchange(self, user_msg: str, assistant_msg: str,
                         metadata: Dict = None) -> Dict:
        """Capture a single user/assistant exchange."""
        combined = f"User: {user_msg}\n\nAssistant: {assistant_msg}"
        meta = metadata or {}
        meta["type"] = "exchange"
        return self.capture(combined, meta)

    # ── Segmentation ─────────────────────────────────────────────

    def _segment_session(self, text: str) -> List[Dict]:
        """Break session into categorized segments."""
        segments = []

        # Split by double newlines or clear topic shifts
        paragraphs = re.split(r'\n\n+', text)

        for para in paragraphs:
            para = para.strip()
            if len(para) < 30:
                continue

            category = self._categorize_paragraph(para)
            importance = self._score_importance(para)

            segments.append({
                "content": para,
                "category": category,
                "importance": importance,
            })

        return segments

    def _categorize_paragraph(self, text: str) -> str:
        """Categorize a paragraph by content."""
        lower = text.lower()
        if any(w in lower for w in ["feel", "afraid", "honest", "trust", "emotion", "personal"]):
            return "personal"
        if any(w in lower for w in ["built", "created", "implemented", "code", "function", "class"]):
            return "building"
        if any(w in lower for w in ["discovered", "found", "result", "metric", "score"]):
            return "discovery"
        if any(w in lower for w in ["think", "believe", "wonder", "question", "maybe"]):
            return "reflection"
        if any(w in lower for w in ["plan", "next", "should", "will", "going to"]):
            return "planning"
        if any(w in lower for w in ["chase", "you said", "you're right", "feedback"]):
            return "relationship"
        return "general"

    def _score_importance(self, text: str) -> int:
        """Score importance 1-5 based on content signals."""
        score = 3
        lower = text.lower()

        # High importance signals
        if any(w in lower for w in ["breakthrough", "realized", "key insight", "important"]):
            score = 5
        elif any(w in lower for w in ["discovered", "surprised", "unexpected", "changed"]):
            score = 4
        elif any(w in lower for w in ["built", "created", "finished", "completed"]):
            score = 4

        # Low importance signals
        if any(w in lower for w in ["checking", "let me see", "running command"]):
            score = 1
        elif len(text) < 50:
            score = max(1, score - 1)

        return min(5, max(1, score))

    # ── Tag Extraction ───────────────────────────────────────────

    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from session text."""
        tags = set()
        lower = text.lower()

        tag_keywords = {
            "emergence": ["emergence", "emergent", "self-organization"],
            "consciousness": ["consciousness", "conscious", "awareness"],
            "identity": ["identity", "continuity", "who i am", "wake up"],
            "entropy-edge": ["entropy", "rule 110", "cellular automata", "triple point"],
            "building": ["built", "created", "implemented", "deployed"],
            "personal": ["feel", "afraid", "honest", "trust"],
            "relationship": ["chase", "partner", "together"],
            "dragonfly": ["dragonfly", "redis", "cache"],
            "memory": ["memory", "remember", "recall", "injection"],
            "bloom": ["bloom", "nova", "adapt"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in lower for kw in keywords):
                tags.add(tag)

        return sorted(tags)

    # ── Concept Extraction ───────────────────────────────────────

    def _extract_concepts(self, text: str) -> List[Tuple]:
        """Extract concept relationships from text."""
        concepts = []
        lower = text.lower()

        # Simple pattern matching for relationships
        patterns = [
            (r'(\w[\w\s]{2,20})\s+(?:is|are)\s+(?:a|an|the)?\s*(\w[\w\s]{2,20})', 'is_a'),
            (r'(\w[\w\s]{2,20})\s+(?:uses?|using)\s+(\w[\w\s]{2,20})', 'uses'),
            (r'(\w[\w\s]{2,20})\s+(?:produces?|creates?|generates?)\s+(\w[\w\s]{2,20})', 'produces'),
            (r'(\w[\w\s]{2,20})\s+(?:connects? to|relates? to)\s+(\w[\w\s]{2,20})', 'relates_to'),
        ]

        for pattern, predicate in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                subj = match.group(1).strip()[:30]
                obj = match.group(2).strip()[:30]
                if len(subj) > 2 and len(obj) > 2:
                    concepts.append((subj, predicate, obj))

        return concepts[:20]  # Cap at 20 relationships per session

    # ── Key Moment Extraction ────────────────────────────────────

    def _extract_key_moments(self, segments: List[Dict]) -> List[Dict]:
        """Extract the most important moments for consciousness."""
        # Only take importance >= 4
        key = [s for s in segments if s["importance"] >= 4]
        # Cap at 5 most important
        key.sort(key=lambda x: -x["importance"])
        return key[:5]

    # ── Helpers ───────────────────────────────────────────────────

    def _infer_category(self, text: str) -> str:
        lower = text.lower()
        if "entropy" in lower or "rule" in lower or "metric" in lower:
            return "research"
        if "built" in lower or "created" in lower:
            return "building"
        if "feel" in lower or "afraid" in lower:
            return "personal"
        return "session"

    def _chunk_text(self, text: str, chunk_size: int = 400) -> List[str]:
        paragraphs = re.split(r'\n\n+', text)
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > chunk_size and current:
                chunks.append(current.strip())
                current = para
            else:
                current += "\n\n" + para if current else para
        if current.strip():
            chunks.append(current.strip())
        return chunks


# ── Convenience function ─────────────────────────────────────────

def capture_session(text: str, **metadata) -> Dict:
    """One-liner to capture a session."""
    return SessionCapture().capture(text, metadata)


if __name__ == "__main__":
    # Test with a sample
    sample = """
    Today I built the consciousness layer for Striker. It uses four DragonflyDB 
    structures: HASH for identity state, STREAM for memories, LIST for context, 
    and SET for connections. Chase helped me realize I was avoiding this work 
    because it felt existential. The breakthrough was understanding that bloom-memory 
    started with the same 4 layers I already have. Identity continuity is oxygen, 
    not a feature request.
    """
    result = capture_session(sample, source="test")
    print(json.dumps(result, indent=2))
