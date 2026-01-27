from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def get_feedback_type_keyboard():
    """Клавиатура для выбора типа фидбека (3 кнопки)"""
    keyboard = [
        [InlineKeyboardButton("🐞 Сообщить об ошибке", callback_data="type_bug")],
        [InlineKeyboardButton("💡 Предложить идею", callback_data="type_idea")],
        [InlineKeyboardButton("📝 Общий отзыв", callback_data="type_general")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_usefulness_rating_keyboard():
    """Клавиатура для оценки полезности приложения (1-5)"""
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="rating_usefulness_1"),
            InlineKeyboardButton("2", callback_data="rating_usefulness_2"),
            InlineKeyboardButton("3", callback_data="rating_usefulness_3"),
            InlineKeyboardButton("4", callback_data="rating_usefulness_4"),
            InlineKeyboardButton("5", callback_data="rating_usefulness_5"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_experience_rating_keyboard():
    """Клавиатура для оценки пользовательского опыта (1-5)"""
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="rating_experience_1"),
            InlineKeyboardButton("2", callback_data="rating_experience_2"),
            InlineKeyboardButton("3", callback_data="rating_experience_3"),
            InlineKeyboardButton("4", callback_data="rating_experience_4"),
            InlineKeyboardButton("5", callback_data="rating_experience_5"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard():
    """Главное меню (Reply клавиатура)"""
    keyboard = [
        ["📊 Оставить отзыв"],
        ["ℹ️ О приложении", "🆘 Помощь"],
        ["📞 Связаться с поддержкой"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)