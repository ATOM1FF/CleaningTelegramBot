from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards import language_keyboard, main_menu
from locales import SUPPORTED_LANGUAGES, get_locale
from utils.formatting import status_label

router = Router(name="common")
_MENU_TEXTS = {
    get_locale(language)[key]
    for language in SUPPORTED_LANGUAGES
    for key in ("menu_orders", "menu_about", "menu_language")
}


@router.message(CommandStart())
async def start(message: Message, db: Database, settings: Settings) -> None:
    await db.register_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    locale = get_locale(await db.get_language(message.from_user.id))
    await message.answer(locale["choose_language"], reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def select_language(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    language = callback.data.split(":", 1)[1]
    if language not in SUPPORTED_LANGUAGES:
        await callback.answer()
        return
    await db.set_language(callback.from_user.id, language)
    locale = get_locale(language)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            locale["welcome"].format(business=settings.business_name),
            reply_markup=main_menu(locale),
        )


@router.message(F.text.in_(_MENU_TEXTS))
async def menu_actions(message: Message, db: Database, settings: Settings) -> None:
    language = await db.get_language(message.from_user.id)
    locale = get_locale(language)
    text = message.text
    action = next(
        (
            key
            for lang in SUPPORTED_LANGUAGES
            for key in ("menu_orders", "menu_about", "menu_language")
            if text == get_locale(lang)[key]
        ),
        None,
    )
    if action == "menu_language":
        await message.answer(locale["choose_language"], reply_markup=language_keyboard())
    elif action == "menu_about":
        await message.answer(
            locale["about_text"].format(business=settings.business_name, phone=settings.contact_phone or "-"),
            reply_markup=main_menu(locale),
        )
    elif action == "menu_orders":
        orders = await db.list_user_orders(message.from_user.id)
        if not orders:
            await message.answer(locale["my_empty"], reply_markup=main_menu(locale))
            return
        rows = [locale["my_orders_title"]]
        for order in orders:
            created = order["created_at"].replace("T", " ")[:16]
            rows.append(
                locale["my_order_row"].format(
                    order_id=order["id"], date=created,
                    status=status_label(order["status"], locale),
                )
            )
        await message.answer("\n".join(rows), reply_markup=main_menu(locale))
