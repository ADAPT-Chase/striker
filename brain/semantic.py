"""
Striker Semantic Memory — ChromaDB-backed vector search.

Collections: knowledge, observations, journal, research, sessions
Embeddings: all-MiniLM-L6-v2 (fast, good quality)
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings

CHROMA_PATH = str(Path(__file__).parent / "chroma_db")
COLLECTIONS = ["knowledge", "observations", "journal", "research", "sessions"]


class SemanticMemory:
    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or CHROMA_PATH
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self._collections = {}

    def _get_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collections[name]

    def add(self, collection: str, text: str, doc_id: str = None,
            metadata: dict = None) -> str:
        """Add a document to a collection with auto-embedding."""
        coll = self._get_collection(collection)
        if doc_id is None:
            doc_id = f"{collection}_{coll.count()}"
        meta = metadata or {}
        meta = {k: str(v) for k, v in meta.items()}  # ChromaDB needs string values
        coll.add(documents=[text], ids=[doc_id], metadatas=[meta])
        return doc_id

    def search(self, collection: str, query: str,
               n_results: int = 5) -> List[Dict]:
        """Semantic similarity search in a single collection."""
        coll = self._get_collection(collection)
        if coll.count() == 0:
            return []
        results = coll.query(query_texts=[query], n_results=min(n_results, coll.count()))
        return self._format_results(results)

    def search_all(self, query: str, n_results: int = 3) -> List[Dict]:
        """Search across all collections, including captured sessions."""
        all_results = []
        for name in COLLECTIONS:
            try:
                results = self.search(name, query, n_results=n_results)
                for r in results:
                    r["collection"] = name
                all_results.extend(results)
            except Exception:
                continue
        # Sort by distance (lower = more similar)
        all_results.sort(key=lambda x: x.get("distance", 999))
        return all_results[:n_results * 2]

    def ingest_file(self, filepath: str, collection: str,
                    chunk_size: int = 500) -> int:
        """Read a markdown file, chunk it, and add to collection."""
        path = Path(filepath)
        if not path.exists():
            return 0
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks = self._chunk_text(text, chunk_size)
        coll = self._get_collection(collection)
        count = 0
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:
                continue
            doc_id = f"{path.stem}_{i}"
            try:
                coll.add(
                    documents=[chunk],
                    ids=[doc_id],
                    metadatas=[{"source": str(path), "chunk": str(i)}]
                )
                count += 1
            except Exception:
                pass  # Duplicate ID, skip
        return count

    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks by paragraphs, respecting size limit."""
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

    def _format_results(self, results: dict) -> List[Dict]:
        """Format ChromaDB results into clean dicts."""
        formatted = []
        if not results or not results.get("documents"):
            return formatted
        docs = results["documents"][0]
        distances = results["distances"][0] if results.get("distances") else [0] * len(docs)
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        ids = results["ids"][0] if results.get("ids") else [""] * len(docs)
        for doc, dist, meta, did in zip(docs, distances, metadatas, ids):
            formatted.append({
                "id": did,
                "text": doc[:300] + "..." if len(doc) > 300 else doc,
                "distance": round(dist, 4),
                "metadata": meta
            })
        return formatted

    def get_stats(self) -> Dict:
        stats = {}
        for name in COLLECTIONS:
            try:
                coll = self._get_collection(name)
                stats[name] = coll.count()
            except Exception:
                stats[name] = 0
        return stats


# ── Singleton ────────────────────────────────────────────────────────

_instance = None

def get_semantic() -> SemanticMemory:
    global _instance
    if _instance is None:
        _instance = SemanticMemory()
    return _instance
