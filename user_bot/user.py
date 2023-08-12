from datetime import timedelta
import openai
from aiogram import Bot, Dispatcher, types, executor
import logging
import os
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from states import StatusForm
from db.db_connection import User_db
import asyncio
from redis.redis_connection import r
from aiogram.types import ReplyKeyboardRemove


# инициализаци логов
logging.basicConfig(level=logging.INFO)
load_dotenv()


openai.api_key = os.getenv("OPENAI_TOKEN")
bot = Bot(token=os.getenv("GPT_BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# создания блокировки потовок
lock = asyncio.Lock()


gpt_name_db = ''
user_name_db = ''
user_id = ''
task = None

@dp.message_handler(Command("start"))
async def start(message: types.Message):
    """Обработка команды старт"""
    global user_id
    global user_name_db
    global gpt_name_db
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.KeyboardButton(text='FAQ', callback_data='faq')
    button2 = types.KeyboardButton(text='Техподдержка', callback_data='support')
    welcome_message = """
        Приветствую! Я бот техподдержки условного ресурса.
        Ты можешь ознакомиться с наиболее частыми проблемами, нажав на кнопку FAQ, или пообщаться с техподдержкой на прямую, нажав "Техподдержка".
        """
    keyboard.add(button1, button2)
    await message.answer(welcome_message, reply_markup=keyboard)
    user_name_db = message.from_user.username.lower()
    """Cоздание бд и переменных для конкретного пользователя"""
    gpt_name_db = user_name_db + "_gpt"
    create_db = User_db()
    create_db.create_user_db(user_name_db)

@dp.callback_query_handler(lambda c: c.data == 'faq', state='*')
async def faq(call: types.CallbackQuery):
    """Вывод часто возникающих вопросов и ответов"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    create_db = User_db()
    faq_text = create_db.faq_output()
    if faq_text:
        for num, faq in enumerate(faq_text, start=1):
            await call.message.answer(f"{num}. Вопрос - {faq[1]}\n"
                                      f"Ответ - {faq[2]}\n", reply_markup=keyboard)
    else:
        await call.message.answer("Здесь пока нету вопросов \U0001F62A", reply_markup=keyboard)



@dp.callback_query_handler(lambda c: c.data == 'support', state='*')
async def support(call: types.CallbackQuery):
    """Выбор чата между админом и ChatGPT"""
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.KeyboardButton('Чат с ChatGPT', callback_data='gpt')
    button2 = types.KeyboardButton('Чат с администратором', callback_data='admin')
    keyboard.add(button1)
    keyboard.add(button2)
    await call.message.answer('Ниже выберите с кем хотите вести диалог', reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'gpt', state='*')
async def start_chat_whit_gpt(call: types.CallbackQuery):
    """Чат с GPT"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)
    create_db = User_db()
    create_db.update_status_gpt(gpt_name_db)
    await call.message.answer("Диалог с чатом GPT активирован. Что Вы хотели спросить?", reply_markup=keyboard)
    await StatusForm.chat_gpt.set()


@dp.message_handler(state=StatusForm.chat_gpt)
async def chat_gpt(message: types.Message, state: FSMContext):
    """Подключение к API с официального openai задаем chatGPT роль и посылаем вопрос
    ответ сохраняется в Postgress, админ при желании может просмотреть диалог у себя в боте"""
    if message.text != 'Вернуться в главное меню':
        request = message.text
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты техподдержка чего-либо..."},
                {"role": "user", "content": request}
            ]
        )

        create_db = User_db()
        create_db.response_gpt(user_name_db=user_name_db, gpt_name_db=gpt_name_db, question=message.text,
                                   answer=completion.choices[0].message)
        await message.answer(completion.choices[0].message)
    else:
        await state.finish()
        await start(message)


