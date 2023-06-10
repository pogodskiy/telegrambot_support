from aiogram import Bot, Dispatcher, types
import logging
import redis
import asyncio

logging.basicConfig(level=logging.INFO)

bot = Bot(token='6281769566:AAHTe4rx8EGL4jmmomv2q1moyGFnEjn_9Rs')
dp = Dispatcher(bot)

r = redis.Redis(host='redis', port=6379, db=0)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    print(message)
    await message.answer('Добро пожаловать, администратор!')


admin_chat_users = set()


def add_admin_user(user_id):
    admin_chat_users.add(user_id)


@dp.message_handler()
async def dialog(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    add_admin_user(user_id)
    r.rpush(user_id, text)
    if user_id in admin_chat_users:
        r.publish("admin_messages", f"{user_id}:{text}")
    else:
        await message.answer("Ваше сообщение сохранено. Ожидайте ответа администратора.")


async def user_message_handler():
    pubsub = r.pubsub()
    print(admin_chat_users)
    for user_id in admin_chat_users:
        pubsub.subscribe(str(user_id))

    for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"].decode()
            user_id, text = data.split(":", 1)

            await bot.send_message(chat_id='ADMIN_CHAT_ID', text=f"Пользователь {user_id} отправил сообщение: {text}")


async def user_handler():
    asyncio.create_task(user_message_handler())


async def main():
    await user_handler()
    await dp.start_polling()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
