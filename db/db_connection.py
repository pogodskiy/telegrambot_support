import os
import psycopg2


class PostgreSQL:
    _config = {
        'dbname':os.getenv('DB_NAME'),
        "user" :os.getenv('DB_USER'),
        "password":os.getenv('DB_PASSWORD'),
        "host":os.getenv('DB_HOST')
    }


class User_db(PostgreSQL):

    def create_users_db(self):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_name TEXT,
                status_chat_gpt INTEGER DEFAULT 0,
                status_chat INTEGER DEFAULT 1
            );
        """)


    def faq_output(self):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute("SELECT * FROM faq")
        faq_text = cur.fetchall()
        return faq_text


    def create_chatGPT_db(self, gpt_name_db):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {gpt_name_db} (
                id SERIAL PRIMARY KEY,
                gpt_id INT,
                question TEXT,
                answer TEXT,
                FOREIGN KEY (gpt_id) REFERENCES users(id)
                    );
            """)
        conn.commit()

    def response_gpt(self,user_name_db, gpt_name_db, answer, response):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute(f"SELECT id FROM users WHERE user_name = '{user_name_db}'")
        user_id = cur.fetchone()[0]
        cur.execute(f"INSERT INTO {gpt_name_db} (gpt_id, question, answer) VALUES (%s, %s, %s)",
                    (user_id, answer, response))
        conn.commit()

    def create_user_db(self, user_name_db):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (user_name) SELECT %s WHERE NOT EXISTS (SELECT 1 FROM users WHERE user_name = %s) RETURNING id",
            (user_name_db, user_name_db))
        row = cur.fetchone()
        if row is not None:
            user_id = int(row[0])
        else:
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

    def update_status_gpt(self, user_name_db):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET status_chat_gpt = 1 WHERE user_name = '{user_name_db}'")
        conn.commit()

    def close_dialog(self, user_name_db):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET status_chat = 0 WHERE user_name = '{user_name_db}'")
        conn.commit()


class FAQ(PostgreSQL):

    def create_faq_db(self):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS faq (
                id SERIAL PRIMARY KEY,
                question TEXT,
                answer TEXT
            );
        """)

        conn.commit()

    def add_faq(self, question, answer):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute("INSERT INTO faq (question, answer) VALUES (%s, %s)", (question, answer))
        conn.commit()

    def select_faq(self):
        conn = psycopg2.connect(**self._config)
        cur = conn.cursor()
        cur.execute("SELECT * FROM faq")
        rows = cur.fetchall()
        return rows