@dp.callback_query_handler(lambda c: c.data == 'admin', state='*')
async def start_chat_with_admin(call: types.CallbackQuery, state: FSMContext):
    """Инициализация диалог с админом"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    button2 = types.KeyboardButton('Закрыть диалог')
    keyboard.add(button1, button2)
    await call.message.answer("Добрый день, чем я могу вам помочь?", reply_markup=keyboard)
    await state.finish()
    await StatusForm.chat_admin.set()
    await chat_with_admin(call.message, state)


@dp.message_handler(state=StatusForm.chat_admin)
async def chat_with_admin(message: types.Message, state: FSMContext):
    global task
    if message.text not in ('Вернуться в главное меню', 'Закрыть диалог', 'Ниже выберите с кем хотите вести диалог'):
        def find_message_id(text):
            """Если пользователь отвечает на сообзение, ищет сообщение в чате админа и возвращает его id"""
            messages = r.lrange(user_name_db, 0, -1)
            for msg in messages:
                decoded_msg = eval(msg.decode())
                if decoded_msg.get('text') == text:
                    return decoded_msg.get('message_id')
            return None

        async def send_messages_from_admin():
            """Проверяет является ли сообщение ответом или нет, а затем пересылает его в чат"""
            while True:
                async with lock:
                    messages = r.lrange(user_name_db, 0, -1)
                    if messages:
                        for msg in messages:
                            decoded_msg = eval(msg.decode())
                            reply_msg_text = decoded_msg.get('reply_msg')
                            if decoded_msg.get('chat') == user_name_db and decoded_msg.get('reply') and decoded_msg.get(
                                    'from') == 'admin' and decoded_msg.get('publish'):
                                message_text = decoded_msg.get('text')
                                found_message_id = find_message_id(reply_msg_text)
                                decoded_msg['publish'] = False
                                await bot.send_message(chat_id=message.chat.id, text=message_text,
                                                       reply_to_message_id=found_message_id)
                                r.lset(user_name_db, messages.index(msg), str(decoded_msg))

                            elif decoded_msg.get('chat') == user_name_db and decoded_msg.get(
                                    'reply') is None and decoded_msg.get('from') == 'admin' and decoded_msg.get(
                                'publish'):
                                message_text = decoded_msg.get('text')
                                decoded_msg['publish'] = False
                                await message.answer(message_text)
                                r.lset(user_name_db, messages.index(msg), str(decoded_msg))
                await asyncio.sleep(2)

        if task is None or task.done():
            task = asyncio.create_task(send_messages_from_admin())

        messages = r.lrange(user_name_db, 0, -1)
        if not any(message.text.encode() == eval(msg.decode()).get('text') for msg in messages):
            async with lock:
                """Добавление сообщений юзера в редис"""
                if message.reply_to_message and message.reply_to_message.message_id:
                    msg = {'text': message.text,
                           'message_id': message.message_id,
                           'chat': user_name_db,
                           'from': 'user',
                           'reply': message.reply_to_message.message_id,
                           'reply_msg': message.reply_to_message.text,
                           'publish': True}
                else:
                    msg = {'text': message.text,
                           'message_id': message.message_id,
                           'chat': user_name_db,
                           'from': 'user',
                           'reply': None,
                           'reply_msg': None,
                           'publish': True}
                r.rpush(user_name_db, str(msg))
                r.expire(user_name_db, timedelta(days=1))

    elif message.text == 'Вернуться в главное меню':
        task.cancel()
        await state.finish()
        await main_menu(message, state)

    elif message.text == 'Закрыть диалог':
        task.cancel()
        await state.set_state(StatusForm.close)
        await state.finish()
        await close_dialog(message, state)


@dp.message_handler(lambda message: message.text == 'Закрыть диалог', state='*')
async def close_dialog(message: types.Message, state: FSMContext):
    """Закрытие диалога"""
    await message.answer('Спасибо, что обратились к нам. Если еще остались вопросы, можете вернуться нажав старт => /start', reply_markup=ReplyKeyboardRemove())
    create_db = User_db()
    create_db.close_dialog(user_name_db)
    await state.finish()



@dp.message_handler(lambda message: message.text == 'Вернуться в главное меню', state='*')
async def main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
    loop = asyncio.get_event_loop()
