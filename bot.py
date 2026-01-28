import os
import logging
from datetime import datetime
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# === Импорты конфигурации и модулей ===
from config import BOT_TOKEN, FEEDBACK_GROUP_ID, ADMIN_ID
from keyboards import (
    get_feedback_type_keyboard, get_usefulness_rating_keyboard,
    get_experience_rating_keyboard, get_main_menu_keyboard
)
from database import db
from messages import WELCOME_MESSAGE

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== ОБРАБОТКА ОШИБОК ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Ошибка: {context.error}")
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Произошла ошибка. Попробуйте еще раз.",
                reply_markup=get_main_menu_keyboard()
            )
        except:
            pass

# ========== КОМАНДА /START ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и показ главного меню"""
    context.user_data.clear()
    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=get_main_menu_keyboard())

# ========== ОБРАБОТКА ГЛАВНОГО МЕНЮ ==========
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок главного меню"""
    text = update.message.text

    # Если пользователь в процессе фидбека, но нажал кнопку меню - прерываем
    if 'step' in context.user_data:
        context.user_data.clear()

    if text == "📊 Оставить отзыв":
        # Удаляем старое сообщение бота с кнопками (если есть)
        if 'feedback_msg_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['feedback_msg_id']
                )
            except:
                pass

        # Отправляем инлайн-кнопки для выбора типа фидбека
        msg = await update.message.reply_text(
            "Выбери тип отзыва:",
            reply_markup=get_feedback_type_keyboard()
        )
        context.user_data['feedback_msg_id'] = msg.message_id
        context.user_data['step'] = 'type'

    elif text == "ℹ️ О приложении":
        await update.message.reply_text(
            "📱 Наше приложение:\n"
            "• Версия: 1.0.0\n"
            "• Последнее обновление: январь 2026\n"
            "• Разработано с заботой для пользователей ❤️",
            reply_markup=get_main_menu_keyboard()
        )

    elif text == "🆘 Помощь":
        await update.message.reply_text(
            "❓ Частые вопросы:\n\n"
            "1. Как оставить отзыв?\n"
            "   - Нажми кнопку '📊 Оставить отзыв'\n"
            "   - Выбери тип отзыва\n"
            "   - Напиши комментарий\n"
            "   - Поставь две оценки (полезность и опыт)\n\n"
            "Для начала нажми '📊 Оставить отзыв'",
            reply_markup=get_main_menu_keyboard()
        )

    elif text == "📞 Связаться с поддержкой":
        await update.message.reply_text(
            "📞 Контакты поддержки:\n\n"
            "• Telegram: @your_support_username\n"
            "• Email: support@yourapp.com\n",
            reply_markup=get_main_menu_keyboard()
        )

# ========== ОБРАБОТЧИК ИНЛАЙН-КНОПОК ==========
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех инлайн-кнопок"""
    query = update.callback_query
    await query.answer()

    # Сохраняем ID сообщения
    context.user_data['feedback_msg_id'] = query.message.message_id

    # 1. Выбор типа фидбека
    if query.data.startswith('type_'):
        feedback_type = query.data.replace("type_", "")
        context.user_data['feedback_type'] = feedback_type

        # Определяем русское название для отображения
        type_names = {
            'bug': 'ошибку',
            'idea': 'идею',
            'general': 'общий отзыв'
        }
        type_name = type_names.get(feedback_type, 'отзыв')

        # Редактируем сообщение, запрашиваем комментарий
        await query.edit_message_text(
            text=f"Вы выбрали: сообщить {type_name}\n\nТеперь напишите ваш отзыв текстом:",
            reply_markup=None  # Убираем инлайн-кнопки
        )
        context.user_data['step'] = 'comment'

    # 2. Обработка оценки полезности
    elif query.data.startswith('rating_usefulness_'):
        rating_usefulness = query.data.replace("rating_usefulness_", "")
        context.user_data['rating_usefulness'] = rating_usefulness

        # Определяем текст для оценки полезности
        rating_texts = {
            '1': '😠 Очень не полезно (1/5)',
            '2': '😕 Не очень полезно (2/5)',
            '3': '😐 Нормально (3/5)',
            '4': '🙂 Полезно (4/5)',
            '5': '😊 Очень полезно (5/5)'
        }
        rating_text = rating_texts.get(rating_usefulness, f'{rating_usefulness}/5')

        # Редактируем сообщение, запрашиваем вторую оценку
        await query.edit_message_text(
            text=f"✅ Оценка полезности: {rating_text}\n\nТеперь оцените пользовательский опыт (удобство, интерфейс):",
            reply_markup=get_experience_rating_keyboard()
        )
        context.user_data['step'] = 'rating_experience'

    # 3. Обработка оценки опыта
    elif query.data.startswith('rating_experience_'):
        rating_experience = query.data.replace("rating_experience_", "")

        # Сохраняем данные
        context.user_data['rating_experience'] = rating_experience
        user = update.effective_user

        # Получаем все данные
        feedback_type = context.user_data.get('feedback_type', 'general')
        comment = context.user_data.get('comment', '')
        rating_usefulness = context.user_data.get('rating_usefulness', '')

        # Проверяем наличие всех данных
        if not comment:
            # Удаляем инлайн-кнопки, показываем ошибку
            await query.edit_message_text(
                text="❌ Ошибка: комментарий не найден. Начните заново с /start"
            )
            context.user_data.clear()
            return

        try:
            # Сохраняем в базу
            db.save_feedback(
                user_id=user.id,
                user_name=user.full_name,
                rating_usefulness=rating_usefulness,
                rating_experience=rating_experience,
                comment=comment,
                feedback_type=feedback_type
            )

            # Формируем сообщение для группы
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

            type_display = {
                'bug': '🐞 Ошибка',
                'idea': '💡 Идея',
                'general': '📝 Общий отзыв'
            }.get(feedback_type, '📝 Отзыв')

            group_message = f"""{type_display}

👤 Пользователь: {user.full_name}
🆔 ID: {user.id}
⭐ Полезность приложения: {rating_usefulness}/5
⭐ Пользовательский опыт: {rating_experience}/5
📝 Комментарий: {comment}
⏰ Время: {timestamp}"""

            # Отправляем в группу
            await context.bot.send_message(
                chat_id=FEEDBACK_GROUP_ID,
                text=group_message
            )

            # Удаляем инлайн-кнопки из сообщения (редактируем без кнопок)
            await query.edit_message_text(
                text="✅ Спасибо! Ваш отзыв отправлен разработчику.",
                reply_markup=None  # Важно: убираем инлайн-кнопки!
            )

            # Отправляем главное меню в отдельном сообщении
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Выберите следующее действие:",
                reply_markup=get_main_menu_keyboard()
            )

        except Exception as e:
            logging.error(f"Ошибка при сохранении: {e}")

            # Убираем инлайн-кнопки, показываем ошибку
            await query.edit_message_text(
                text="❌ Произошла ошибка при сохранении отзыва. Попробуйте позже.",
                reply_markup=None  # Убираем кнопки
            )

            # Отправляем главное меню
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Выберите действие:",
                reply_markup=get_main_menu_keyboard()
            )

        # Очищаем данные
        context.user_data.clear()

