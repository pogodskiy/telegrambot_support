from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import executor
import re
import logging
import os
from db.createdb import cur, conn

logging.basicConfig(level=logging.INFO)
load_dotenv()

bot = Bot(token=os.getenv("ADMIN_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)


class FAQForm(StatesGroup):
    question = State()
    answer = State()
    deleted = State()
    chat = State()


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.KeyboardButton(text='add FAQ', callback_data='add_faq')
    button2 = types.KeyboardButton(text='delete FAQ', callback_data='del_faq')
    button3 = types.KeyboardButton(text='Chat', callback_data='chats')
    welcome_message = """
           Выберите действие
           """
    keyboard.add(button1, button2, button3)
    await message.answer(welcome_message, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'add_faq')
async def add_faq(call: types.CallbackQuery):
    await FAQForm.question.set() #установка состояния question
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Вернуться в главное меню')
    keyboard.add(button1)

    await call.message.answer("Введите вопрос", reply_markup=keyboard)


@dp.message_handler(state=FAQForm.question) #хендлер сработает при состоянии question
async def add_question(message: types.Message, state: FSMContext):
    async with state.proxy() as data: #сохраняем данные в состояния question
        data['question'] = message.text
        await message.answer('Введите ответ')
        question = data['question']
        if question == 'Вернуться в главное меню':
            await message.answer('Возврат в главное меню')
            await state.finish() # выход из состояния
            await start(message) # вывод стартого экрана
        else:
            await FAQForm.answer.set() #установка состояния answer


@dp.message_handler(state=FAQForm.answer)
async def add_answer(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        question = data['question']
        answer = message.text
        cur.execute("INSERT INTO faq (question, answer) VALUES (%s, %s)", (question, answer))
        conn.commit() # добавление в БД вопроса и ответа

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton('Вернуться в главное меню')
        keyboard.add(button1)
        await message.answer('Вопрос и ответ добавлены', reply_markup=keyboard)

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


@dp.message_handler(state=FAQForm.deleted) # удаление вопроса и ответа из FAQ
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
        else:
            await message.answer('Неверный номер вопроса', reply_markup=keyboard)

    await state.finish()
    await start(message)



@dp.callback_query_handler(lambda c: c.data == 'chats')
async def chat(call: types.CallbackQuery):
    cur.execute("SELECT user_name FROM user_messages GROUP BY user_name")
    user_names = cur.fetchall()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user_names:
        for name in user_names:
            new_name = re.sub(r"['(),]", "", name[0])
            button = types.KeyboardButton(f'Чат с {new_name}') # создание кнопок с именами юзеров, которые писали сообщения
            keyboard.add(button)
        keyboard.add(types.KeyboardButton('Вернуться в главное меню'))
        await call.message.answer("Выберите пользователя, с которым хотите начать чат", reply_markup=keyboard)
    else:
        await call.message.answer("Нет активных чатов", reply_markup=keyboard)



@dp.message_handler(lambda message: f"Чат с {message.text}")
async def chat_with_user(message: types.Message, state: FSMContext):
    user_name = message.text[6:]
    cur.execute(f"SELECT * FROM user_messages WHERE user_name = '{user_name}' AND ansewer IS NULL")
    user_messages = cur.fetchall()

    if user_messages:
        for user_message in user_messages:
            await message.answer(f'{user_message[3]}')
        await message.answer('Введите ответ')

        # Установка состояния для диалога
        await state.set_state("chat")
        # Сохраняем значение user_name в контексте состояния
        await state.update_data(user_name=user_name)
    else:
        await message.answer('Нет непрочитанных сообщений от пользователя')


@dp.message_handler(state="chat")
async def add_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_name = data.get("user_name")  # Получаем значение user_name из контекста состояния
    print(message.text)
    if not message.text.startswith('Чат с'):
        cur.execute(f"UPDATE user_messages SET ansewer = '{message.text}' WHERE ansewer IS NULL and user_name = '{user_name}'")
        conn.commit()

    await state.finish()


@dp.message_handler(lambda message: message.text == 'Закрыть диалог') # тут не хватает сосотояния
async def close_dialog(message: types.Message):
    await message.answer('Диалог закрыт')
    cur.execute(f"DELETE FROM user_messages WHERE user_name = '{name}'") # name  будет браться из состояния
    conn.commit()
    await start(message)

# при любом состоянии фраза вернуться в главное меню выдает стартовое сообщение с выбором действий
@dp.message_handler(lambda message: message.text == 'Вернуться в главное меню', state='*')
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await start(message)


async def on_shutdown(dp):
    await bot.close()
    await storage.close()
    await storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_shutdown=on_shutdown)
