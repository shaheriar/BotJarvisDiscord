"""SQLite storage for daily Top Movers subscriptions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite


class TopMoversSubscriptions:
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
                CREATE TABLE IF NOT EXISTS top_movers_subscriptions (
                    server_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    subscribed_by TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_sent_utc_date TEXT,
                    PRIMARY KEY (server_id, channel_id)
                )
                """
            )
            await db.commit()
        self._initialized = True

    async def add_subscription(self, *, server_id: str, channel_id: str, subscribed_by: str) -> bool:
        """
        Add or update a subscription.

        Returns True if a new row was created, False if it already existed.
        """
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT 1 FROM top_movers_subscriptions WHERE server_id = ? AND channel_id = ?",
                (server_id, channel_id),
            )
            exists = await cur.fetchone()
            if exists:
                await db.execute(
                    """
                    UPDATE top_movers_subscriptions
                    SET enabled = 1, subscribed_by = ?, created_at = created_at
                    WHERE server_id = ? AND channel_id = ?
                    """,
                    (subscribed_by, server_id, channel_id),
                )
                await db.commit()
                return False

            await db.execute(
                """
                INSERT INTO top_movers_subscriptions(server_id, channel_id, subscribed_by, enabled, last_sent_utc_date)
                VALUES (?, ?, ?, 1, NULL)
                """,
                (server_id, channel_id, subscribed_by),
            )
            await db.commit()
            return True

    async def remove_subscription(self, *, server_id: str, channel_id: str) -> bool:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "DELETE FROM top_movers_subscriptions WHERE server_id = ? AND channel_id = ?",
                (server_id, channel_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def get_due_subscriptions(self, *, today_utc_date: str) -> list[dict[str, Any]]:
        """
        Return subscriptions that are enabled and not yet sent for `today_utc_date`.
        """
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                SELECT server_id, channel_id, last_sent_utc_date
                FROM top_movers_subscriptions
                WHERE enabled = 1
                  AND (last_sent_utc_date IS NULL OR last_sent_utc_date != ?)
                """,
                (today_utc_date,),
            )
            rows = await cur.fetchall()

        return [
            {"server_id": str(server_id), "channel_id": str(channel_id), "last_sent_utc_date": last_sent}
            for (server_id, channel_id, last_sent) in rows
        ]

    async def mark_sent(self, *, server_id: str, channel_id: str, sent_date_utc: str) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE top_movers_subscriptions
                SET last_sent_utc_date = ?
                WHERE server_id = ? AND channel_id = ?
                """,
                (sent_date_utc, server_id, channel_id),
            )
            await db.commit()

