import logging
import math
from urllib.parse import quote

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database, RateLimited
from keyboards import (
    address_keyboard,
    confirmation_keyboard,
    contact_keyboard,
    item_actions_keyboard,
    item_type_keyboard,
    main_menu,
    navigation,
    operator_keyboard,
    skip_keyboard,
)
from locales import SUPPORTED_LANGUAGES, get_locale
from states import OrderForm
from utils.formatting import format_items, item_type_from_label, status_label
from utils.validation import normalize_phone, parse_size

router = Router(name="orders")
logger = logging.getLogger(__name__)
_ORDER_TEXTS = {get_locale(lang)["menu_order"] for lang in SUPPORTED_LANGUAGES}
_NAV_STATES = (
    OrderForm.name, OrderForm.phone, OrderForm.address, OrderForm.item_type,
    OrderForm.item_size, OrderForm.item_quantity, OrderForm.items_done,
    OrderForm.comment, OrderForm.photo, OrderForm.confirm,
)
_NAV_ACTIONS = {
    get_locale(language)[key]
    for language in SUPPORTED_LANGUAGES
    for key in ("back", "cancel")
}


async def _locale(db: Database, user_id: int) -> dict:
    return get_locale(await db.get_language(user_id))


async def _ask_type(message: Message, locale: dict) -> None:
    await message.answer(locale["ask_type"], reply_markup=item_type_keyboard(locale))


async def _ask_items_done(message: Message, locale: dict) -> None:
    await message.answer(locale["items_complete"], reply_markup=item_actions_keyboard(locale))


async def _ask_comment(message: Message, state: FSMContext, locale: dict) -> None:
    await state.set_state(OrderForm.comment)
    await message.answer(locale["ask_comment"], reply_markup=skip_keyboard(locale))


async def _show_confirmation(message: Message, state: FSMContext, locale: dict, language: str) -> None:
    data = await state.get_data()
    items_text, _ = format_items(data["items"], language, locale)
    summary = locale["confirm_data"].format(
        name=data["name"], phone=data["phone"], address=data["address"],
        items=items_text, comment=data.get("comment") or "-",
    )
    await state.set_state(OrderForm.confirm)
    await message.answer(
        f"{locale['confirm_title']}\n\n{summary}",
        reply_markup=confirmation_keyboard(locale),
    )


