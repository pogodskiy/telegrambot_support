import json

import openai
from aiogram import Bot, Dispatcher, types, executor
import logging
import os
import aioredis
from aiogram.contrib.fsm_storage.redis import RedisStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import redis
from dotenv import load_dotenv
from db.createdb import conn, cur
import asyncio

storage = MemoryStorage()

logging.basicConfig(level=logging.INFO)
load_dotenv()

r = redis.Redis(host='localhost', port=6379, db=0)

bot = Bot(token=os.getenv("GPT_BOT_TOKEN"))
dp = Dispatcher(bot, storage=storage)
openai.api_key = os.getenv("OPENAI_TOKEN")

gpt_name_db = ''
user_name_db = ''
user_id = ''


class FAQForm(StatesGroup):
    chat_gpt = State()
    chat_admin = State()
    chat_admin1 = State()
    chat_admin2 = State()
    chat_admin_wait = State()
    back_menu = State()
    close = State()


# стартовый экран

@dp.message_handler(Command("start"))
async def start(message: types.Message):
    global user_id
    global user_name_db
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.KeyboardButton(text='FAQ', callback_data='faq')
    button2 = types.KeyboardButton(text='Техподдержка', callback_data='support')
    welcome_message = """
        Приветствую! Я бот техподдержки условного ресурса.
        Ты можешь ознакомиться с наиболее частыми проблемами, нажав на кнопку FAQ, или пообщаться с техподдержкой на прямую, нажав "Техподдержка".
        """
    # динамически создаем бд, для пользователя, который начал диалог
    keyboard.add(button1, button2)
    await message.answer(welcome_message, reply_markup=keyboard)
    user_name_db = message.from_user.username.lower()

    cur.execute(
        "INSERT INTO users (user_name) SELECT %s WHERE NOT EXISTS (SELECT 1 FROM users WHERE user_name = %s) RETURNING id",
        (user_name_db, user_name_db))
    row = cur.fetchone()
    if row is not None:
        user_id = int(row[0])
    else:
        # Пользователь уже существует, получаем его id
        cur.execute("SELECT id FROM users WHERE user_name = %s", (user_name_db,))
        row = cur.fetchone()
        user_id = int(row[0])
    create_table = f"""
        CREATE TABLE IF NOT EXISTS {user_name_db} (
            id SERIAL PRIMARY KEY,
            user_id INT,
            message_id BIGINT,
            user_name TEXT,
            question TEXT,
            answer TEXT,
            status_message INTEGER DEFAULT 2,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """
    cur.execute(f"UPDATE users SET status_chat = 1")
    conn.commit()

    cur.execute(create_table)
    conn.commit()


@dp.callback_query_handler(lambda c: c.data == 'faq', state='*')
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


