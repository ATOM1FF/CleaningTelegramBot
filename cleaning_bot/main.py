import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from config import load_settings
from database import Database
from database.storage import SQLiteStorage
from handlers import admin_router, common_router, operators_router, orders_router


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = load_settings()
    db = Database(settings.database_path)
    await db.initialize()
    if not settings.admin_ids:
        logging.warning("ADMIN_IDS ro'yxati bo'sh: /admin panelidan foydalanuvchi foydalana olmaydi")

    dispatcher = Dispatcher(storage=SQLiteStorage(settings.database_path))
    dispatcher.include_routers(common_router, orders_router, operators_router, admin_router)

    @dispatcher.errors()
    async def handle_error(event: ErrorEvent) -> bool:
        error = event.exception
        logging.getLogger("bot.errors").error(
            "Yangilanmani qayta ishlashda xatolik",
            exc_info=(type(error), error, error.__traceback__),
        )
        return True

    async with Bot(settings.bot_token) as bot:
        await dispatcher.start_polling(bot, db=db, settings=settings)


if __name__ == "__main__":
    asyncio.run(main())
