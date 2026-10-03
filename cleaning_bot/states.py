from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    name = State()
    phone = State()
    address = State()
    item_type = State()
    item_size = State()
    item_quantity = State()
    items_done = State()
    comment = State()
    photo = State()
    confirm = State()


class AdminForm(StatesGroup):
    add_operator = State()
    remove_operator = State()
    broadcast = State()
