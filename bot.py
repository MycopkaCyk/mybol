import os
import asyncio
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# === Импорты ===
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


# ========== ОБРАБОТЧИКИ ==========
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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=get_main_menu_keyboard())


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # ИСПРАВЛЕНО: было context.user_ → стало context.user_data
    if 'step' in context.user_data:
        context.user_data.clear()

    if text == "📊 Оставить отзыв":
        # ИСПРАВЛЕНО: было context.user_ → стало context.user_data
        if 'feedback_msg_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['feedback_msg_id']
                )
            except:
                pass
        msg = await update.message.reply_text("Выбери тип отзыва:", reply_markup=get_feedback_type_keyboard())
        context.user_data['feedback_msg_id'] = msg.message_id
        context.user_data['step'] = 'type'

    elif text == "ℹ️ О приложении":
        await update.message.reply_text(
            "📱 Наше приложение:\n• Версия: 1.0.0\n• Последнее обновление: январь 2026\n• Разработано с заботой для пользователей ❤️",
            reply_markup=get_main_menu_keyboard()
        )
    elif text == "🆘 Помощь":
        await update.message.reply_text(
            "❓ Частые вопросы:\n\n1. Как оставить отзыв?\n   - Нажми кнопку '📊 Оставить отзыв'\n   - Выбери тип отзыва\n   - Напиши комментарий\n   - Поставь две оценки (полезность и опыт)\n\nДля начала нажми '📊 Оставить отзыв'",
            reply_markup=get_main_menu_keyboard()
        )
    elif text == "📞 Связаться с поддержкой":
        await update.message.reply_text(
            "📞 Контакты поддержки:\n\n• Telegram: @your_support_username\n• Email: support@yourapp.com\n",
            reply_markup=get_main_menu_keyboard()
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['feedback_msg_id'] = query.message.message_id

    if query.data.startswith('type_'):
        feedback_type = query.data.replace("type_", "")
        context.user_data['feedback_type'] = feedback_type
        type_names = {'bug': 'ошибку', 'idea': 'идею', 'general': 'общий отзыв'}
        type_name = type_names.get(feedback_type, 'отзыв')
        await query.edit_message_text(
            text=f"Вы выбрали: сообщить {type_name}\n\nТеперь напишите ваш отзыв текстом:",
            reply_markup=None
        )
        context.user_data['step'] = 'comment'

    elif query.data.startswith('rating_usefulness_'):
        rating_usefulness = query.data.replace("rating_usefulness_", "")
        context.user_data['rating_usefulness'] = rating_usefulness
        rating_texts = {
            '1': '😠 Очень не полезно (1/5)',
            '2': '😕 Не очень полезно (2/5)',
            '3': '😐 Нормально (3/5)',
            '4': '🙂 Полезно (4/5)',
            '5': '😊 Очень полезно (5/5)'
        }
        rating_text = rating_texts.get(rating_usefulness, f'{rating_usefulness}/5')
        await query.edit_message_text(
            text=f"✅ Оценка полезности: {rating_text}\n\nТеперь оцените пользовательский опыт (удобство, интерфейс):",
            reply_markup=get_experience_rating_keyboard()
        )
        context.user_data['step'] = 'rating_experience'

    elif query.data.startswith('rating_experience_'):
        rating_experience = query.data.replace("rating_experience_", "")
        context.user_data['rating_experience'] = rating_experience
        user = update.effective_user
        feedback_type = context.user_data.get('feedback_type', 'general')
        comment = context.user_data.get('comment', '')
        rating_usefulness = context.user_data.get('rating_usefulness', '')

        if not comment:
            await query.edit_message_text(text="❌ Ошибка: комментарий не найден. Начните заново с /start")
            context.user_data.clear()
            return

        try:
            db.save_feedback(
                user_id=user.id,
                user_name=user.full_name,
                rating_usefulness=rating_usefulness,
                rating_experience=rating_experience,
                comment=comment,
                feedback_type=feedback_type
            )

            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
            type_display = {'bug': '🐞 Ошибка', 'idea': '💡 Идея', 'general': '📝 Общий отзыв'}.get(feedback_type,
                                                                                                 '📝 Отзыв')
            group_message = f"""{type_display}

👤 Пользователь: {user.full_name}
🆔 ID: {user.id}
⭐ Полезность приложения: {rating_usefulness}/5
⭐ Пользовательский опыт: {rating_experience}/5
📝 Комментарий: {comment}
⏰ Время: {timestamp}"""

            await context.bot.send_message(chat_id=FEEDBACK_GROUP_ID, text=group_message)
            await query.edit_message_text(text="✅ Спасибо! Ваш отзыв отправлен разработчику.", reply_markup=None)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Выберите следующее действие:",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as e:
            logging.error(f"Ошибка при сохранении: {e}")
            await query.edit_message_text(text="❌ Произошла ошибка при сохранении отзыва. Попробуйте позже.",
                                          reply_markup=None)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Выберите действие:",
                reply_markup=get_main_menu_keyboard()
            )
        context.user_data.clear()


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') == 'comment':
        comment = update.message.text
        context.user_data['comment'] = comment
        msg = await update.message.reply_text(
            "✅ Комментарий сохранен!\n\nТеперь оцените полезность приложения (насколько оно решает ваши задачи):",
            reply_markup=get_usefulness_rating_keyboard()
        )
        context.user_data['feedback_msg_id'] = msg.message_id
        context.user_data['step'] = 'rating_usefulness'


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            "Сначала выберите тип отзыва.\n\nНажмите '📊 Оставить отзыв'",
            reply_markup=get_main_menu_keyboard()
        )


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    msg = await update.message.reply_text("Выбери тип отзыва:", reply_markup=get_feedback_type_keyboard())
    context.user_data['feedback_msg_id'] = msg.message_id
    context.user_data['step'] = 'type'


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав доступа.")
        return
    recent = db.get_recent_feedback(limit=10)
    if not recent:
        await update.message.reply_text("📊 Пока нет отзывов.")
        return
    text = "📈 **Последние 10 отзывов:**\n\n"
    for i, (user_name, rating_usefulness, rating_experience, comment, feedback_type, created_at) in enumerate(recent,
                                                                                                              1):
        text += f"{i}. **{user_name}**\n"
        text += f"   Тип: {feedback_type}\n"
        text += f"   Полезность: {rating_usefulness}/5 | Опыт: {rating_experience}/5\n"
        if comment != "Без комментария":
            text += f"   💬 {comment[:60]}{'...' if len(comment) > 60 else ''}\n"
        text += f"   ⏰ {created_at}\n\n"
    await update.message.reply_text(text, parse_mode='Markdown')


