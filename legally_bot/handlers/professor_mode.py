from aiogram import Router, types, F
from legally_bot.services.access_control import AccessControl
from legally_bot.services.workflow import WorkflowService
from legally_bot.keyboards.keyboards import professor_review_kb
import logging

router = Router()

@router.message(F.text == "📝 Review Corrections")
async def review_corrections(message: types.Message):
    logging.info(f"Professor {message.from_user.id} requested review queue")
    if not await AccessControl.is_professor(message.from_user.id):
        return await message.answer("Access Denied.")
    
    queue = await WorkflowService.get_professor_queue()
    if not queue:
        return await message.answer("No pending corrections to review.")
    
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

    action, feedback_id = callback.data.split("_")[1], callback.data.split("_")[2]
    logging.info(f"Professor {callback.from_user.id} {action}ed correction {feedback_id}")
    
    if action == "approve":
        await WorkflowService.approve_correction(feedback_id, callback.from_user.id)
        await callback.message.edit_text(callback.message.md_text + "\n\n✅ **APPROVED**")
    elif action == "reject":
        await WorkflowService.reject_correction(feedback_id, callback.from_user.id)
        await callback.message.edit_text(callback.message.md_text + "\n\n❌ **REJECTED**")
    
    await callback.answer(f"Correction {action}d")
