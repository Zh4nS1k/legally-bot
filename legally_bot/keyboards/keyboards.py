from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from legally_bot.services.i18n import I18n

def get_main_menu(role: str, lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    
    # All roles can chat
    builder.row(KeyboardButton(text=I18n.t("chat_with_ai", lang)))

    if role == "student":
        builder.row(KeyboardButton(text=I18n.t("get_case", lang)))
        builder.row(KeyboardButton(text=I18n.t("my_stats", lang)))
    elif role == "professor":
        builder.row(KeyboardButton(text=I18n.t("review_corrections", lang)))
    elif role == "admin":
        builder.row(KeyboardButton(text=I18n.t("get_case", lang)), KeyboardButton(text=I18n.t("my_stats", lang)))
        builder.row(KeyboardButton(text=I18n.t("review_corrections", lang)))
        builder.row(KeyboardButton(text=I18n.t("manage_users", lang)), KeyboardButton(text=I18n.t("dev_tools", lang)))
    
    builder.row(KeyboardButton(text=I18n.t("profile", lang)), KeyboardButton(text=I18n.t("help", lang)))
    return builder.as_markup(resize_keyboard=True)

def language_selection_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Русский 🇷🇺", callback_data="lang_ru")
    builder.button(text="English 🇺🇸", callback_data="lang_en")
    builder.adjust(2)
    return builder.as_markup()

def role_selection_kb(prefix: str = "role_"):
    builder = InlineKeyboardBuilder()
    builder.button(text="Student", callback_data=f"{prefix}student")
    builder.button(text="Professor", callback_data=f"{prefix}professor")
    builder.adjust(2)
    return builder.as_markup()

def admin_request_kb(user_id: int, requested_role: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Approve", callback_data=f"adm_appr_{user_id}_{requested_role}")
    builder.button(text="❌ Reject", callback_data=f"adm_reje_{user_id}_{requested_role}")
    builder.adjust(2)
    return builder.as_markup()

def feedback_kb(case_id: str, response_id: str, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    
    labels = {
        "ru": ["✅ Все верно", "⚠️ Логическая ошибка", "❌ Неверная статья"],
        "en": ["✅ Everything Correct", "⚠️ Logic Error", "❌ Wrong Article"]
    }
    l = labels.get(lang, labels["ru"])

    # Correct response
    builder.button(text=l[0], callback_data=f"fb_good_{case_id}")
    # Logic Error
    builder.button(text=l[1], callback_data=f"fb_logic_{case_id}")
    # Wrong Article
    builder.button(text=l[2], callback_data=f"fb_article_{case_id}")
    builder.adjust(1)
    return builder.as_markup()

def professor_review_kb(feedback_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Approve", callback_data=f"rev_approve_{feedback_id}")
    builder.button(text="❌ Reject", callback_data=f"rev_reject_{feedback_id}")
    builder.adjust(2)
    return builder.as_markup()

def developer_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="/upload")
    builder.button(text="/ingest_link")
    builder.button(text="⬅️ Back")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def rating_kb(chat_id: str):
    builder = InlineKeyboardBuilder()
    for i in range(11):
        builder.button(text=str(i), callback_data=f"rate_{i}_{chat_id}")
    builder.adjust(5, 5, 1)
    return builder.as_markup()
