"""
Striker Experiment Tracker — structured tracking of research threads.

Each thread is a distinct line of investigation with its own:
- hypothesis
- series of experiments
- current status
- next steps

Stored in SQLite for durability, surfaced in consciousness injection.
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

DB_PATH = Path(__file__).parent / "striker.db"


class ExperimentTracker:
    """Track distinct experimental threads."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS experiment_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                project TEXT NOT NULL,
                hypothesis TEXT NOT NULL,
                status TEXT DEFAULT 'active' CHECK(status IN ('active','paused','completed','abandoned')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                current_result TEXT,
                best_score REAL,
                iteration_count INTEGER DEFAULT 0,
                next_steps TEXT,
                notes TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_thread_project ON experiment_threads(project);
            CREATE INDEX IF NOT EXISTS idx_thread_status ON experiment_threads(status);
        """)
        self.conn.commit()

    def create_thread(self, name: str, project: str, hypothesis: str,
                      next_steps: str = None) -> int:
        """Start a new experimental thread."""
        now = datetime.utcnow().isoformat() + "Z"
        cur = self.conn.execute("""
            INSERT OR REPLACE INTO experiment_threads
                (name, project, hypothesis, status, created_at, updated_at, next_steps)
            VALUES (?, ?, ?, 'active', ?, ?, ?)
        """, (name, project, hypothesis, now, now, next_steps))
        self.conn.commit()
        return cur.lastrowid

    def update_thread(self, name: str, result: str = None, score: float = None,
                      next_steps: str = None, status: str = None,
                      notes: str = None):
        """Update an existing thread with new results."""
        now = datetime.utcnow().isoformat() + "Z"

        thread = self.get_thread(name)
        if not thread:
            return

        updates = ["updated_at = ?"]
        params = [now]

        if result is not None:
            updates.append("current_result = ?")
            params.append(result)
        if score is not None:
            updates.append("best_score = ?")
            # Only update if better than current best
            current_best = thread.get("best_score")
            if current_best is None or score > current_best:
                params.append(score)
            else:
                params.append(current_best)
        if next_steps is not None:
            updates.append("next_steps = ?")
            params.append(next_steps)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        updates.append("iteration_count = iteration_count + 1")

        params.append(name)
        self.conn.execute(
            f"UPDATE experiment_threads SET {', '.join(updates)} WHERE name = ?",
            params
        )
        self.conn.commit()

    def get_thread(self, name: str) -> Optional[Dict]:
        """Get a single thread by name."""
        row = self.conn.execute(
            "SELECT * FROM experiment_threads WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None

    def get_active_threads(self) -> List[Dict]:
        """Get all active experimental threads."""
        rows = self.conn.execute(
            "SELECT * FROM experiment_threads WHERE status = 'active' ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_threads_by_project(self, project: str) -> List[Dict]:
        """Get all threads for a project."""
        rows = self.conn.execute(
            "SELECT * FROM experiment_threads WHERE project = ? ORDER BY updated_at DESC",
            (project,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_threads(self) -> List[Dict]:
        """Get all threads."""
        rows = self.conn.execute(
            "SELECT * FROM experiment_threads ORDER BY status, updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def generate_status_summary(self) -> str:
        """Generate a concise status summary for consciousness injection."""
        active = self.get_active_threads()
        if not active:
            return ""

        lines = []
        # Group by project
        by_project = {}
        for t in active:
            by_project.setdefault(t["project"], []).append(t)

        for project, threads in by_project.items():
            lines.append(f"### {project}")
            for t in threads:
                score = f" (best: {t['best_score']:.4f})" if t["best_score"] is not None else ""
                iters = f" [{t['iteration_count']} iterations]" if t["iteration_count"] else ""
                lines.append(f"- **{t['name']}**: {t['hypothesis'][:100]}{score}{iters}")
                if t.get("current_result"):
                    lines.append(f"  Latest: {t['current_result'][:120]}")
                if t.get("next_steps"):
                    lines.append(f"  Next: {t['next_steps'][:120]}")
            lines.append("")

        return "\n".join(lines)


# ── Singleton ────────────────────────────────────────────────────────

_instance = None

def get_tracker() -> ExperimentTracker:
    global _instance
    if _instance is None:
        _instance = ExperimentTracker()
    return _instance
