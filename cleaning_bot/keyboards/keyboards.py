from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from locales import LANGUAGE_NAMES, SUPPORTED_LANGUAGES
from utils.formatting import ITEM_KEYS


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGE_NAMES[language], callback_data=f"lang:{language}")]
            for language in SUPPORTED_LANGUAGES
        ]
    )


def main_menu(locale: dict[str, Any]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=locale["menu_order"])],
            [KeyboardButton(text=locale["menu_orders"]), KeyboardButton(text=locale["menu_about"])],
            [KeyboardButton(text=locale["menu_language"])],
        ],
        resize_keyboard=True,
    )


def navigation(locale: dict[str, Any], extra: list[KeyboardButton] | None = None) -> ReplyKeyboardMarkup:
    keyboard = []
    if extra:
        keyboard.append(extra)
    keyboard.append([KeyboardButton(text=locale["back"]), KeyboardButton(text=locale["cancel"])])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def contact_keyboard(locale: dict[str, Any]) -> ReplyKeyboardMarkup:
    return navigation(locale, [KeyboardButton(text=locale["contact"], request_contact=True)])


def address_keyboard(locale: dict[str, Any]) -> ReplyKeyboardMarkup:
    return navigation(
        locale,
        [KeyboardButton(text=locale["share_location"], request_location=True), KeyboardButton(text=locale["manual"])],
    )


def item_type_keyboard(locale: dict[str, Any]) -> ReplyKeyboardMarkup:
    keys = ["carpet", "curtain", "bedding", "sofa", "other"]
    rows = [[KeyboardButton(text=locale[ITEM_KEYS[key]])] for key in keys]
    rows.append([KeyboardButton(text=locale["back"]), KeyboardButton(text=locale["cancel"])])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def item_actions_keyboard(locale: dict[str, Any]) -> ReplyKeyboardMarkup:
    return navigation(locale, [KeyboardButton(text=locale["add_more"]), KeyboardButton(text=locale["finish_items"])])


def skip_keyboard(locale: dict[str, Any]) -> ReplyKeyboardMarkup:
    return navigation(locale, [KeyboardButton(text=locale["skip"])])


def confirmation_keyboard(locale: dict[str, Any]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=locale["confirm"], callback_data="order:confirm")],
            [InlineKeyboardButton(text=locale["cancel"], callback_data="order:cancel")],
        ]
    )


def operator_keyboard(order: dict[str, Any], locale: dict[str, Any]) -> InlineKeyboardMarkup:
    if order["status"] == "new" and order["accepted_by"] is None:
        accept_text = locale["op_accept"]
    elif order["accepted_by"] is not None:
        accept_text = locale["op_busy"]
    else:
        accept_text = locale["op_accept"]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=accept_text, callback_data=f"ord:{order['id']}:accept")],
            [
                InlineKeyboardButton(text=locale["op_progress"], callback_data=f"ord:{order['id']}:progress"),
                InlineKeyboardButton(text=locale["op_done"], callback_data=f"ord:{order['id']}:done"),
            ],
            [InlineKeyboardButton(text=locale["op_cancel"], callback_data=f"ord:{order['id']}:cancel")],
        ]
    )


def admin_keyboard(locale: dict[str, Any]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=locale["admin_stats"], callback_data="admin:stats")],
            [InlineKeyboardButton(text=locale["admin_orders"], callback_data="admin:orders")],
            [InlineKeyboardButton(text=locale["admin_operators"], callback_data="admin:operators")],
            [InlineKeyboardButton(text=locale["admin_broadcast"], callback_data="admin:broadcast")],
            [InlineKeyboardButton(text=locale["admin_clients"], callback_data="admin:clients")],
        ]
    )


def order_filter_keyboard(locale: dict[str, Any]) -> InlineKeyboardMarkup:
    labels = [
        ("new", locale["status_new"]),
        ("accepted", locale["status_accepted"]),
        ("in_progress", locale["status_in_progress"]),
        ("completed", locale["status_completed"]),
        ("cancelled", locale["status_cancelled"]),
        ("all", locale["admin_all"]),
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"admin:filter:{status}")]
            for status, label in labels
        ]
    )


def operator_manage_keyboard(locale: dict[str, Any]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=locale["admin_add_operator"], callback_data="admin:add_operator")],
            [InlineKeyboardButton(text=locale["admin_remove_operator"], callback_data="admin:remove_operator")],
        ]
    )


def statistics_keyboard(locale: dict[str, Any]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=locale["period_week"], callback_data="stats:week")],
            [InlineKeyboardButton(text=locale["period_month"], callback_data="stats:month")],
            [InlineKeyboardButton(text=locale["period_year"], callback_data="stats:year")],
        ]
    )


def report_keyboard(locale: dict[str, Any], period: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=locale["download_excel"], callback_data=f"report:{period}")]
        ]
    )
