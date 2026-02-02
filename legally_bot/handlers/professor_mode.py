from aiogram import Router, types, F
from legally_bot.services.access_control import AccessControl
from legally_bot.services.workflow import WorkflowService
from legally_bot.keyboards.keyboards import professor_review_kb
import logging

from legally_bot.database.users_repo import UserRepository
from legally_bot.services.i18n import I18n

router = Router()

@router.message(F.text.in_(["📝 Review Corrections", "📝 Проверить исправления"]))
async def review_corrections(message: types.Message):
    logging.info(f"Professor {message.from_user.id} requested review queue")
    user = await UserRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    if not await AccessControl.is_professor(message.from_user.id):
        return await message.answer(I18n.t("no_access", lang))
    
    queue = await WorkflowService.get_professor_queue()
    if not queue:
        msg = "No pending corrections to review." if lang == "en" else "Нет ожидающих исправлений для проверки."
        return await message.answer(msg)
    
    # Just show the first one for now
    item = queue[0]
    
    text = (
        f"📝 **Review Correction**\n"
        f"Student ID: `{item['student_id']}`\n"
        f"Error Type: {item['error_type']}\n"
        f"Comment: {item['student_comment']}\n"
        f"Status: {item['professor_validation_status']}"
    )
    
    await message.answer(text, parse_mode="Markdown", reply_markup=professor_review_kb(str(item['_id'])))

@router.callback_query(F.data.startswith("rev_"))
async def process_review(callback: types.CallbackQuery):
    if not await AccessControl.is_professor(callback.from_user.id):
        return

    user = await UserRepository.get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    action, feedback_id = callback.data.split("_")[1], callback.data.split("_")[2]
    logging.info(f"Professor {callback.from_user.id} {action}ed correction {feedback_id}")
    
    if action == "approve":
        await WorkflowService.approve_correction(feedback_id, callback.from_user.id)
        label = "✅ **APPROVED**" if lang == "en" else "✅ **ОДОБРЕНО**"
        await callback.message.edit_text(callback.message.md_text + f"\n\n{label}")
    elif action == "reject":
        await WorkflowService.reject_correction(feedback_id, callback.from_user.id)
        label = "❌ **REJECTED**" if lang == "en" else "❌ **ОТКЛОНЕНО**"
        await callback.message.edit_text(callback.message.md_text + f"\n\n{label}")
    
    msg = f"Correction {action}d" if lang == "en" else f"Исправление {action == 'approve' and 'одобрено' or 'отклонено'}"
    await callback.answer(msg)
