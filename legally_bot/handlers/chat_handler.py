import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from legally_bot.services.rag_engine import RAGEngine
from legally_bot.services.access_control import AccessControl
from legally_bot.database.users_repo import UsersRepository
from legally_bot.database.feedback_repo import FeedbackRepository
from legally_bot.keyboards.keyboards import rating_kb, get_main_menu
from legally_bot.states.states import ChatState

from legally_bot.services.i18n import I18n

router = Router()
rag_engine = RAGEngine()

@router.message(F.text.in_(["💬 Chat with AI", "💬 Чат с ИИ"]))
@router.message(Command("chat"))
async def start_chat(message: types.Message, state: FSMContext):
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await state.set_state(ChatState.chatting)
    await message.answer(I18n.t("chat_mode", lang))

@router.message(ChatState.chatting)
async def handle_chat_message(message: types.Message, state: FSMContext):
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    
    if message.text.lower() in ["exit", "stop", "back", "выход", "стоп", "назад"]:
        await state.clear()
        role = user.get("actual_role", user.get("role", "guest")) if user else "guest"
        return await message.answer(I18n.t("exit_chat", lang), reply_markup=get_main_menu(role, lang))

    # Intercept commands that shouldn't be processed as RAG queries
    if message.text.startswith("/"):
        logging.info(f"Command '{message.text}' intercepted in Chat Mode")
        await message.answer("⚠️ Unknown command or command not available in Chat Mode.\nType 'exit' to return to menu or just type your legal question.")
        return

    # Determine user role and limits
    user = await UsersRepository.get_user(message.from_user.id)
    role = user.get("actual_role", user.get("role", "guest")) if user else "guest"
    
    num_chunks = 0
    num_articles = 0
    
    if role in ["student", "professor"]:
        num_chunks = 3
        num_articles = 3
    elif role in ["developer", "admin"]:
        num_chunks = 5
        num_articles = 5

    # Search and generate answer
    await message.bot.send_chat_action(message.chat.id, "typing")
    # We pass the limits to the search method. 
    # For guest, it will use 0 chunks/articles in the final response, 
    # but the RAG engine still needs some context to answer.
    # Actually, the user says "user or guest can get only - answer".
    # This means they shouldn't see chunks/articles.
    # However, the AI still needs context to answer based on Kazakhstan law.
    # So we should retrieve context but NOT show it to guests.
    
    search_limit_chunks = max(num_chunks, 3) # Minimum 3 for AI context
    search_limit_articles = max(num_articles, 3)
    
    result = await rag_engine.search(message.text, num_chunks=search_limit_chunks, num_articles=search_limit_articles, lang=lang)
    
    answer = result.get("answer", "I'm sorry, I couldn't find an answer.")
    chunks = result.get("chunks", [])[:num_chunks]
    articles = result.get("articles", [])[:num_articles]

    response_text = f"{I18n.t('ai_answer', lang)}\n{answer}\n\n"
    
    if chunks:
        response_text += f"{I18n.t('top_chunks', lang)}\n"
        for i, chunk in enumerate(chunks, 1):
            response_text += f"{i}. {chunk['title']}: {chunk['content'][:200]}...\n"
        response_text += "\n"

    if articles:
        response_text += f"{I18n.t('relevant_articles', lang)}\n"
        for i, art in enumerate(articles, 1):
            response_text += f"{i}. {art['title']}: {art['content'][:200]}...\n"

    can_rate = role in ["student", "professor", "developer", "admin"]
    
    kb = None
    if can_rate:
        # Using message.message_id as a reference for feedback
        kb = rating_kb(str(message.message_id))
        response_text += f"\n\n{I18n.t('rate_answer', lang)}"

    # Escape or remove problematic Markdown characters to prevent parsing errors
    # For Telegram Markdown, certain characters like '_' or '*' can break if not closed
    # A simple way to avoid errors while keeping some formatting:
    
    try:
        await message.answer(response_text, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logging.warning(f"Markdown parsing failed, sending as plain text: {e}")
        # Strip Markdown-like symbols as a fallback
        plain_text = response_text.replace("**", "").replace("__", "").replace("`", "").replace("🤖 ", "").replace("🔍 ", "").replace("⚖️ ", "")
        await message.answer(plain_text, reply_markup=kb)

@router.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    # rate_{score}_{msg_id}
    parts = callback.data.split("_")
    score = int(parts[1])
    msg_id = parts[2]
    
    await state.update_data(rating_score=score, chat_msg_id=msg_id)
    await callback.message.answer(f"You rated: {score}/10. Please add a comment about why (or type 'none'):")
    await state.set_state(ChatState.waiting_for_comment)
    await callback.answer()

@router.message(ChatState.waiting_for_comment)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data.get("rating_score")
    msg_id = data.get("chat_msg_id")
    comment = message.text if message.text.lower() != "none" else ""
    
    await FeedbackRepository.log_chat_feedback(
        user_id=message.from_user.id,
        chat_msg_id=msg_id,
        rating=score,
        comment=comment
    )
    
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await message.answer(I18n.t("thank_feedback", lang))
    await state.set_state(ChatState.chatting)