# ========== ОБРАБОТКА ТЕКСТОВЫХ КОММЕНТАРИЕВ ==========
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений (комментариев)"""
    # Если мы на шаге 'comment' (после выбора типа фидбека)
    if context.user_data.get('step') == 'comment':
        comment = update.message.text
        context.user_data['comment'] = comment

        # Отправляем новое сообщение с кнопками для оценки полезности
        msg = await update.message.reply_text(
            "✅ Комментарий сохранен!\n\n"
            "Теперь оцените полезность приложения (насколько оно решает ваши задачи):",
            reply_markup=get_usefulness_rating_keyboard()
        )

        # Сохраняем ID нового сообщения
        context.user_data['feedback_msg_id'] = msg.message_id
        context.user_data['step'] = 'rating_usefulness'

# ========== КОМАНДА /SKIP ==========
async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск комментария (если пользователь не хочет писать текст)"""
    if context.user_data.get('step') == 'comment':
        context.user_data['comment'] = 'Без комментария'

        msg = await update.message.reply_text(
            "Теперь оцените полезность приложения (насколько оно решает ваши задачи):",
            reply_markup=get_usefulness_rating_keyboard()
        )

        context.user_data['feedback_msg_id'] = msg.message_id
        context.user_data['step'] = 'rating_usefulness'
    else:
        await update.message.reply_text(
            "Сначала выберите тип отзыва.\n\n"
            "Нажмите '📊 Оставить отзыв'",
            reply_markup=get_main_menu_keyboard()
        )

