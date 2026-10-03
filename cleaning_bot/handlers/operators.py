import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery

from config import Settings
from database import Database
from keyboards import operator_keyboard
from locales import get_locale

router = Router(name="operators")
logger = logging.getLogger(__name__)
_FINAL_STATUSES = {"completed", "cancelled"}


@router.callback_query(F.data.startswith("ord:"))
async def update_order_status(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    user_id = callback.from_user.id
    locale = get_locale("uz")
    allowed = user_id in settings.admin_ids or user_id in await db.operator_ids()
    if not allowed:
        await callback.answer(locale["op_not_allowed"], show_alert=True)
        return
    try:
        _, order_id_raw, action = callback.data.split(":", 2)
        order_id = int(order_id_raw)
    except (ValueError, AttributeError):
        await callback.answer()
        return
    order, result = await db.update_status(order_id, action, user_id, user_id in settings.admin_ids)
    if result == "missing":
        await callback.answer(locale["admin_no_orders"], show_alert=True)
        return
    if result == "taken":
        await _sync_buttons(callback, db, order)
        await callback.answer(locale["op_claimed_else"], show_alert=True)
        return
    if result == "not_owner":
        await callback.answer(locale["op_not_allowed"], show_alert=True)
        return
    if result != "updated" or order is None:
        await callback.answer()
        return

    await _sync_buttons(callback, db, order)
    await callback.answer(locale["op_claimed"] if action == "accept" else locale["op_updated"])
    customer_locale = get_locale(await db.get_language(order["user_id"]))
    try:
        await callback.bot.send_message(
            order["user_id"],
            customer_locale["status_notice"].format(
                order_id=order_id, status=customer_locale[f"status_{order['status']}"]
            ),
        )
    except TelegramAPIError:
        logger.exception("Buyurtma holati mijozga yuborilmadi: order=%s", order_id)


async def _sync_buttons(callback: CallbackQuery, db: Database, order: dict) -> None:
    keyboard = None if order["status"] in _FINAL_STATUSES else operator_keyboard(order, get_locale("uz"))
    for chat_id, message_id in await db.order_messages(order["id"]):
        try:
            await callback.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=keyboard
            )
        except TelegramAPIError:
            logger.exception("Buyurtma tugmalari yangilanmadi: order=%s chat=%s", order["id"], chat_id)
