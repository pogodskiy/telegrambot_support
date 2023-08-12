from aiogram.dispatcher.filters.state import State, StatesGroup

class StatusForm(StatesGroup):
    chat_gpt = State()
    chat_start = State()
    chat_admin = State()
    chat_admin1 = State()
    chat_admin2 = State()
    chat_admin_wait = State()
    back_menu = State()
    close = State()