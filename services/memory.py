"""SQLite-backed memory store for Jarvis conversations and facts."""
from __future__ import annotations

from pathlib import Path

import aiosqlite


class MemoryService:
    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self.db_path = db_path
        self._initialized = False

    async def init(self) -> None:
        if self._initialized:
            return
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()
        self._initialized = True

    async def save_message(self, *, server: str, sender: str, role: str, content: str) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations(server, sender, role, content) VALUES (?, ?, ?, ?)",
                (server, sender, role, content),
            )
            await db.commit()

    async def get_history(self, *, server: str, sender: str, limit: int = 30) -> list[dict]:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                SELECT role, content
                FROM conversations
                WHERE server = ? AND sender = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (server, sender, max(1, limit)),
            )
            rows = await cur.fetchall()
        rows.reverse()
        return [{"role": role, "content": content} for role, content in rows]

    async def save_fact(self, *, server: str, sender: str, key: str, value: str, source: str = "") -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO facts(server, sender, key, value, source) VALUES (?, ?, ?, ?, ?)",
                (server, sender, key, value, source),
            )
            await db.commit()

    async def recall_facts(self, *, server: str, sender: str, limit: int = 10) -> list[dict]:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                SELECT key, value, source
                FROM facts
                WHERE server = ? AND sender = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (server, sender, max(1, limit)),
            )
            rows = await cur.fetchall()
        return [{"key": key, "value": value, "source": source} for key, value, source in rows]
