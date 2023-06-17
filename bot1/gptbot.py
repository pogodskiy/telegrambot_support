from aiogram import Bot, Dispatcher, types, executor
import logging
import os

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

class ChatState:
    WithAdmin = "with_admin"

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

@dp.message_handler(text="Чат с администратором")
async def start_chat_admin(message: types.Message, state: FSMContext):
    await state.set_state(ChatState.WithAdmin)

    # Добавляем сообщение пользователя в базу данных
    if message.text != 'Чат с администратором':
        cur.execute("INSERT INTO user_messages (user_id, user_name, question) VALUES (%s, %s, %s)",
                (message.from_user.id, message.from_user.username, message.text))
        conn.commit()

    await message.answer("Теперь вы можете общаться с администратором.")

dp.message_handler()

@dp.message_handler(lambda message: message.text == 'Вернуться в главное меню', state='*')
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message)

@dp.message_handler(state=ChatState.WithAdmin)
async def chat_with_admin(message: types.Message):
    # admin_chat_id = os.getenv('ADMIN_CHAT_ID')

    # Отправляем сообщение пользователя администратору
    # await admin_bot.send_message(chat_id=admin_chat_id, text=message.text)

    # Добавляем сообщение пользователя в базу данных
    cur.execute("INSERT INTO user_messages (user_id, user_name, question) VALUES (%s, %s, %s)",
                (message.from_user.id, message.from_user.username, message.text))
    conn.commit()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)