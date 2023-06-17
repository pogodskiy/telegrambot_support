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
        user_id INTEGER,
        user_name TEXT,
        question TEXT,
        ansewer TEXT
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

# if __name__ == '__main__':
#     main()

