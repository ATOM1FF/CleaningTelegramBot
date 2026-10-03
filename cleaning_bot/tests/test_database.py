import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database import Database, RateLimited
from database.storage import SQLiteStorage
from aiogram.fsm.storage.base import StorageKey


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "test.sqlite3")
        self.db = Database(self.path)
        await self.db.initialize()

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_order_lifecycle_and_statistics(self):
        await self.db.register_user(10, "Test", "tester")
        order_id = await self.db.create_order(
            user_id=10, customer_name="Test", phone="+998901234567", address="Toshkent",
            latitude=None, longitude=None, comment="", photo_file_id=None,
            items=[{"type": "carpet", "width": 2.0, "length": 3.0, "quantity": 2, "area": 6.0}],
            rate_limit_seconds=0, first_name="Test", username="tester",
        )
        with self.assertRaises(RateLimited):
            await self.db.create_order(
                user_id=10, customer_name="Test", phone="+998901234567", address="Toshkent",
                latitude=None, longitude=None, comment="", photo_file_id=None,
                items=[{"type": "carpet", "width": 2.0, "length": 3.0, "quantity": 1, "area": 6.0}],
                rate_limit_seconds=300, first_name="Test", username="tester",
            )
        order, result = await self.db.update_status(order_id, "accept", 20, False)
        self.assertEqual(result, "updated")
        self.assertEqual(order["accepted_by"], 20)
        order, result = await self.db.update_status(order_id, "done", 20, False)
        self.assertEqual(result, "updated")

        now = datetime.now(timezone.utc)
        stats = await self.db.statistics(now - timedelta(days=1), now + timedelta(days=1))
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["pieces"], 2)
        self.assertEqual(stats["area"], 12.0)
        self.assertEqual(stats["distribution"], {"carpet": 2})

    async def test_fsm_survives_new_storage_instance(self):
        key = StorageKey(bot_id=1, chat_id=2, user_id=2)
        first = SQLiteStorage(self.path)
        await first.set_state(key, "OrderForm:name")
        await first.set_data(key, {"name": "Aziza", "items": []})
        second = SQLiteStorage(self.path)
        self.assertEqual(await second.get_state(key), "OrderForm:name")
        self.assertEqual(await second.get_data(key), {"name": "Aziza", "items": []})


if __name__ == "__main__":
    unittest.main()