@router.message(F.text.in_(_ORDER_TEXTS))
async def begin_order(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    locale = await _locale(db, message.from_user.id)
    await state.set_state(OrderForm.name)
    await state.update_data(items=[])
    await message.answer(locale["ask_name"], reply_markup=navigation(locale))


@router.message(StateFilter(*_NAV_STATES), F.text.in_(_NAV_ACTIONS))
async def order_navigation(message: Message, state: FSMContext, db: Database) -> None:
    current = await state.get_state()
    locale = await _locale(db, message.from_user.id)
    text = message.text
    back_texts = {get_locale(language)["back"] for language in SUPPORTED_LANGUAGES}
    cancel_texts = {get_locale(language)["cancel"] for language in SUPPORTED_LANGUAGES}
    if text in cancel_texts:
        await state.clear()
        await message.answer(locale["order_cancelled"], reply_markup=main_menu(locale))
        return
    data = await state.get_data()
    transitions = {
        OrderForm.name.state: (None, None),
        OrderForm.phone.state: (OrderForm.name, "ask_name"),
        OrderForm.address.state: (OrderForm.phone, "ask_phone"),
        OrderForm.item_type.state: (OrderForm.items_done, None) if data.get("items") else (OrderForm.address, "ask_address"),
        OrderForm.item_size.state: (OrderForm.item_type, "ask_type"),
        OrderForm.item_quantity.state: (OrderForm.item_size, "ask_size"),
        OrderForm.items_done.state: (OrderForm.item_type, "ask_type"),
        OrderForm.comment.state: (OrderForm.items_done, None),
        OrderForm.photo.state: (OrderForm.comment, "ask_comment"),
        OrderForm.confirm.state: (OrderForm.photo, "ask_photo"),
    }
    next_state, prompt_key = transitions[current]
    if next_state is None:
        await state.clear()
        await message.answer(locale["order_cancelled"], reply_markup=main_menu(locale))
        return
    await state.set_state(next_state)
    if next_state == OrderForm.items_done:
        await _ask_items_done(message, locale)
    elif prompt_key == "ask_phone":
        await message.answer(locale[prompt_key], reply_markup=contact_keyboard(locale))
    elif prompt_key == "ask_address":
        await message.answer(locale[prompt_key], reply_markup=address_keyboard(locale))
    elif prompt_key == "ask_type":
        await _ask_type(message, locale)
    elif prompt_key in ("ask_size", "ask_quantity"):
        await message.answer(locale[prompt_key], reply_markup=navigation(locale))
    elif prompt_key == "ask_photo":
        await message.answer(locale[prompt_key], reply_markup=skip_keyboard(locale))
    else:
        await message.answer(locale[prompt_key], reply_markup=navigation(locale))


@router.message(OrderForm.name, F.text)
async def get_name(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    name = message.text.strip()
    if sum(character.isalpha() for character in name) < 2:
        await message.answer(locale["bad_name"], reply_markup=navigation(locale))
        return
    await state.update_data(name=name)
    await state.set_state(OrderForm.phone)
    await message.answer(locale["ask_phone"], reply_markup=contact_keyboard(locale))


async def _save_phone(message: Message, state: FSMContext, db: Database, phone: str) -> None:
    locale = await _locale(db, message.from_user.id)
    normalized = normalize_phone(phone)
    if not normalized:
        await message.answer(locale["bad_phone"], reply_markup=contact_keyboard(locale))
        return
    await state.update_data(phone=normalized)
    await state.set_state(OrderForm.address)
    await message.answer(locale["ask_address"], reply_markup=address_keyboard(locale))


@router.message(OrderForm.phone, F.contact)
async def get_contact(message: Message, state: FSMContext, db: Database) -> None:
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        locale = await _locale(db, message.from_user.id)
        await message.answer(locale["bad_phone"], reply_markup=contact_keyboard(locale))
        return
    await _save_phone(message, state, db, message.contact.phone_number)


@router.message(OrderForm.phone, F.text)
async def get_phone(message: Message, state: FSMContext, db: Database) -> None:
    await _save_phone(message, state, db, message.text)


@router.message(OrderForm.address, F.location)
async def get_location(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    latitude, longitude = message.location.latitude, message.location.longitude
    await state.update_data(
        address=f"{latitude:.6f}, {longitude:.6f}", latitude=latitude, longitude=longitude
    )
    await state.set_state(OrderForm.item_type)
    await _ask_type(message, locale)


@router.message(OrderForm.address, F.text)
async def get_address(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    manual_texts = {get_locale(language)["manual"] for language in SUPPORTED_LANGUAGES}
    address = message.text.strip()
    if address in manual_texts:
        await message.answer(locale["ask_address"], reply_markup=navigation(locale))
        return
    if len(address) < 3:
        await message.answer(locale["bad_address"], reply_markup=address_keyboard(locale))
        return
    await state.update_data(address=address, latitude=None, longitude=None)
    await state.set_state(OrderForm.item_type)
    await _ask_type(message, locale)


@router.message(OrderForm.item_type, F.text)
async def get_item_type(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    item_type = item_type_from_label(message.text)
    if not item_type:
        await message.answer(locale["ask_type"], reply_markup=item_type_keyboard(locale))
        return
    await state.update_data(current_type=item_type)
    await state.set_state(OrderForm.item_size)
    await message.answer(locale["ask_size"], reply_markup=navigation(locale))


@router.message(OrderForm.item_size, F.text)
async def get_item_size(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    size = parse_size(message.text)
    if not size:
        await message.answer(locale["bad_size"], reply_markup=navigation(locale))
        return
    width, length = size
    await state.update_data(current_width=width, current_length=length)
    await state.set_state(OrderForm.item_quantity)
    await message.answer(locale["ask_quantity"], reply_markup=navigation(locale))


@router.message(OrderForm.item_quantity, F.text)
async def get_item_quantity(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    if not message.text.strip().isdigit() or not 1 <= int(message.text.strip()) <= 10000:
        await message.answer(locale["bad_quantity"], reply_markup=navigation(locale))
        return
    data = await state.get_data()
    items = data.get("items", [])
    width, length = data["current_width"], data["current_length"]
    items.append({
        "type": data["current_type"], "width": width, "length": length,
        "quantity": int(message.text.strip()), "area": width * length,
    })
    await state.update_data(items=items)
    await state.set_state(OrderForm.items_done)
    await _ask_items_done(message, locale)


@router.message(OrderForm.items_done, F.text)
async def items_done(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    add_texts = {get_locale(language)["add_more"] for language in SUPPORTED_LANGUAGES}
    done_texts = {get_locale(language)["finish_items"] for language in SUPPORTED_LANGUAGES}
    if message.text in add_texts:
        await state.set_state(OrderForm.item_type)
        await _ask_type(message, locale)
    elif message.text in done_texts:
        await _ask_comment(message, state, locale)
    else:
        await _ask_items_done(message, locale)


@router.message(OrderForm.comment, F.text)
async def get_comment(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    skip_texts = {get_locale(language)["skip"] for language in SUPPORTED_LANGUAGES}
    comment = "" if message.text in skip_texts else message.text.strip()
    await state.update_data(comment=comment)
    await state.set_state(OrderForm.photo)
    await message.answer(locale["ask_photo"], reply_markup=skip_keyboard(locale))


async def _show_confirm_after_photo(message: Message, state: FSMContext, db: Database) -> None:
    language = await db.get_language(message.from_user.id)
    locale = get_locale(language)
    await _show_confirmation(message, state, locale, language)


@router.message(OrderForm.photo, F.photo)
async def get_photo(message: Message, state: FSMContext, db: Database) -> None:
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await _show_confirm_after_photo(message, state, db)


@router.message(OrderForm.photo, F.text)
async def skip_photo(message: Message, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    skip_texts = {get_locale(language)["skip"] for language in SUPPORTED_LANGUAGES}
    if message.text not in skip_texts:
        await message.answer(locale["bad_photo"], reply_markup=skip_keyboard(locale))
        return
    await state.update_data(photo_file_id=None)
    await _show_confirm_after_photo(message, state, db)


async def _send_staff_copy(message: Message, db: Database, settings: Settings, order: dict) -> None:
    locale = get_locale("uz")
    items_text, total_area = format_items(order["items"], "uz", locale)
    if order["latitude"] is not None and order["longitude"] is not None:
        map_url = f"https://maps.google.com/?q={order['latitude']},{order['longitude']}"
    else:
        map_url = f"https://maps.google.com/?q={quote(order['address'])}"
    text = locale["operator_new"].format(
        order_id=order["id"], name=order["customer_name"], phone=order["phone"],
        address=order["address"], map=map_url, items=items_text, area=f"{total_area:.2f}",
        comment=order["comment"] or "-", date=order["created_at"].replace("T", " ") + " UTC",
    )
    destinations = set(settings.admin_ids) | await db.operator_ids()
    if settings.channel_id is not None:
        destinations.add(settings.channel_id)
    for chat_id in destinations:
        try:
            sent = await message.bot.send_message(chat_id, text, reply_markup=operator_keyboard(order, locale))
            await db.save_order_message(order["id"], chat_id, sent.message_id)
            if order["latitude"] is not None and order["longitude"] is not None:
                await message.bot.send_location(chat_id, order["latitude"], order["longitude"])
            if order["photo_file_id"]:
                await message.bot.send_photo(
                    chat_id, order["photo_file_id"],
                    caption=locale["photo_caption"].format(order_id=order["id"]),
                )
        except (TelegramAPIError, TypeError, ValueError):
            logger.exception("Buyurtma nusxasini %s chatiga yuborib bo'lmadi", chat_id)


@router.callback_query(F.data == "order:confirm", OrderForm.confirm)
async def confirm_order(callback: CallbackQuery, state: FSMContext, db: Database, settings: Settings) -> None:
    data = await state.get_data()
    language = await db.get_language(callback.from_user.id)
    locale = get_locale(language)
    try:
        order_id = await db.create_order(
            user_id=callback.from_user.id, customer_name=data["name"], phone=data["phone"],
            address=data["address"], latitude=data.get("latitude"), longitude=data.get("longitude"),
            comment=data.get("comment", ""), photo_file_id=data.get("photo_file_id"),
            items=data["items"], rate_limit_seconds=settings.rate_limit_seconds,
            first_name=callback.from_user.first_name, username=callback.from_user.username,
        )
    except RateLimited as error:
        minutes = max(1, math.ceil(error.wait_seconds / 60))
        await callback.answer(locale["rate_limited"].format(minutes=minutes), show_alert=True)
        return
    except Exception:
        logger.exception("Buyurtma saqlanmadi: user=%s", callback.from_user.id)
        await callback.answer(locale["order_failed"], show_alert=True)
        return

    order = await db.get_order(order_id)
    await _send_staff_copy(callback.message, db, settings, order)
    await callback.answer()
    await callback.message.answer(
        locale["order_saved"].format(order_id=order_id), reply_markup=main_menu(locale)
    )
    await state.clear()


@router.callback_query(F.data == "order:cancel", OrderForm.confirm)
async def cancel_confirmed_order(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    locale = await _locale(db, callback.from_user.id)
    await state.clear()
    await callback.answer()
    await callback.message.answer(locale["order_cancelled"], reply_markup=main_menu(locale))


@router.message(OrderForm.photo)
async def invalid_photo(message: Message, db: Database) -> None:
    locale = await _locale(db, message.from_user.id)
    await message.answer(locale["bad_photo"], reply_markup=skip_keyboard(locale))
