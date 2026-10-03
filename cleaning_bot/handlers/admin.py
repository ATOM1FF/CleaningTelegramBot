import logging
from datetime import datetime, timedelta, timezone
from io import BytesIO

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from config import Settings
from database import Database
from keyboards import (
    admin_keyboard,
    operator_manage_keyboard,
    order_filter_keyboard,
    report_keyboard,
    statistics_keyboard,
)
from locales import get_locale
from states import AdminForm
from utils.formatting import status_label
from utils.reports import make_report

router = Router(name="admin")
logger = logging.getLogger(__name__)
_PERIOD_NAMES = {"week": "period_week", "month": "period_month", "year": "period_year"}


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


def _period_range(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if period == "week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now + timedelta(seconds=1)


@router.message(Command("admin"))
async def admin_command(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        locale = get_locale(await db.get_language(message.from_user.id))
        await message.answer(locale["admin_only"])
        return
    locale = get_locale(await db.get_language(message.from_user.id))
    await message.answer(locale["admin_title"], reply_markup=admin_keyboard(locale))


@router.callback_query(F.data.startswith("admin:"))
async def admin_actions(callback: CallbackQuery, db: Database, settings: Settings, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id, settings):
        locale = get_locale(await db.get_language(callback.from_user.id))
        await callback.answer(locale["admin_only"], show_alert=True)
        return
    locale = get_locale(await db.get_language(callback.from_user.id))
    action = callback.data.split(":", 1)[1]
    await callback.answer()
    if action == "stats":
        await callback.message.answer(locale["admin_period"], reply_markup=statistics_keyboard(locale))
    elif action == "orders":
        await callback.message.answer(locale["admin_filter"], reply_markup=order_filter_keyboard(locale))
    elif action == "operators":
        ids = sorted(await db.operator_ids())
        list_text = ", ".join(map(str, ids)) if ids else "-"
        await callback.message.answer(
            f"{locale['admin_operators']}\n{list_text}",
            reply_markup=operator_manage_keyboard(locale),
        )
    elif action == "add_operator":
        await state.set_state(AdminForm.add_operator)
        await callback.message.answer(locale["admin_enter_id"])
    elif action == "remove_operator":
        await state.set_state(AdminForm.remove_operator)
        await callback.message.answer(locale["admin_enter_id"])
    elif action == "broadcast":
        await state.set_state(AdminForm.broadcast)
        await callback.message.answer(locale["admin_broadcast_prompt"])
    elif action == "clients":
        count = await db.customer_count()
        await callback.message.answer(locale["admin_client_count"].format(count=count))
    elif action.startswith("filter:"):
        status = action.split(":", 1)[1]
        orders = await db.list_orders(None if status == "all" else status)
        if not orders:
            await callback.message.answer(locale["admin_no_orders"])
            return
        lines = []
        for order in orders:
            created = order["created_at"].replace("T", " ")[:16]
            lines.append(
                f"#{order['id']} | {order['customer_name']} | {order['phone']} | "
                f"{status_label(order['status'], locale)} | {created}"
            )
        await callback.message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("stats:"))
async def show_statistics(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        locale = get_locale(await db.get_language(callback.from_user.id))
        await callback.answer(locale["admin_only"], show_alert=True)
        return
    period = callback.data.split(":", 1)[1]
    if period not in _PERIOD_NAMES:
        await callback.answer()
        return
    locale = get_locale(await db.get_language(callback.from_user.id))
    start, end = _period_range(period)
    values = await db.statistics(start, end)
    distribution = values["distribution"]
    distribution_text = ", ".join(
        f"{locale[f'type_{kind}']}: {quantity}"
        for kind, quantity in distribution.items()
    ) or locale["stats_empty_types"]
    period_name = locale[_PERIOD_NAMES[period]]
    text = locale["stats_text"].format(
        period=period_name, total=values["total"], completed=values["completed"],
        cancelled=values["cancelled"], pieces=values["pieces"], area=values["area"],
        distribution=distribution_text,
    )
    await callback.answer()
    await callback.message.answer(text, reply_markup=report_keyboard(locale, period))


@router.callback_query(F.data.startswith("report:"))
async def export_report(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        locale = get_locale(await db.get_language(callback.from_user.id))
        await callback.answer(locale["admin_only"], show_alert=True)
        return
    period = callback.data.split(":", 1)[1]
    if period not in _PERIOD_NAMES:
        await callback.answer()
        return
    locale = get_locale(await db.get_language(callback.from_user.id))
    start, end = _period_range(period)
    rows = await db.completed_orders(start, end)
    report = make_report(rows, period)
    period_name = locale[_PERIOD_NAMES[period]]
    file = BufferedInputFile(report.getvalue(), filename=f"cleaning_report_{period}.xlsx")
    await callback.answer()
    await callback.message.answer_document(file, caption=locale["excel_caption"].format(period=period_name))


@router.message(AdminForm.add_operator, F.text)
async def add_operator(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    locale = get_locale(await db.get_language(message.from_user.id))
    if not _is_admin(message.from_user.id, settings):
        await state.clear()
        await message.answer(locale["admin_only"])
        return
    value = message.text.strip()
    if not value.isdigit():
        await message.answer(locale["admin_bad_id"])
        return
    await db.add_operator(int(value))
    await state.clear()
    await message.answer(locale["admin_added"], reply_markup=admin_keyboard(locale))


@router.message(AdminForm.remove_operator, F.text)
async def remove_operator(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    locale = get_locale(await db.get_language(message.from_user.id))
    if not _is_admin(message.from_user.id, settings):
        await state.clear()
        await message.answer(locale["admin_only"])
        return
    value = message.text.strip()
    if not value.isdigit():
        await message.answer(locale["admin_bad_id"])
        return
    await db.remove_operator(int(value))
    await state.clear()
    await message.answer(locale["admin_removed"], reply_markup=admin_keyboard(locale))


@router.message(AdminForm.broadcast)
async def broadcast(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    locale = get_locale(await db.get_language(message.from_user.id))
    if not _is_admin(message.from_user.id, settings):
        await state.clear()
        await message.answer(locale["admin_only"])
        return
    customer_ids = await db.customer_ids()
    sent = failed = 0
    for customer_id in customer_ids:
        try:
            await message.bot.copy_message(
                chat_id=customer_id, from_chat_id=message.chat.id, message_id=message.message_id
            )
            sent += 1
        except TelegramAPIError:
            failed += 1
            logger.exception("Ommaviy xabar %s foydalanuvchiga yuborilmadi", customer_id)
    await state.clear()
    await message.answer(
        locale["admin_broadcast_done"].format(sent=sent, failed=failed),
        reply_markup=admin_keyboard(locale),
    )
