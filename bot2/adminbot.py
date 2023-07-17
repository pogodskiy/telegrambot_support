import asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import executor
import re
import logging
import os
from db.createdb import cur, conn
from aiogram.contrib.fsm_storage.redis import RedisStorage
import redis

# Создание подключения к Redis
r = redis.Redis(host='localhost', port=6379, db=0)

logging.basicConfig(level=logging.INFO)
load_dotenv()

bot = Bot(token=os.getenv("ADMIN_TOKEN"))
storage = RedisStorage(host='localhost', port=6379)
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

user_name_db = ''
gpt_name_db = ''
names = ''


class FAQForm(StatesGroup):
    question = State()
    answer = State()
    deleted = State()
    update_n = State()
    update_q = State()
    update_a = State()
    chat = State()
    chat_with_user = State()
    save_db_name = State()
    chat_a = State()
    chat_q = State()
    close = State()


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.KeyboardButton(text='FAQ', callback_data='faq')
    button2 = types.KeyboardButton(text='Chat', callback_data='chats')
    welcome_message = """
           Выберите действие
           """
    keyboard.add(button1)
    keyboard.add(button2)
    await message.answer(welcome_message, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'faq')
async def faq(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.KeyboardButton(text='add FAQ', callback_data='add_faq')
    button2 = types.KeyboardButton(text='del FAQ', callback_data='del_faq')
    button3 = types.KeyboardButton(text='update FAQ', callback_data='up_faq')
    keyboard.add(button1, button3, button2)
    await call.message.answer('Панель администрации FAQ', reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'add_faq')
async def add_faq(call: types.CallbackQuery):
    await FAQForm.question.set()  # установка состояния question
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    await call.message.answer("Введите вопрос", reply_markup=keyboard)


@dp.message_handler(state=FAQForm.question)  # хендлер сработает при состоянии question
async def add_question(message: types.Message, state: FSMContext):
    async with state.proxy() as data:  # сохраняем данные в состояния question
        data['question'] = message.text
        await message.answer('Введите ответ')
        question = data['question']
        if question == 'Вернуться в главное меню':
            await message.answer('Возврат в главное меню')
            await state.finish()  # выход из состояния
            await start(message)  # вывод стартого экрана
        else:
            await FAQForm.answer.set()  # установка состояния answer


@dp.message_handler(state=FAQForm.answer)
async def add_answer(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        question = data['question']
        answer = message.text
        cur.execute("INSERT INTO faq (question, answer) VALUES (%s, %s)", (question, answer))
        conn.commit()  # добавление в БД вопроса и ответа

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton('Вернуться в главное меню')
        keyboard.add(button1)
        await message.answer('Вопрос и ответ добавлены', reply_markup=keyboard)

    await state.finish()
    await start(message)


@dp.callback_query_handler(lambda c: c.data == 'up_faq')
async def update_faq(call: types.CallbackQuery):
    cur.execute("SELECT * FROM faq")
    rows = cur.fetchall()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    if rows:
        for row in rows:
            await call.message.answer(f"{row[0]}. Вопрос - {row[1]} Ответ - {row[2]}")
        await call.message.answer("Введите номер вопроса и ответа, который хотите изменить", reply_markup=keyboard)
        await FAQForm.update_n.set()
    else:
        await call.message.answer('Нет доступных вопросов для удаления', reply_markup=keyboard)


@dp.message_handler(state=FAQForm.update_n)
async def question_number(message: types.Message, state: FSMContext):
    question_number = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    async with state.proxy() as data:  # сохраняем данные в состояния question
        data['question_number'] = question_number
        if question_number == 'Вернуться в главное меню':
            await message.answer('Возврат в главное меню', reply_markup=keyboard)
            await state.finish()
            await start(message)
        elif question_number.isdigit():
            await message.answer("Введите новый вопрос")
            await FAQForm.update_q.set()
        else:
            await message.answer('Неверный формат ввода', reply_markup=keyboard)


@dp.message_handler(state=FAQForm.update_q)
async def update_question(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    async with state.proxy() as data:
        question_number = data['question_number']
        question_text = message.text
        if question_number.isdigit():
            cur.execute("SELECT * FROM faq WHERE id = %s", (int(question_number),))
            row = cur.fetchone()
            if row:
                cur.execute(f"UPDATE faq SET question = '{question_text}' WHERE id = %s", ((int(question_number),),))
                conn.commit()
                await FAQForm.update_a.set()
                await message.answer("Введите новый ответ")
            else:
                await message.answer('Неверный номер вопроса', reply_markup=keyboard)
        else:
            if question_number == 'Вернуться в главное меню':
                await message.answer('Возврат в главное меню', reply_markup=keyboard)
                await state.finish()
                await start(message)
            else:
                await message.answer('Неверный формат ввода', reply_markup=keyboard)


@dp.message_handler(state=FAQForm.update_a)
async def update_answer(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        question_number = data['question_number']
        answer_text = message.text
        cur.execute("SELECT * FROM faq WHERE id = %s", (int(question_number),))
        row = cur.fetchone()
        if row:
            cur.execute(
                f"UPDATE faq SET answer = '{answer_text}' WHERE id = %s", (int(question_number),))
            conn.commit()
            await message.answer('Изменения внесены.')
        await state.finish()
        await start(message)


@dp.callback_query_handler(lambda c: c.data == 'del_faq')
async def delete_faq(call: types.CallbackQuery):
    cur.execute("SELECT * FROM faq")
    rows = cur.fetchall()

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)

    # вывод всех вопросов и ответов из БД
    if rows:
        await call.message.answer('Какой вопрос хотите удалить?')
        for row in rows:
            await call.message.answer(f"{row[0]}. вопрос - {row[1]}, ответ - {row[2]}")
        await call.message.answer("Введите номер вопроса и ответа, который хотите удалить", reply_markup=keyboard)
        await FAQForm.deleted.set()
    else:
        await call.message.answer('Нет доступных вопросов для удаления', reply_markup=keyboard)


@dp.message_handler(state=FAQForm.deleted)  # удаление вопроса и ответа из FAQ
async def confirm_delete(message: types.Message, state: FSMContext):
    question_number = message.text.strip()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)

    if question_number.isdigit():
        cur.execute("SELECT * FROM faq WHERE id = %s", (int(question_number),))
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM faq WHERE id = %s", (int(question_number),))
            conn.commit()
            await message.answer(f'Запись с вопросом "{row[1]}" удалена', reply_markup=keyboard)
        else:
            await message.answer('Неверный номер вопроса', reply_markup=keyboard)
    else:
        if question_number == 'Вернуться в главное меню':
            await message.answer('Возврат в главное меню')
            await state.finish()
            await start(message)
        else:
            await message.answer('Неверный номер вопроса', reply_markup=keyboard)

    await state.finish()
    await FAQForm.deleted.set()


@dp.callback_query_handler(lambda c: c.data == 'chats', state='*')
async def chats(call: types.CallbackQuery):
    cur.execute("SELECT count(id), status_chat FROM users WHERE status_chat = 1 GROUP BY status_chat")
    open = cur.fetchall()
    cur.execute("SELECT count(id), status_chat FROM users WHERE status_chat = 0 GROUP BY status_chat")
    close = cur.fetchall()
    if open:
        open_chats = open[0][0]
    else:
        open_chats = 0
    if close:
        close_chats = close[0][0]
    else:
        close_chats = 0

    keyboard = types.InlineKeyboardMarkup()
    button1 = types.KeyboardButton(text=f'Активных чатов - {open_chats}', callback_data='open')
    button2 = types.KeyboardButton(text=f'Закрытых чатов - {close_chats}', callback_data='close')
    button3 = types.KeyboardButton(text='Вернуться в главное меню', callback_data='exit')
    keyboard.add(button1)
    keyboard.add(button2)
    keyboard.add(button3)
    await call.message.answer("Выберите нужный тип чатов", reply_markup=keyboard)


@dp.callback_query_handler(text='open', state='*')
async def chat_with_user(call: types.CallbackQuery, state: FSMContext):
    global names

    cur.execute("SELECT user_name FROM users WHERE status_chat = 1")
    user_names = cur.fetchall()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Вернуться в главное меню'))
    names = ''
    if user_names:
        await call.message.answer("Выберите пользователя, с которым хотите вести диалог", reply_markup=keyboard)
        for name in user_names:
            new_name = str(re.sub(r"['(),]", "", name[0] + '\n'))
            names += new_name
        await call.message.answer(names)
    else:
        await call.message.answer("Нет активных чатов", reply_markup=keyboard)
    await FAQForm.chat.set()


@dp.message_handler(state=FAQForm.chat)
async def user_chat(message: types.Message, state: FSMContext):
    global user_name_db
    global gpt_name_db
    if message.text in ('Вернуться в главное меню',):
        await state.finish()
        await start(message)

    elif message.text not in ('Вернуться в главное меню', 'Закрыть диалог'):
        if message.text in names:
            user_name_db = message.text.lower()
            gpt_name_db = f"{user_name_db}_gpt"
        else:
            await message.answer('Ошибка в имени')
        cur.execute("SELECT status_chat_gpt FROM users WHERE user_name = %s", (user_name_db,))
        rows = cur.fetchall()
        keyboard = types.InlineKeyboardMarkup()
        for row in rows:
            status_gpt = row[0]
            if status_gpt == 1:
                button1 = types.InlineKeyboardButton(text=f'Просмотреть чат с GPT', callback_data='user_gpt')
                keyboard.add(button1)
        button2 = types.InlineKeyboardButton(text=f'Диалог с {user_name_db}',
                                             callback_data=f'{user_name_db}')
        keyboard.add(button2)
        await state.finish()
        await message.answer("Выберите действия", reply_markup=keyboard)

# Создайте асинхронный лок
lock = asyncio.Lock()
# @dp.callback_query_handler(lambda c: c.data == f'{user_name_db}', state='*')
# async def user_chat_message(call: types.CallbackQuery, state: FSMContext):
#     await FAQForm.chat_with_user()
# @dp.message_handler(state=FAQForm.chat_with_user)
# async def process_messages(message: types.Message):
#     print('начало')
#
#     async def send_messages():
#         while True:
#             async with lock:
#                 # Проверяем наличие сообщений
#                 messages = r.lrange(user_name_db, 0, -1)
#                 if messages:
#                     for msg in messages:
#                         decoded_msg = eval(msg.decode())
#                         if decoded_msg.get('chat') == user_name_db and decoded_msg.get('reply') and decoded_msg.get(
#                                 'from') == 'user':
#                             message_text = decoded_msg.get('text')
#                             print(msg)
#                             print(message)
#                             await bot.send_message(chat_id=message.chat.id, text=message_text,
#                                                    reply_to_message_id=decoded_msg.get('reply'))
#                         elif decoded_msg.get('chat') == user_name_db and decoded_msg.get('reply') is None and decoded_msg.get(
#                                 'from') == 'user':
#                             message_text = decoded_msg.get('text')
#                             print(msg)
#                             print(message)
#                             await message.answer(message_text)
#                     r.delete(user_name_db)
#             await asyncio.sleep(1)
#
#     # Запускаем функцию send_messages() в фоновом режиме
#     asyncio.create_task(send_messages())
#
#     # Добавляем сообщение только если его нет в Redis
#     messages = r.lrange(user_name_db, 0, -1)
#     if not any(message.text.encode() == eval(msg.decode()).get('text') for msg in messages):
#         async with lock:
#             if message.reply_to_message and message.reply_to_message.message_id:
#                 msg = {'text': message.text, 'message_id': message.message_id, 'chat': user_name_db, 'from': 'admin',
#                        'reply': message.reply_to_message.message_id}
#             else:
#                 msg = {'text': message.text, 'message_id': message.message_id, 'chat': user_name_db, 'from': 'admin',
#                        'reply': None}
#             r.rpush(user_name_db, str(msg))
#             print(message.text.encode())
#             print(msg.get('chat'))

@dp.callback_query_handler(lambda c: c.data == 'user_gpt', state='*')
async def check_gpt_dialog(call: types.CallbackQuery):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    await call.message.answer("Диалог с GPT", reply_markup=keyboard)
    cur.execute(f"SELECT question, answer FROM {gpt_name_db}")
    rows = cur.fetchall()
    for row in rows:
        question = row[0]
        answer = row[1]
        await call.message.answer(f'- {question}\n '
                                  f'- {answer}')
    keyboard2 = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Чат с пользователем", callback_data='user_chat_callback')
    keyboard2.add(button)
    await call.message.answer(f"Можете перейти в диалог с пользователем", reply_markup=keyboard2)


@dp.message_handler(state=FAQForm.chat_a)
async def add_answer(message: types.Message, state: FSMContext):
    if message.text in ('Закрыть диалог'):
        await state.finish()
        await FAQForm.close.set()
    elif message.text in ('Вернуться в главное меню'):
        await state.finish()
        await start(message)


@dp.callback_query_handler(lambda c: c.data == 'back')
async def back(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await start(call.message)


@dp.message_handler(lambda message: message.text == 'Закрыть диалог', state=[FAQForm.close, '*'])
async def close_dialog(message: types.Message, state: FSMContext):
    await message.answer('Диалог закрыт')
    rows = cur.fetchall()
    if rows:
        cur.execute(f"DROP TABLE {gpt_name_db}")
    conn.commit()
    cur.execute(f"UPDATE users SET status_chat = 0, status_chat_gpt = 0 WHERE user_name = '{user_name_db}'")
    conn.commit()
    await state.finish()
    await start(message)


# при любом состоянии фраза вернуться в главное меню выдает стартовое сообщение с выбором действий
@dp.message_handler(lambda message: message.text == 'Вернуться в главное меню', state='*')
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message)


loop = asyncio.get_event_loop()

# Запускаем приложение
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

