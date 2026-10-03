import json
from typing import Any

import aiosqlite
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey


class SQLiteStorage(BaseStorage):
    def __init__(self, path: str) -> None:
        self.path = path

    @staticmethod
    def _key(key: StorageKey) -> str:
        return ":".join(
            str(value or "")
            for value in (
                key.bot_id, key.chat_id, key.user_id, key.thread_id,
                key.business_connection_id, key.destiny,
            )
        )

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if hasattr(state, "state") else state
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO fsm_state(storage_key, state, data) VALUES (?, ?, '{}')
                   ON CONFLICT(storage_key) DO UPDATE SET state=excluded.state""",
                (self._key(key), value),
            )
            await db.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT state FROM fsm_state WHERE storage_key=?", (self._key(key),))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO fsm_state(storage_key, state, data) VALUES (?, NULL, ?)
                   ON CONFLICT(storage_key) DO UPDATE SET data=excluded.data""",
                (self._key(key), json.dumps(data, ensure_ascii=False)),
            )
            await db.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT data FROM fsm_state WHERE storage_key=?", (self._key(key),))
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else {}

    async def close(self) -> None:
        return None
