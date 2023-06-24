import psycopg2
import logging
import os

logging.basicConfig(level=logging.INFO)
conn = psycopg2.connect(dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
                        host=os.getenv('DB_HOST'))

cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS user_messages (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        chat_id BIGINT,
        user_name TEXT,
        question TEXT,
        answer TEXT, 
        status_message INTEGER DEFAULT 2,
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
conn.commit()
