
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from legally_bot.database.mongo_db import MongoDB
from legally_bot.database.case_repo import CaseRepository
from legally_bot.states.states import StudentModeState # Reuse or create new

router = Router()

# State for Rating Flow
from aiogram.fsm.state import State, StatesGroup
class RatingState(StatesGroup):
    viewing_case = State()
    rating_question = State()
    rating_chunk = State()
    rating_article = State()
    commenting = State()

@router.message(Command("my_cases"))
async def cmd_my_cases(message: types.Message):
    """
    Lists cases assigned to the user.
    """
    user_id = message.from_user.id
    db = MongoDB.get_db()
    
    # Check both collections? Or just assume one based on role?
    # For now, let's search both locally for simplicity or assume User Role defines it.
    # Let's search student_cases first.
    
    student_cases = await db.student_cases.find({"assigned_to": user_id, "status": "assigned"}).to_list(length=10)
    prof_cases = await db.professor_cases.find({"assigned_to": user_id, "status": "assigned"}).to_list(length=10)
    
    all_cases = student_cases + prof_cases
    
    if not all_cases:
        await message.answer("📭 You have no pending cases.")
        return
        
    builder = InlineKeyboardBuilder()
    for case in all_cases:
        # Button: "Case ID ... (Subject)"
        case_id = str(case["_id"])
        # Use first 20 chars of question
        label = f"{case.get('subject', 'General')}: {case.get('question', '')[:20]}..."
        builder.button(text=label, callback_data=f"open_case:{case_id}")
    
    builder.adjust(1)
    await message.answer("📋 **Your Assigned Cases**:", reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("open_case:"))
async def cb_open_case(callback: types.CallbackQuery, state: FSMContext):
    case_id = callback.data.split(":")[1]
    
    # Fetch case
    from bson import ObjectId
    try:
        oid = ObjectId(case_id)
        db = MongoDB.get_db()
        # Try finding in both
        case = await db.student_cases.find_one({"_id": oid})
        collection_type = "student_cases"
        if not case:
            case = await db.professor_cases.find_one({"_id": oid})
            collection_type = "professor_cases"
            
        if not case:
            await callback.answer("Case not found.")
            return
            
        # Display Case
        text = f"**Question:** {case.get('question')}\n\n"
        text += f"**AI Answer:** {case.get('answer')}\n\n"
        text += f"**Chunks:** {case.get('chunks')}\n\n"
        text += f"**Articles:** {case.get('articles')}\n"
        
        await state.update_data(case_id=case_id, collection_type=collection_type)
        
        # Rating Button
        kb = InlineKeyboardBuilder()
        kb.button(text="⭐ Rate This Case", callback_data="start_rating")
        
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error opening case: {e}")
        await callback.answer("Error opening case.")

@router.callback_query(F.data == "start_rating")
async def cb_start_rating(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("1️⃣ **Rate Question Quality** (0-10):")
    await state.set_state(RatingState.rating_question)
    await callback.answer()

@router.message(RatingState.rating_question)
async def process_rate_q(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (0 <= int(message.text) <= 10):
        await message.answer("❌ Please enter a number 0-10.")
        return
    await state.update_data(rate_q=int(message.text))
    await message.answer("2️⃣ **Rate Chunk Relevance** (0-10):")
    await state.set_state(RatingState.rating_chunk)

@router.message(RatingState.rating_chunk)
async def process_rate_c(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (0 <= int(message.text) <= 10):
        await message.answer("❌ Please enter a number 0-10.")
        return
    await state.update_data(rate_c=int(message.text))
    await message.answer("3️⃣ **Rate Article Accuracy** (0-10):")
    await state.set_state(RatingState.rating_article)

@router.message(RatingState.rating_article)
async def process_rate_a(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (0 <= int(message.text) <= 10):
        await message.answer("❌ Please enter a number 0-10.")
        return
    await state.update_data(rate_a=int(message.text))
    await message.answer("💬 **Leave a Comment (optional/required):**")
    await state.set_state(RatingState.commenting)

@router.message(RatingState.commenting)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text
    
    # Save Rating
    repo = CaseRepository(MongoDB.get_db())
    from bson import ObjectId
    case_oid = ObjectId(data['case_id'])
    
    ratings = {
        "question": data['rate_q'],
        "chunk": data['rate_c'],
        "article": data['rate_a']
    }
    
    await repo.submit_rating(
        collection_name=data['collection_type'],
        case_id=case_oid,
        ratings=ratings,
        comment=comment,
        rater_id=message.from_user.id
    )
    
    await message.answer("✅ **Rating Submitted!** Case moved to Rated Questions.")
    await state.clear()
