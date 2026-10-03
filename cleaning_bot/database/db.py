from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite


class RateLimited(Exception):
    def __init__(self, wait_seconds: int) -> None:
        self.wait_seconds = wait_seconds
        super().__init__("User is rate limited")


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    async def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA foreign_keys=ON")
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT NOT NULL DEFAULT 'uz',
                    first_name TEXT,
                    username TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS fsm_state (
                    storage_key TEXT PRIMARY KEY,
                    state TEXT,
                    data TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS operators (
                    user_id INTEGER PRIMARY KEY,
                    added_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(user_id),
                    customer_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    comment TEXT NOT NULL DEFAULT '',
                    photo_file_id TEXT,
                    status TEXT NOT NULL DEFAULT 'new',
                    accepted_by INTEGER,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    item_type TEXT NOT NULL,
                    width REAL NOT NULL,
                    length REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    area REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS order_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    UNIQUE(chat_id, message_id)
                );
                CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);
                """
            )
            await db.commit()

    async def register_user(self, user_id: int, first_name: str, username: str | None) -> None:
        now = self._now()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO users(user_id, first_name, username, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name,
                       username=excluded.username""",
                (user_id, first_name, username, now),
            )
            await db.commit()

    async def set_language(self, user_id: int, language: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET language=? WHERE user_id=?", (language, user_id))
            await db.commit()

    async def get_language(self, user_id: int) -> str:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else "uz"

    async def create_order(
        self,
        user_id: int,
        customer_name: str,
        phone: str,
        address: str,
        latitude: float | None,
        longitude: float | None,
        comment: str,
        photo_file_id: str | None,
        items: list[dict[str, Any]],
        rate_limit_seconds: int,
        first_name: str,
        username: str | None,
    ) -> int:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat(timespec="seconds")
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys=ON")
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                """INSERT INTO users(user_id, first_name, username, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name,
                       username=excluded.username""",
                (user_id, first_name, username, now),
            )
            if rate_limit_seconds:
                cursor = await db.execute(
                    "SELECT created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1",
                    (user_id,),
                )
                last = await cursor.fetchone()
                if last:
                    last_dt = datetime.fromisoformat(last[0])
                    wait = rate_limit_seconds - int((now_dt - last_dt).total_seconds())
                    if wait > 0:
                        await db.rollback()
                        raise RateLimited(wait)
            cursor = await db.execute(
                """INSERT INTO orders(user_id, customer_name, phone, address, latitude,
                   longitude, comment, photo_file_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, customer_name, phone, address, latitude, longitude, comment, photo_file_id, now),
            )
            order_id = int(cursor.lastrowid)
            await db.executemany(
                """INSERT INTO order_items(order_id, item_type, width, length, quantity, area)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (order_id, item["type"], item["width"], item["length"], item["quantity"], item["area"])
                    for item in items
                ],
            )
            await db.commit()
            return order_id

    async def get_order(self, order_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            order = dict(row)
            cursor = await db.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (order_id,))
            order["items"] = [dict(item) for item in await cursor.fetchall()]
            return order

    async def save_order_message(self, order_id: int, chat_id: int, message_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO order_messages(order_id, chat_id, message_id) VALUES (?, ?, ?)",
                (order_id, chat_id, message_id),
            )
            await db.commit()

    async def order_messages(self, order_id: int) -> list[tuple[int, int]]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT chat_id, message_id FROM order_messages WHERE order_id=?", (order_id,)
            )
            return [(row[0], row[1]) for row in await cursor.fetchall()]

    async def update_status(
        self, order_id: int, action: str, operator_id: int, is_admin: bool
    ) -> tuple[dict[str, Any] | None, str]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
            row = await cursor.fetchone()
            if not row:
                await db.rollback()
                return None, "missing"
            order = dict(row)
            if action == "accept":
                if order["accepted_by"] is not None and order["accepted_by"] != operator_id:
                    await db.rollback()
                    return order, "taken"
                if order["status"] == "new":
                    await db.execute(
                        "UPDATE orders SET status='accepted', accepted_by=? WHERE id=?",
                        (operator_id, order_id),
                    )
                elif order["accepted_by"] != operator_id:
                    await db.rollback()
                    return order, "taken"
            else:
                if order["accepted_by"] is not None and order["accepted_by"] != operator_id and not is_admin:
                    await db.rollback()
                    return order, "not_owner"
                statuses = {"progress": "in_progress", "done": "completed", "cancel": "cancelled"}
                new_status = statuses.get(action)
                if not new_status:
                    await db.rollback()
                    return order, "invalid"
                await db.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
            await db.commit()
        updated = await self.get_order(order_id)
        return updated, "updated"

    async def list_user_orders(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def list_orders(self, status: str | None = None, limit: int = 15) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute(
                    "SELECT id, customer_name, phone, status, created_at FROM orders WHERE status=? ORDER BY id DESC LIMIT ?",
                    (status, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT id, customer_name, phone, status, created_at FROM orders ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
            return [dict(row) for row in await cursor.fetchall()]

    async def customer_ids(self) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT user_id FROM users ORDER BY user_id")
            return [row[0] for row in await cursor.fetchall()]

    async def customer_count(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            return int((await cursor.fetchone())[0])

    async def add_operator(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO operators(user_id, added_at) VALUES (?, ?)",
                (user_id, self._now()),
            )
            await db.commit()

    async def remove_operator(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM operators WHERE user_id=?", (user_id,))
            await db.commit()

    async def operator_ids(self) -> set[int]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT user_id FROM operators")
            return {row[0] for row in await cursor.fetchall()}

    async def statistics(self, start: datetime, end: datetime) -> dict[str, Any]:
        start_text, end_text = start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) AS cancelled
                   FROM orders WHERE created_at>=? AND created_at<?""",
                (start_text, end_text),
            )
            counts = await cursor.fetchone()
            cursor = await db.execute(
                """SELECT COALESCE(SUM(i.quantity), 0) AS pieces,
                          COALESCE(SUM(i.area * i.quantity), 0) AS area
                   FROM orders o JOIN order_items i ON i.order_id=o.id
                   WHERE o.status='completed' AND o.created_at>=? AND o.created_at<?""",
                (start_text, end_text),
            )
            volume = await cursor.fetchone()
            cursor = await db.execute(
                """SELECT i.item_type, SUM(i.quantity) AS quantity
                   FROM orders o JOIN order_items i ON i.order_id=o.id
                   WHERE o.status='completed' AND o.created_at>=? AND o.created_at<?
                   GROUP BY i.item_type ORDER BY i.item_type""",
                (start_text, end_text),
            )
            distribution = {row[0]: row[1] for row in await cursor.fetchall()}
            return {
                "total": counts[0] or 0,
                "completed": counts[1] or 0,
                "cancelled": counts[2] or 0,
                "pieces": volume[0] or 0,
                "area": volume[1] or 0.0,
                "distribution": distribution,
            }

    async def completed_orders(self, start: datetime, end: datetime) -> list[dict[str, Any]]:
        start_text, end_text = start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT o.id, o.customer_name, o.phone, o.address, o.created_at,
                          i.item_type, i.width, i.length, i.quantity, i.area
                   FROM orders o JOIN order_items i ON i.order_id=o.id
                   WHERE o.status='completed' AND o.created_at>=? AND o.created_at<?
                   ORDER BY o.id, i.id""",
                (start_text, end_text),
            )
            return [dict(row) for row in await cursor.fetchall()]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
