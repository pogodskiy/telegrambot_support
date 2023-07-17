import psycopg2
import logging
import os

logging.basicConfig(level=logging.INFO)
conn = psycopg2.connect(dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
                        host=os.getenv('DB_HOST'))

cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        user_name TEXT,
        status_chat_gpt INTEGER DEFAULT 0,
        status_chat INTEGER DEFAULT 1
    );
""")


cur.execute("""
    CREATE TABLE IF NOT EXISTS faq (
        id SERIAL PRIMARY KEY,
        question TEXT,
        answer TEXT
    );
""")
# async def trigger():
#     cur.execute("""CREATE TRIGGER answer_trigger
#         AFTER UPDATE ON {user_name}
#         FOR EACH ROW
#         WHEN (OLD.answer <> NEW.answer)
#         EXECUTE FUNCTION trigger_func();
#         """
#         )
#
# async def trigger_func(message:types.Message):
#     cur.execute(
#     f"UPDATE {user_name} SET status_message = 0 "
#     "WHERE status_message = 1"
#     )

    # await bot.send_messaage(2066654938, 'answer')


conn.commit()


# CREATE FUNCTION trigger_func() RETURNS TRIGGER AS $$
# BEGIN
#     -- Отправить сообщение с использованием библиотеки aiogram
#     PERFORM pg_notify('send_message', NEW.answer::text);
#
#     -- Обновить столбец status_message в таблице
#     EXECUTE format('UPDATE %I SET status_message = 0 WHERE status_message = 1', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME);
#
#     RETURN NEW;
# END;
# $$ LANGUAGE plpgsql;

#
# import asyncio
#
# async def trigger_checker():
#     while True:
#         # Проверяем наличие триггера с именем "answer_trigger"
#         cur.execute(f"""
#             SELECT 1
#             FROM pg_trigger
#             WHERE tgname = 'answer_trigger'
#               AND tgrelid = '{user_name_db}'::regclass
#         """)
#         trigger_exists = cur.fetchone()
#
#         if not trigger_exists:
#             cur.execute(f"""
#                 CREATE TRIGGER answer_trigger
#                 AFTER UPDATE ON {user_name_db}
#                 FOR EACH ROW
#                 WHEN (OLD.answer <> NEW.answer)
#                 EXECUTE FUNCTION trigger_func(NEW.answer)
#             """)
#
#         await asyncio.sleep(5)  # Задержка в 5 секунд
# # Функция для прослушивания событий PostgreSQL и запуска trigger_checker
# async def listen_for_events():
#     conn = await aiopg.connect(dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'))
#     async with conn.cursor() as cur:
#         await cur.execute(f"LISTEN answer_update_event;")  # Установка прослушивания события
#         while True:
#             await conn.commit()  # Фиксация транзакции
#             await asyncio.sleep(1)  # Задержка в 1 секунду
#             await trigger_checker()  # Выполнение trigger_checker
#
#
# async def trigger_func(answer):
#     print(f"Триггер сработал. Значение answer: {answer}")
#     cur.execute(
#         f"UPDATE {user_name_db} SET status_message = 0 WHERE answer = %s",
#         (answer,)
#     )