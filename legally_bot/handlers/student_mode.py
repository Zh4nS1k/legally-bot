from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from legally_bot.services.access_control import AccessControl
from legally_bot.services.workflow import WorkflowService
from legally_bot.database.feedback_repo import FeedbackRepository
from legally_bot.keyboards.keyboards import feedback_kb
from legally_bot.states.states import StudentModeState
import logging

from legally_bot.database.users_repo import UsersRepository
from legally_bot.services.i18n import I18n

router = Router()

@router.message(F.text.in_(["🎓 Get Case", "🎓 Получить кейс"]))
async def get_case(message: types.Message):
    logging.info(f"Student {message.from_user.id} requested a case")
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    if not await AccessControl.is_student(message.from_user.id):
        return await message.answer(I18n.t("no_access", lang))

    # 1. Fetch Random Case
    case = await FeedbackRepository.get_random_case()
    if not case:
        # If no cases in DB, generate a mock one for testing
        case = {"_id": "mock_id_123", "text": "A mock case about Contract Law...", "domain": "Civil"}
    
    # 2. Get RAG Answer
    rag_response = await WorkflowService.process_student_question(message.from_user.id, case['text'], lang=lang)
    
    answer_label = "🤖 **Ответ ИИ:**" if lang == "ru" else "🤖 **AI Answer:**"
    sources_label = "📚 **Источники:**" if lang == "ru" else "📚 **Sources:**"

    text = (
        f"**Case (Domain: {case.get('domain')}):**\n`{case['text']}`\n\n"
        f"{answer_label}\n{rag_response['answer']}\n\n"
        f"{sources_label}\n"
    )
    for doc in rag_response.get('source_documents', []):
        text += f"- {doc['title']} (Confidence: {doc['score']})\n"
        
    await message.answer(text, parse_mode="Markdown", 
                         reply_markup=feedback_kb(str(case['_id']), "ai_resp_123", lang=lang))

# --- Feedback Callback Handlers ---

@router.callback_query(F.data.startswith("fb_good_"))
async def feedback_good(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    case_id = parts[2]
    
    logging.info(f"Student {callback.from_user.id} gave POSITIVE feedback for case {case_id}")
    user = await UsersRepository.get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    await WorkflowService.submit_feedback(
        user_id=callback.from_user.id,
        case_id=case_id,
        ai_response_id="ai_resp_123",
        rating=10,
        error_type=None,
        comment="Auto-approved as correct"
    )
    fb_label = "✅ Feedback: Everything Correct" if lang == "en" else "✅ Отзыв: Все верно"
    await callback.message.edit_text(callback.message.md_text + f"\n\n{fb_label}")
    msg = "Great job! Case marked as solved." if lang == "en" else "Отлично! Кейс отмечен как решенный."
    await callback.answer(msg)

@router.callback_query(F.data.startswith("fb_logic_"))
async def feedback_logic(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    case_id = parts[2]
    logging.info(f"Student {callback.from_user.id} reported LOGIC error for case {case_id}")
    user = await UsersRepository.get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    
    await state.update_data(case_id=case_id, error_type="logic", language=lang)
    prompt = "⚠️ Please describe the logic error in the AI's reasoning:" if lang == "en" else "⚠️ Пожалуйста, опишите логическую ошибку в рассуждениях ИИ:"
    await callback.message.answer(prompt)
    await state.set_state(StudentModeState.waiting_for_error_desc)
    await callback.answer()

@router.callback_query(F.data.startswith("fb_article_"))
async def feedback_article(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    case_id = parts[2]
    logging.info(f"Student {callback.from_user.id} reported ARTICLE error for case {case_id}")
    user = await UsersRepository.get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    await state.update_data(case_id=case_id, error_type="wrong_article", language=lang)
    prompt = "❌ Which article is wrong, and what is the correct one? Please explain:" if lang == "en" else "❌ Какая статья неверна и какая верная? Пожалуйста, объясните:"
    await callback.message.answer(prompt)
    await state.set_state(StudentModeState.waiting_for_error_desc)
    await callback.answer()

@router.message(StudentModeState.waiting_for_error_desc)
async def process_error_desc(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    await WorkflowService.submit_feedback(
        user_id=message.from_user.id,
        case_id=data['case_id'],
        ai_response_id="ai_resp_123",
        rating=None, # No rating on error? Or low rating.
        error_type=data['error_type'],
        comment=message.text
    )
    
    msg = "Feedback submitted! A professor will review your correction." if lang == "en" else "Отзыв отправлен! Профессор проверит ваше исправление."
    await message.answer(msg)
    await state.clear()