@dp.callback_query_handler(lambda c: c.data == 'support', state='*')
async def support(call: types.CallbackQuery):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Чат с ChatGPT')
    button2 = types.KeyboardButton('Чат с администратором')
    keyboard.add(button1, button2)
    await call.message.answer('Ниже выберите с кем хотите вести диалог', reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Чат с ChatGPT", state='*')
async def start_chat_whit_gpt(message: types.Message):
    global gpt_name_db
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    gpt_name_db = message.from_user.username.lower() + "_gpt"
    create_table_gpt = f"""
            CREATE TABLE IF NOT EXISTS {gpt_name_db} (
                id SERIAL PRIMARY KEY,
                gpt_id INT,
                question TEXT,
                answer TEXT,
                FOREIGN KEY (gpt_id) REFERENCES users(id)
            );
    """
    cur.execute(f"UPDATE users SET status_chat_gpt = 1 WHERE user_name = '{message.from_user.username.lower()}'")

    conn.commit()
    cur.execute(create_table_gpt)
    conn.commit()
    await message.answer("Диалог с чатом GPT активирован. Что Вы хотели спросить?", reply_markup=keyboard)
    await FAQForm.chat_gpt.set()


@dp.message_handler(state=FAQForm.chat_gpt)
async def chat_gpt(message: types.Message, state: FSMContext):
    if message.text != 'Вернуться в главное меню':
        # response = openai.Completion.create(
        #     model="text-davinci-002",
        #     prompt=message.text,
        #     temperature=0.9,
        #     max_tokens=150,
        #     top_p=1,
        #     frequency_penalty=0.0,
        #     presence_penalty=0.6
        # )
        response = 'Hello'
        cur.execute(f"SELECT id FROM users WHERE user_name = '{user_name_db}'")
        user_id = cur.fetchone()[0]
        cur.execute(f"INSERT INTO {gpt_name_db} (gpt_id, question, answer) VALUES (%s, %s, %s)",
                    (user_id, message.text, response))
        conn.commit()
        print(message)
        await message.answer(response)
        await message.answer('asd')
        print(message)

    else:
        await state.finish()
        await start(message)


@dp.message_handler(lambda message: message.text == "Чат с администратором", state='*')
async def start_chat_admin(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    button2 = types.KeyboardButton('Закрыть диалог')
    keyboard.add(button1, button2)
    await message.answer("Теперь вы можете общаться с администратором.", reply_markup=keyboard)
    await FAQForm.chat_admin.set()


online = True

listen_to_redis = False


@dp.message_handler(state=FAQForm.chat_admin)
async def user_chat_message(message: types.Message, state: FSMContext):
    print('старт')
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    button2 = types.KeyboardButton('Закрыть диалог')
    keyboard.add(button1, button2)
    await message.answer('Чат activated', reply_markup=keyboard)
    await FAQForm.chat_admin1.set()


chat_id = ''
import redis
import time

# Создание подключения к Redis
r = redis.Redis()


import asyncio

# Создайте асинхронный лок
lock = asyncio.Lock()

@dp.message_handler(state=FAQForm.chat_admin1)
async def process_messages(message: types.Message):
    print('начало')

    async def send_messages():
        while True:
            async with lock:
                # Проверяем наличие сообщений
                messages = r.lrange(user_name_db, 0, -1)
                if messages:
                    for msg in messages:
                        decoded_msg = eval(msg.decode())
                        if decoded_msg.get('chat') == user_name_db and decoded_msg.get('reply') and decoded_msg.get(
                                'from') == 'admin':
                            message_text = decoded_msg.get('text')
                            print(msg)
                            print(message)
                            await bot.send_message(chat_id=message.chat.id, text=message_text,
                                                   reply_to_message_id=decoded_msg.get('reply'))
                        elif decoded_msg.get('admin') == user_name_db and decoded_msg.get('reply') is None and decoded_msg.get(
                                'from') == 'user':
                            message_text = decoded_msg.get('text')
                            print(msg)
                            print(message)
                            await message.answer(message_text)
                    r.delete(user_name_db)
            await asyncio.sleep(1)

    # Запускаем функцию send_messages() в фоновом режиме
    asyncio.create_task(send_messages())

    # Добавляем сообщение только если его нет в Redis
    messages = r.lrange(user_name_db, 0, -1)
    if not any(message.text.encode() == eval(msg.decode()).get('text') for msg in messages):
        async with lock:
            if message.reply_to_message and message.reply_to_message.message_id:
                msg = {'text': message.text, 'message_id': message.message_id, 'chat': user_name_db, 'from': 'user',
                       'reply': message.reply_to_message.message_id}
            else:
                msg = {'text': message.text, 'message_id': message.message_id, 'chat': user_name_db, 'from': 'user',
                       'reply': None}
            r.rpush(user_name_db, str(msg))
            print(message.text.encode())
            print(msg.get('chat'))


# import psutil
#
# # Получение списка всех процессов
# processes = psutil.process_iter()
#
# # Печать информации о каждом процессе
# for process in processes:
#     print(process)
#
#
#
# # Получение списка всех потоков в процессе
# threads = process.threads()
# print(threads)

@dp.message_handler(lambda message: message.text == 'Закрыть диалог', state=[FAQForm.close, '*'])
async def close_dialog(message: types.Message, state: FSMContext):
    await message.answer('Диалог закрыт. Спасибо, что обратились к нам. Для возобновления диалога нажмите /start')
    rows = cur.fetchall()
    if rows:
        cur.execute(f"DROP TABLE {gpt_name_db}")
    conn.commit()
    cur.execute(f"UPDATE users SET status_chat = 0, status_chat_gpt = 0 WHERE user_name = '{user_name_db}'")
    conn.commit()
    await state.finish()


@dp.message_handler(lambda message: message.text == 'Вернуться в главное меню', state=['*', FAQForm.back_menu])
async def back_to_menu(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardRemove()
    await message.answer("Вы вернулись в главное меню.", reply_markup=keyboard)
    await state.finish()
    await start(message)


if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.create_task(process_messages())
    executor.start_polling(dp, skip_updates=True)
