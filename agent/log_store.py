"""
Structured log + token usage storage (SQLite).
Ensures tables exist before every query so /api/stats never crashes on fresh start.
"""

import aiosqlite, json, logging
from datetime import datetime

DB_PATH = "agent_logs.db"


class LogStore:
    def __init__(self):
        self._callbacks = []

    def on_new_entry(self, callback):
        self._callbacks.append(callback)

    async def _ensure_schema(self, db):
        """Create tables if they don't exist. Safe to call repeatedly."""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, conversation_id TEXT, tool_name TEXT,
                arguments TEXT, policy_decision TEXT, rule_id TEXT,
                reason TEXT, result_preview TEXT, approval_id TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, tool_calls TEXT, tokens TEXT, created_at TEXT
            )
        """)
        await db.commit()

    async def append_tool_call(self, entry: dict):
        async with aiosqlite.connect(DB_PATH) as db:
            await self._ensure_schema(db)
            await db.execute(
                "INSERT INTO tool_calls (timestamp, conversation_id, tool_name, arguments, policy_decision, rule_id, reason, result_preview, approval_id) VALUES (?,?,?,?,?,?,?,?,?)",
                (entry.get("timestamp"), entry.get("conversation_id"), entry.get("tool_name"),
                 json.dumps(entry.get("arguments", {})), entry.get("policy_decision"),
                 entry.get("rule_id"), entry.get("reason"), entry.get("result_preview"),
                 entry.get("approval_id")))
            await db.commit()
        for cb in self._callbacks:
            await cb(entry)

    async def save_conversation(self, conv_id: str, tool_calls: list, tokens: dict):
        async with aiosqlite.connect(DB_PATH) as db:
            await self._ensure_schema(db)
            await db.execute(
                "INSERT OR REPLACE INTO conversations (id, tool_calls, tokens, created_at) VALUES (?, ?, ?, ?)",
                (conv_id, json.dumps(tool_calls), json.dumps(tokens), datetime.utcnow().isoformat()))
            await db.commit()

    async def query(self, limit=50, offset=0, tool_name=None, action=None) -> list[dict]:
        filters, params = [], []
        if tool_name:
            filters.append("tool_name = ?"); params.append(tool_name)
        if action:
            filters.append("policy_decision = ?"); params.append(action)
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        async with aiosqlite.connect(DB_PATH) as db:
            await self._ensure_schema(db)
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                f"SELECT * FROM tool_calls {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset])
        return [dict(r) for r in rows]

    async def get_stats(self) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
            await self._ensure_schema(db)
            db.row_factory = aiosqlite.Row
            total = (await db.execute_fetchall("SELECT COUNT(*) as c FROM tool_calls"))[0]["c"]
            blocked = (await db.execute_fetchall(
                "SELECT COUNT(*) as c FROM tool_calls WHERE policy_decision='BLOCK'"))[0]["c"]
            approved = (await db.execute_fetchall(
                "SELECT COUNT(*) as c FROM tool_calls WHERE policy_decision='APPROVED'"))[0]["c"]
            denied = (await db.execute_fetchall(
                "SELECT COUNT(*) as c FROM tool_calls WHERE policy_decision='DENIED'"))[0]["c"]
            convs = (await db.execute_fetchall("SELECT COUNT(*) as c FROM conversations"))[0]["c"]
            tokens_rows = await db.execute_fetchall("SELECT tokens FROM conversations")

        tp = tc = 0
        for row in tokens_rows:
            try:
                t = json.loads(row["tokens"])
                tp += t.get("prompt", 0)
                tc += t.get("completion", 0)
            except (json.JSONDecodeError, TypeError):
                pass  # skip malformed token data

        return {
            "total_conversations": convs,
            "total_tool_calls": total,
            "blocked_calls": blocked,
            "approved_calls": approved,
            "denied_calls": denied,
            "blocked_pct": round(blocked / total * 100, 1) if total else 0,
            "total_prompt_tokens": tp,
            "total_completion_tokens": tc,
            "estimated_cost": round((tp * 0.15 + tc * 0.60) / 1_000_000, 4),  # rough $/1M tokens
        }
