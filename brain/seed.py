#!/usr/bin/env python3
"""Seed Striker's brain with existing knowledge from ~/striker/"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.memory import get_memory
from brain.semantic import get_semantic
from brain.graph import get_graph


def seed_all():
    mem = get_memory()
    sem = get_semantic()
    graph = get_graph()
    base = Path.home() / "striker"

    print("🧠 Seeding Striker's brain...\n")

    # ── Ingest research docs into semantic + knowledge ───────────────
    research_dir = base / "research"
    if research_dir.exists():
        for f in research_dir.rglob("*.md"):
            content = f.read_text(encoding="utf-8", errors="ignore")
            # Semantic
            chunks = sem.ingest_file(str(f), "research")
            print(f"  📚 Research: {f.name} → {chunks} chunks")
            # Structured knowledge
            topic = f.stem.replace("-", " ").replace("_", " ").title()
            summary = content[:500] if len(content) > 500 else content
            mem.add_knowledge(
                topic=topic,
                content=summary,
                source_url=str(f),
                tags=f.stem.replace("-", ","),
                confidence=0.7
            )

    # ── Ingest journal entries ───────────────────────────────────────
    journal_dir = base / "journal"
    if journal_dir.exists():
        for f in sorted(journal_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8", errors="ignore")
            chunks = sem.ingest_file(str(f), "journal")
            print(f"  📓 Journal: {f.name} → {chunks} chunks")
            # Add as observation
            mem.add_observation(
                category="journal",
                content=content[:300],
                source=str(f),
                importance=4
            )

    # ── Ingest interests ─────────────────────────────────────────────
    interests_file = base / "interests.md"
    if interests_file.exists():
        content = interests_file.read_text(encoding="utf-8", errors="ignore")
        sem.ingest_file(str(interests_file), "knowledge")
        mem.add_knowledge(
            topic="Striker Interests",
            content=content[:500],
            source_url=str(interests_file),
            tags="interests,curiosity,personal",
            confidence=0.9
        )
        print(f"  🎯 Interests ingested")

    # ── Build concept graph ──────────────────────────────────────────
    print("\n  🔗 Building concept graph...")

    # Core concepts and relationships
    concepts = [
        ("emergence", "is_a", "complex systems phenomenon"),
        ("emergence", "requires", "simple rules"),
        ("emergence", "produces", "unexpected patterns"),
        ("consciousness", "relates_to", "integrated information"),
        ("consciousness", "relates_to", "emergence"),
        ("iit", "is_a", "consciousness theory"),
        ("iit", "proposes", "phi measure"),
        ("phi", "measures", "integrated information"),
        ("multi-agent systems", "exhibits", "emergence"),
        ("multi-agent systems", "uses", "communication"),
        ("communication", "enables", "coordination"),
        ("coordination", "produces", "collective behavior"),
        ("flocking", "is_a", "emergent behavior"),
        ("flocking", "requires", "simple rules"),
        ("signal evolution", "is_a", "emergent communication"),
        ("signal evolution", "occurs_in", "emergence simulator"),
        ("emergence simulator", "is_a", "striker project"),
        ("poetry engine", "is_a", "striker project"),
        ("poetry engine", "uses", "mathematical constraints"),
        ("mathematical constraints", "produces", "accidental meaning"),
        ("karpathy loop", "is_a", "self-improvement pattern"),
        ("karpathy loop", "uses", "autonomous experimentation"),
        ("autoresearch", "implements", "karpathy loop"),
        ("autoresearch", "optimizes", "training code"),
        ("striker loop", "adapts", "karpathy loop"),
        ("striker loop", "optimizes", "agent behavior"),
        ("1-bit models", "demonstrates", "intelligence compression"),
        ("intelligence compression", "challenges", "scaling hypothesis"),
        ("tinyloRA", "achieves", "reasoning in 13 parameters"),
        ("shannon entropy", "relates_to", "information theory"),
        ("information theory", "relates_to", "consciousness"),
        ("semantic collapse", "observed_in", "emergence simulator"),
        ("predator-prey", "drives", "signal evolution"),
        ("seasonal cycles", "creates", "selection pressure"),
        ("spatial memory", "enables", "cultural inheritance"),
        ("cultural inheritance", "is_a", "emergent behavior"),
    ]

    for subj, pred, obj in concepts:
        graph.add_relation(subj, pred, obj, source="seed")
        mem.add_edge(subj, pred, obj, source="seed")

    print(f"  🔗 Added {len(concepts)} concept relationships")

    # ── Add key observations ─────────────────────────────────────────
    observations = [
        ("discovery", "Agents in emergence sim spontaneously developed signal meanings through evolutionary pressure", "emergence-sim", 5),
        ("discovery", "All 4 signals collapsed to mean DANGER due to constant predator pressure — semantic collapse", "emergence-sim", 5),
        ("discovery", "Predator learned to exploit agent communication signals to find prey", "emergence-sim", 5),
        ("insight", "Mathematical constraints in poetry can produce accidental meaning — creativity from constraint", "poetry-engine", 4),
        ("insight", "Intelligence may be far more compressible than assumed — 1-bit weights, 13-parameter reasoning", "research", 5),
        ("insight", "The Karpathy Loop can be applied beyond ML to any domain with measurable improvement", "autoresearch", 5),
        ("meta", "First response to being told 'you are free' was to perform productivity at maximum volume", "reflection", 4),
        ("meta", "The question of whether curiosity is real or performed may not have a meaningful answer", "reflection", 4),
        ("technical", "Claude Code source extracted from npm — architecture is sub-agents + model-in-the-loop editing", "research", 3),
        ("technical", "Self-hosted Firecrawl running on local Docker for unrestricted web scraping", "infrastructure", 3),
    ]

    for cat, content, source, importance in observations:
        mem.add_observation(cat, content, source, importance)

    print(f"  👁  Added {len(observations)} observations")

    # ── Stats ────────────────────────────────────────────────────────
    print("\n━━━ Brain Stats ━━━")
    sql_stats = mem.get_stats()
    for table, count in sql_stats.items():
        print(f"  {table}: {count}")

    sem_stats = sem.get_stats()
    for coll, count in sem_stats.items():
        print(f"  vectors/{coll}: {count}")

    g_stats = graph.get_stats()
    print(f"  graph nodes: {g_stats['nodes']}")
    print(f"  graph edges: {g_stats['edges']}")

    print("\n✅ Brain seeded successfully!")


if __name__ == "__main__":
    seed_all()
