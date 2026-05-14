"""
SQLite-backed persistence for policy rules with change notification via polling.
Detects creates, updates, and deletes reliably using a count+timestamp fingerprint.
"""

import sqlite3, json, threading, time, logging
from pathlib import Path
from .models import PolicyRule

logger = logging.getLogger(__name__)
DB_PATH = Path("policy_rules.db")


class RuleStore:
    def __init__(self):
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._last_fingerprint = ""
        self._change_callbacks: list = []
        self._init_db()
        self._last_fingerprint = self._compute_fingerprint()
        self._start_watcher()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    type TEXT NOT NULL,
                    config TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            self._conn.commit()

    def _compute_fingerprint(self) -> str:
        """Fingerprint = count + max(updated_at) so deletes are always detected."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt, COALESCE(MAX(updated_at), '') as mx FROM rules"
            ).fetchone()
        return f"{row['cnt']}:{row['mx']}"

    def _notify(self):
        """Fire all change callbacks (called after save/delete)."""
        for cb in self._change_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Change callback error: {e}")

    def _start_watcher(self):
        """Background thread: poll DB every 2s, fire callbacks on change."""
        def _watch():
            while True:
                time.sleep(2)
                try:
                    current = self._compute_fingerprint()
                    if current != self._last_fingerprint:
                        self._last_fingerprint = current
                        self._notify()
                except Exception as e:
                    logger.error(f"Rule watcher error: {e}")
        threading.Thread(target=_watch, daemon=True).start()

    def on_change(self, callback):
        self._change_callbacks.append(callback)

    def save(self, rule: PolicyRule):
        with self._lock:
            self._conn.execute("""
                INSERT OR REPLACE INTO rules (id, name, enabled, type, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (rule.id, rule.name, int(rule.enabled), rule.type,
                  json.dumps(rule.config), rule.created_at, rule.updated_at))
            self._conn.commit()
        self._last_fingerprint = self._compute_fingerprint()
        self._notify()

    def delete(self, rule_id: str):
        with self._lock:
            self._conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            self._conn.commit()
        self._last_fingerprint = self._compute_fingerprint()
        self._notify()

    def load_all(self) -> list[PolicyRule]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM rules ORDER BY created_at").fetchall()
        return [PolicyRule(
            id=row["id"], name=row["name"], enabled=bool(row["enabled"]),
            type=row["type"], config=json.loads(row["config"]),
            created_at=row["created_at"], updated_at=row["updated_at"]
        ) for row in rows]