# === Создаём Application ===
application = Application.builder().token(BOT_TOKEN).build()

# === Регистрация обработчиков ===
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("feedback", feedback_command))
application.add_handler(CommandHandler("skip", skip_command))
application.add_handler(CommandHandler("stats", stats_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, text_handler))
application.add_handler(CallbackQueryHandler(callback_handler))
application.add_error_handler(error_handler)


# === Установка вебхука и запуск сервера ===
async def main():
    raw_url = os.environ.get('RAILWAY_STATIC_URL', '').strip()
    if not raw_url:
        raise ValueError("❌ RAILWAY_STATIC_URL не задан!")

    if not raw_url.startswith(('http://', 'https://')):
        webhook_url = f"https://{raw_url}"
    else:
        webhook_url = raw_url

    full_webhook_url = f"{webhook_url.rstrip('/')}/{BOT_TOKEN}"
    print(f"✅ Устанавливаем вебхук: {full_webhook_url}")
    await application.bot.set_webhook(url=full_webhook_url)
    print("✅ Вебхук успешно установлен!")

    port = int(os.environ.get('PORT', '8080'))
    print(f"🚀 Запуск веб-сервера на порту {port}...")

    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=full_webhook_url
    )
    print("✅ Сервер запущен. Готов принимать запросы от Telegram!")


# === ЗАПУСК ===
if __name__ == '__main__':
    print("=== ЗАПУСК БОТА ДЛЯ RAILWAY ===")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен.")
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        raise