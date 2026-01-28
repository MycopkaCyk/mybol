import os
import asyncio
from urllib.parse import urlparse
from telegram.ext import Application

# === ВАШИ ИМПОРТЫ ===
from config import BOT_TOKEN, FEEDBACK_GROUP_ID, ADMIN_ID
from keyboards import (
    get_feedback_type_keyboard, get_usefulness_rating_keyboard,
    get_experience_rating_keyboard, get_main_menu_keyboard
)
from database import db
from messages import WELCOME_MESSAGE

# === ВСТАВЬТЕ СЮДА ВСЕ ВАШИ ОБРАБОТЧИКИ (полностью, без изменений) ===
# (error_handler, start_command, handle_main_menu, callback_handler, text_handler, skip_command, feedback_command, stats_command)

# === СОЗДАНИЕ И НАСТРОЙКА APPLICATION ===
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(...)  # все ваши обработчики

# === УСТАНОВКА WEBHOOK ===
async def _set_hook():
    raw = os.environ.get('RAILWAY_STATIC_URL', '').strip()
    if raw:
        url = f"https://{raw}" if not urlparse(raw).scheme else raw
        await application.bot.set_webhook(f"{url.rstrip('/')}/{BOT_TOKEN}")
        print("✅ Webhook set")

# Запуск установки
try:
    asyncio.get_running_loop().create_task(_set_hook())
except RuntimeError:
    asyncio.run(_set_hook())

# === ЭКСПОРТ ДЛЯ RAILWAY ===
app = application.webhook_app