# ========== КОМАНДА /FEEDBACK ==========
async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /feedback - альтернатива кнопке"""
    context.user_data.clear()
    msg = await update.message.reply_text(
        "Выбери тип отзыва:",
        reply_markup=get_feedback_type_keyboard()
    )
    context.user_data['feedback_msg_id'] = msg.message_id
    context.user_data['step'] = 'type'

# ========== КОМАНДА /STATS ==========
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика для админа"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав доступа.")
        return

    recent = db.get_recent_feedback(limit=10)
    if not recent:
        await update.message.reply_text("📊 Пока нет отзывов.")
        return

    text = "📈 **Последние 10 отзывов:**\n\n"
    for i, (user_name, rating_usefulness, rating_experience, comment, feedback_type, created_at) in enumerate(recent, 1):
        text += f"{i}. **{user_name}**\n"
        text += f"   Тип: {feedback_type}\n"
        text += f"   Полезность: {rating_usefulness}/5 | Опыт: {rating_experience}/5\n"
        if comment != "Без комментария":
            text += f"   💬 {comment[:60]}"
            if len(comment) > 60:
                text += "..."
            text += "\n"
        text += f"   ⏰ {created_at}\n\n"

    await update.message.reply_text(text, parse_mode='Markdown')

# === Создаём Application БЕЗ JobQueue ===
application = Application.builder().token(BOT_TOKEN).build()

# === Регистрация всех обработчиков ===
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("feedback", feedback_command))
application.add_handler(CommandHandler("skip", skip_command))
application.add_handler(CommandHandler("stats", stats_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, text_handler))
application.add_handler(CallbackQueryHandler(callback_handler))
application.add_error_handler(error_handler)

# === УСТАНОВКА WEBHOOK ПРИ ИМПОРТЕ ===
async def _set_webhook():
    raw_url = os.environ.get('RAILWAY_STATIC_URL', '').strip()
    if not raw_url:
        print("⚠️ RAILWAY_STATIC_URL не задан. Webhook не установлен.")
        return

    if not raw_url.startswith(('http://', 'https://')):
        webhook_url = f"https://{raw_url}"
    else:
        webhook_url = raw_url

    full_url = f"{webhook_url.rstrip('/')}/{BOT_TOKEN}"
    print(f"✅ Устанавливаем вебхук: {full_url}")
    await application.bot.set_webhook(url=full_url)
    print("✅ Вебхук успешно установлен!")

# Запускаем установку вебхука один раз при импорте модуля
import asyncio
try:
    loop = asyncio.get_running_loop()
    loop.create_task(_set_webhook())
except RuntimeError:
    asyncio.run(_set_webhook())

# === ЭКСПОРТИРУЕМ ASGI-ПРИЛОЖЕНИЕ ДЛЯ RAILWAY ===
app = application.webhook_app
print("✅ ASGI-приложение 'app' готово для Railway!")