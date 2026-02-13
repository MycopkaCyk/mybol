# config.py
# Конфигурация проекта

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ ОШИБКА: Переменная окружения 'BOT_TOKEN' не найдена.")

FEEDBACK_GROUP_ID = -1003849272336
ADMIN_ID = 992068929