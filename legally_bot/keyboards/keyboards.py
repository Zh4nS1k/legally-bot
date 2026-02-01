from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_menu(role: str):
    builder = ReplyKeyboardBuilder()
    
    if role == "student":
        builder.row(KeyboardButton(text="🎓 Get Case"))
        builder.row(KeyboardButton(text="📊 My Stats"))
    elif role == "professor":
        builder.row(KeyboardButton(text="📝 Review Corrections"))
    elif role == "admin":
        builder.row(KeyboardButton(text="🎓 Get Case"), KeyboardButton(text="📊 My Stats"))
        builder.row(KeyboardButton(text="📝 Review Corrections"))
        builder.row(KeyboardButton(text="👥 Manage Users"), KeyboardButton(text="⚙️ Developer Tools"))
    
    builder.row(KeyboardButton(text="👤 Profile"))
    return builder.as_markup(resize_keyboard=True)

def role_selection_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Student", callback_data="role_student")
    builder.button(text="Professor", callback_data="role_professor")
    builder.adjust(2)
    return builder.as_markup()

def feedback_kb(case_id: str, response_id: str):
    builder = InlineKeyboardBuilder()
    # Correct response
    builder.button(text="✅ Everything Correct", callback_data=f"fb_good_{case_id}")
    # Logic Error
    builder.button(text="⚠️ Logic Error", callback_data=f"fb_logic_{case_id}")
    # Wrong Article
    builder.button(text="❌ Wrong Article", callback_data=f"fb_article_{case_id}")
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
