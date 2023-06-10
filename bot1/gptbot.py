from aiogram import Bot, Dispatcher, types, executor
import logging
import openai
from aiogram.dispatcher.filters import Text


logging.basicConfig(level=logging.INFO)

bot = Bot(token='6216842834:AAFKLlJJlhh5lWvYlPPZXTD2ax0ZVm2Frk0')
dp = Dispatcher(bot)
openai.api_key = "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"

@dp.message_handler(commands=["start"])
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
async def faq(callback_query: types.CallbackQuery):
    with open("./faq.txt", 'r') as file:
        text = file.readlines()
    faq_text = '\n'.join(text)
    await bot.send_message(callback_query.from_user.id, faq_text)
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data == 'support')
async def support(call: types.CallbackQuery):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Чат с ChatGPT')
    button2 = types.KeyboardButton('Чат с администратором')
    keyboard.add(button1, button2)
    await call.message.answer('Ниже выберите с кем хотите вести диалог', reply_markup=keyboard)

@dp.message_handler(Text(equals="Чат с ChatGPT"))
async def chat_gpt(message: types.Message):
    await message.answer('Введите ваш запрос:')
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=message.text,
        temperature=0.5,
        max_tokens=60,
        top_p=1.0,
        frequency_penalty=0.5,
        presence_penalty=0.0,
    )
    response_text = response['choices'][0]['text']
    await bot.send_message(chat_id=message.from_user.id, text=response_text)

@dp.message_handler(Text(equals="Чат с администратором"))
async def chat_admin(message: types.Message):
    await message.answer('Сообщение отправлено администратору. Ожидайте ответа.')

    # Отправляем сообщение администратору через бота администратора
    admin_bot_token = '6281769566:AAHTe4rx8EGL4jmmomv2q1moyGFnEjn_9Rs'
    admin_bot = Bot(token=admin_bot_token)
    await admin_bot.send_message(chat_id='2066654938', text=f"Пользователь {message.from_user.id} отправил вопрос: {message.text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
