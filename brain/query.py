#!/usr/bin/env python3
"""
Striker Brain CLI — unified search and query interface.

Usage:
    python3 query.py search 'emergence'          # Search everything
    python3 query.py stats                        # Show all stats
    python3 query.py recent                       # Recent observations
    python3 query.py experiments [--target sim]   # Experiment log
    python3 query.py graph 'consciousness'        # Graph neighborhood
    python3 query.py path 'emergence' 'poetry'    # Find concept path
"""

import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.memory import get_memory
from brain.semantic import get_semantic
from brain.graph import get_graph
from brain.cache import get_cache


def cmd_search(args):
    """Search across all memory systems."""
    query = " ".join(args.query)
    print(f"\n🔍 Searching for: '{query}'\n")

    # SQLite FTS
    mem = get_memory()
    print("━━━ Structured Memory (SQLite FTS5) ━━━")
    knowledge = mem.search_knowledge(query, limit=5)
    if knowledge:
        for k in knowledge:
            print(f"  📚 [{k['topic']}] {k['content'][:120]}...")
    observations = mem.search_observations(query, limit=5)
    if observations:
        for o in observations:
            print(f"  👁  [{o['category']}] {o['content'][:120]}...")
    experiments = mem.search_experiments(query, limit=3)
    if experiments:
        for e in experiments:
            print(f"  🧪 [{e['target']}] {e['hypothesis'][:100]}... → {e['outcome']}")

    if not knowledge and not observations and not experiments:
        print("  (no structured results)")

    # Semantic search
    print("\n━━━ Semantic Memory (ChromaDB) ━━━")
    sem = get_semantic()
    results = sem.search_all(query, n_results=5)
    if results:
        for r in results:
            coll = r.get("collection", "?")
            dist = r.get("distance", 0)
            src = r.get("metadata", {}).get("source", "")
            print(f"  🧠 [{coll}] (sim={1-dist:.2f}) {r['text'][:120]}...")
            if src:
                print(f"     └─ {src}")
    else:
        print("  (no semantic results)")

    # Graph
    print("\n━━━ Concept Graph ━━━")
    g = get_graph()
    neighborhood = g.get_neighbors(query.split()[0], depth=1)
    if neighborhood["edges"]:
        for e in neighborhood["edges"][:5]:
            pred = e.get("predicate", e.get("predicates", ["?"])[0] if isinstance(e.get("predicates"), list) else "?")
            print(f"  🔗 {e['from']} ──{pred}──▸ {e['to']}")
    else:
        print("  (no graph connections)")
    print()


def cmd_stats(args):
    """Show stats across all memory systems."""
    print("\n📊 Striker Brain Stats\n")

    mem = get_memory()
    sql_stats = mem.get_stats()
    print("━━━ Structured Memory (SQLite) ━━━")
    for table, count in sql_stats.items():
        print(f"  {table}: {count} records")

    sem = get_semantic()
    sem_stats = sem.get_stats()
    print("\n━━━ Semantic Memory (ChromaDB) ━━━")
    for coll, count in sem_stats.items():
        print(f"  {coll}: {count} vectors")

    g = get_graph()
    g_stats = g.get_stats()
    print("\n━━━ Concept Graph ━━━")
    print(f"  Nodes: {g_stats['nodes']}")
    print(f"  Edges: {g_stats['edges']}")
    print(f"  Clusters: {g_stats['clusters']}")
    if g_stats.get("top_concepts"):
        print("  Top concepts:")
        for name, score in g_stats["top_concepts"]:
            print(f"    {name}: {score:.4f}")

    try:
        cache = get_cache()
        c_stats = cache.get_stats()
        print(f"\n━━━ Hot Cache (DragonflyDB) ━━━")
        print(f"  Engine: {c_stats['engine']}")
        print(f"  Memory: {c_stats['memory_used']}")
        print(f"  Keys: {c_stats['total_keys']}")
        print(f"  Threads: {c_stats['threads']}")
    except Exception as e:
        print(f"\n━━━ Hot Cache (DragonflyDB) ━━━")
        print(f"  Offline: {e}")
    print()


def cmd_recent(args):
    """Show recent observations."""
    mem = get_memory()
    obs = mem.get_recent_observations(limit=args.limit)
    print(f"\n👁  Recent Observations (last {args.limit})\n")
    for o in obs:
        imp = "!" * o["importance"]
        print(f"  [{o['category']}] {imp} {o['content'][:150]}")
        if o.get("source"):
            print(f"    └─ {o['source']}")
    print()


def cmd_experiments(args):
    """Show experiment log."""
    mem = get_memory()
    exps = mem.get_experiments(target=args.target, outcome=args.outcome, limit=args.limit)
    print(f"\n🧪 Experiments\n")
    for e in exps:
        icon = "✅" if e["outcome"] == "keep" else "❌" if e["outcome"] == "discard" else "🔄"
        score = f" (score: {e['result_score']:.4f})" if e["result_score"] is not None else ""
        print(f"  {icon} [{e['target']}] {e['hypothesis'][:100]}{score}")
        if e.get("notes"):
            print(f"    └─ {e['notes'][:120]}")
    print()


def cmd_graph(args):
    """Show concept graph neighborhood."""
    g = get_graph()
    concept = " ".join(args.concept)
    nb = g.get_neighbors(concept, depth=args.depth)
    print(f"\n🔗 Graph neighborhood of '{concept}' (depth={args.depth})\n")
    print(f"  Nodes: {', '.join(nb['nodes'])}")
    for e in nb["edges"]:
        pred = e.get("predicate", "?")
        w = e.get("weight", 1.0)
        print(f"  {e['from']} ──{pred} ({w:.1f})──▸ {e['to']}")
    print()


def cmd_path(args):
    """Find path between concepts."""
    g = get_graph()
    path = g.find_path(args.source, args.target)
    if path:
        print(f"\n🛤  Path: {' → '.join(path)}\n")
    else:
        print(f"\n🛤  No path found between '{args.source}' and '{args.target}'\n")


def main():
    parser = argparse.ArgumentParser(description="Striker Brain CLI")
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Search all memory systems")
    p_search.add_argument("query", nargs="+")

    p_stats = sub.add_parser("stats", help="Show brain stats")

    p_recent = sub.add_parser("recent", help="Recent observations")
    p_recent.add_argument("--limit", type=int, default=20)

    p_exp = sub.add_parser("experiments", help="Experiment log")
    p_exp.add_argument("--target", default=None)
    p_exp.add_argument("--outcome", default=None)
    p_exp.add_argument("--limit", type=int, default=20)

    p_graph = sub.add_parser("graph", help="Concept graph neighborhood")
    p_graph.add_argument("concept", nargs="+")
    p_graph.add_argument("--depth", type=int, default=2)

    p_path = sub.add_parser("path", help="Find path between concepts")
    p_path.add_argument("source")
    p_path.add_argument("target")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmds = {
        "search": cmd_search, "stats": cmd_stats, "recent": cmd_recent,
        "experiments": cmd_experiments, "graph": cmd_graph, "path": cmd_path,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
