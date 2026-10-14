import asyncio
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from config import load_settings
from database import Database
from database.storage import SQLiteStorage
from handlers import admin_router, common_router, operators_router, orders_router


# Render kabi serverlar uchun oddiy web-server (portni band qilib turish uchun)
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async b_app = web.Application()
b_app.router.add_get("/", handle_ping)


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

    # Render avtomatik beradigan PORT ni aniqlaymiz (agar bo'lmasa 8080)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(b_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server {port}-portda ishga tushdi.")

    # Botni ishga tushirish
    async with Bot(settings.bot_token) as bot:
        await dispatcher.start_polling(bot, db=db, settings=settings)


if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
