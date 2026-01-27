import sqlite3
from datetime import datetime


class FeedbackDatabase:
    def __init__(self, db_name="feedback.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        """Создаем таблицу для хранения отзывов с двумя оценками"""
        query = """
                CREATE TABLE IF NOT EXISTS feedback \
                ( \
                    id \
                    INTEGER \
                    PRIMARY \
                    KEY \
                    AUTOINCREMENT, \
                    user_id \
                    INTEGER, \
                    user_name \
                    TEXT, \
                    rating_usefulness \
                    INTEGER, \
                    rating_experience \
                    INTEGER, \
                    comment \
                    TEXT, \
                    feedback_type \
                    TEXT, \
                    created_at \
                    TIMESTAMP
                ) \
                """
        self.conn.execute(query)
        self.conn.commit()

    def save_feedback(self, user_id, user_name, rating_usefulness, rating_experience, comment, feedback_type="general"):
        """Сохраняем отзыв в базу с двумя оценками"""
        query = """
                INSERT INTO feedback (user_id, user_name, rating_usefulness, rating_experience, comment, feedback_type, \
                                      created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?) \
                """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.execute(query,
                                   (user_id, user_name, rating_usefulness, rating_experience, comment, feedback_type,
                                    timestamp))
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_feedback(self, limit=10):
        """Получаем последние отзывы"""
        query = """
                SELECT user_name, rating_usefulness, rating_experience, comment, feedback_type, created_at
                FROM feedback
                ORDER BY created_at DESC LIMIT ? \
                """
        cursor = self.conn.execute(query, (limit,))
        return cursor.fetchall()


db = FeedbackDatabase()