from aiogram import Bot, Dispatcher, types, executor
import logging
import os
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from db.createdb import conn, cur

storage = MemoryStorage()

logging.basicConfig(level=logging.INFO)
load_dotenv()

bot = Bot(token=os.getenv("GPT_BOT_TOKEN"))
admin_bot = Bot(token=os.getenv("ADMIN_TOKEN"))
dp = Dispatcher(bot, storage=storage)


class FAQForm(StatesGroup):
    chat_admin = State()
    chat_admin_wait = State()
    back_menu = State()


# стартовый экран
@dp.message_handler(Command("start"))
async def start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.KeyboardButton(text='FAQ', callback_data='faq')
    button2 = types.KeyboardButton(text='Техподдержка', callback_data='support')
    welcome_message = """
        Приветствую! Я бот техподдержки условного ресурса.
        Ты можешь ознакомиться с наиболее частыми проблемами, нажав на кнопку FAQ, или пообщаться с техподдержкой на прямую, нажав "Техподдержка".
        """
    keyboard.add(button1, button2)
    await message.answer(welcome_message, reply_markup=keyboard)
    await bot.send_message(message.from_user.id, message.chat.id)

@dp.callback_query_handler(lambda c: c.data == 'faq')
async def faq(call: types.CallbackQuery):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    cur.execute("SELECT * FROM faq")
    faq_text = cur.fetchall()
    if faq_text:
        # вывод faq
        for num, faq in enumerate(faq_text, start=1):
            await call.message.answer(f"{num}. Вопрос - {faq[1]}\n"
                                      f"   Ответ - {faq[2]}\n", reply_markup=keyboard)
    else:
        await call.message.answer("Здесь пока нету вопросов \U0001F62A", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'support')
async def support(call: types.CallbackQuery):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Чат с ChatGPT')
    button2 = types.KeyboardButton('Чат с администратором')
    keyboard.add(button1, button2)
    await call.message.answer('Ниже выберите с кем хотите вести диалог', reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "Чат с администратором")
async def start_chat_admin(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    await message.answer("Теперь вы можете общаться с администратором.", reply_markup=keyboard)
    await FAQForm.chat_admin.set()
    # Добавляем сообщение пользователя в базу данных




@dp.message_handler(state=FAQForm.chat_admin)
async def chat_admin(message: types.Message):
    if message.text == 'Вернуться в главное меню':
        FAQForm.back_menu.set()

    elif message.text != ('Чат с администратором'):
        cur.execute("INSERT INTO user_messages (user_id, chat_id, user_name, question) VALUES (%s, %s, %s, %s)",
                    (message.from_user.id, message.chat.id, message.from_user.username, message.text))
        conn.commit()
        await FAQForm.chat_admin_wait.set()

import re

@dp.message_handler(state=FAQForm.chat_admin_wait)
async def admin_answer(message: types.Message):
    cur.execute("SELECT answer FROM user_messages WHERE status_message = 1")
    rows = cur.fetchall()
    answers = ''
    if rows:
        for answer in rows:
            new_answer = str(re.sub(r"['(),]", "", answer[0] + '\n'))
            if new_answer not in answers:
                answers += new_answer
            cur.execute(
                f"UPDATE user_messages SET status_message = 0 "
                f"WHERE user_name = '{message.from_user.username}' "
                f"AND status_message = 1 "
            )
        await message.answer(answers)

    await FAQForm.chat_admin.set()

@dp.message_handler(lambda message: message.text == 'Закрыть диалог', state=FAQForm.close)
async def close_dialog(message: types.Message, state: FSMContext):
    await message.answer('Диалог закрыт')
    data = await state.get_data()
    user_name = data.get("user_name")
    print(user_name)
    cur.execute(f"UPDATE user_messages SET status_chat=0 WHERE user_name = '{user_name}'")
    conn.commit()
    await state.reset_state(with_data=False)  # Сбросить состояние без удаления данных
    await start(message)



@dp.message_handler(lambda message: message.text == 'Вернуться в главное меню', state='*' or FAQForm.back_menu)
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)