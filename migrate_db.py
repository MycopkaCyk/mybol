# migrate_db.py
import sqlite3
from datetime import datetime

def migrate_database():
    """Миграция базы данных с одной оценки на две"""
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()

    # Создаем новую таблицу с правильной структурой
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS feedback_new
                   (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       user_name TEXT,
                       rating_usefulness INTEGER,
                       rating_experience INTEGER,
                       comment TEXT,
                       feedback_type TEXT,
                       created_at TIMESTAMP
                   );
                   ''')

    #  Пытаемся перенести данные из старой таблицы, если они есть
    try:
        cursor.execute('SELECT * FROM feedback')
        old_data = cursor.fetchall()

        for row in old_data:
            # Старая структура: (id, user_id, user_name, rating, comment, feedback_type, created_at)
            # Новая: (user_id, user_name, rating_usefulness, rating_experience, comment, feedback_type, created_at)
            # Предполагаем, что старая оценка переходит в обе новые
            old_rating = row[3] # индекс старой оценки
            cursor.execute('''
                           INSERT INTO feedback_new (user_id, user_name, rating_usefulness, rating_experience, comment, feedback_type, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?);
                           ''', (row[1], row[2], old_rating, old_rating, row[4], row[5], row[6])) # row[1]=user_id, row[2]=user_name, row[4]=comment, row[5]=feedback_type, row[6]=created_at

        print(f"Перенесено {len(old_data)} записей")
    except sqlite3.OperationalError:
        # Если таблица feedback не существует, просто игнорируем
        print("Создаем новую базу данных (старая таблица отсутствует)")

    # Удаляем старую таблицу
    cursor.execute('DROP TABLE IF EXISTS feedback;')

    # Переименовываем новую таблицу
    cursor.execute('ALTER TABLE feedback_new RENAME TO feedback;')

    conn.commit() # ИСПРАВЛЕНО: co mmit -> commit
    conn.close()
    print("✅ База данных успешно мигрирована!")

# ИСПРАВЛЕНО: name -> __name__, main -> '__main__'
if __name__ == '__main__':
    migrate_database()