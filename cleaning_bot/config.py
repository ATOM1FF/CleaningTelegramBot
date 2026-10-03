import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    channel_id: int | str | None
    database_path: str
    business_name: str
    contact_phone: str
    rate_limit_seconds: int


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "123456:replace_with_your_token":
        raise RuntimeError(".env faylida haqiqiy BOT_TOKEN ko'rsatilishi kerak")

    admin_ids = {
        int(value.strip())
        for value in os.getenv("ADMIN_IDS", "").split(",")
        if value.strip()
    }
    channel_raw = os.getenv("CHANNEL_ID", "").strip()
    channel_id: int | str | None = int(channel_raw) if channel_raw.lstrip("-").isdigit() else channel_raw or None

    return Settings(
        bot_token=token,
        admin_ids=admin_ids,
        channel_id=channel_id,
        database_path=os.getenv("DATABASE_PATH", "cleaning_bot.sqlite3"),
        business_name=os.getenv("BUSINESS_NAME", "Toza Gilam"),
        contact_phone=os.getenv("CONTACT_PHONE", ""),
        rate_limit_seconds=max(0, int(os.getenv("RATE_LIMIT_SECONDS", "300"))),
    )
