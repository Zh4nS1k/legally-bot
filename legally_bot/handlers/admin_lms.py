
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from io import BytesIO

from legally_bot.database.mongo_db import MongoDB
from legally_bot.database.users_repo import UsersRepository
from legally_bot.database.case_repo import CaseRepository
from legally_bot.services.batch_service import BatchService
from legally_bot.states.states import AdminStates

router = Router()
batch_service = BatchService()

@router.message(Command("upload_cases"))
async def cmd_upload_cases(message: types.Message, state: FSMContext):
    # Check Admin Role (TODO: Middleware handles this usually, but simple check here)
    # For now assuming role check is done or we add it
    
    await message.answer("📂 Please upload an Excel (.xlsx) or JSON file with questions.\nFormat: Must have a 'question' column.")
    await state.set_state(AdminStates.waiting_for_case_file)

@router.message(AdminStates.waiting_for_case_file, F.document)
async def handle_case_file(message: types.Message, state: FSMContext):
    file_id = message.document.file_id
    file_name = message.document.file_name
    
    status_msg = await message.answer("⏳ Downloading and processing batch... This may take a while.")
    
    try:
        # Download
        bot = message.bot
        file = await bot.get_file(file_id)
        file_content = BytesIO()
        await bot.download_file(file.file_path, file_content)
        file_content.seek(0)
        
        # Process Schema
        # Check simple validation
        if not (file_name.endswith('.xlsx') or file_name.endswith('.json')):
             await message.answer("❌ Invalid format. Please upload .xlsx or .json")
             return

        # Run Batch Service
        # This takes time, so we should spawn it or await it if it's not too huge.
        # Since we use async semaphore, awaiting is fine for < 100 questions.
        
        result_content = await batch_service.process_file(file_content, file_name)
        
        # Save to DB (Admin Library)
        # We need to re-read the result to save to DB?
        # Ideally BatchService returns data AND file. 
        # But BatchService returns file object.
        # Let's assume BatchService internally could have saved or we parse the output df again.
        # For this MVP, let's assume BatchService handles only processing.
        # Wait, the plan said "Saves to 'cases' collection".
        # We need to modify BatchService to save to DB or do it here. 
        # Doing it here requires reading the result excel.
        import pandas as pd
        result_content.seek(0)
        df = pd.read_excel(result_content)
        cases_data = df.to_dict('records')
        
        repo = CaseRepository(MongoDB.get_db())
        await repo.save_admin_cases(cases_data, saver_id=message.from_user.id)
        
        # Send Result File
        result_content.seek(0)
        input_file = types.BufferedInputFile(result_content.read(), filename=f"processed_{file_name}")
        await message.answer_document(input_file, caption=f"✅ Processed {len(cases_data)} cases and saved to Library.")
        
    except Exception as e:
        logging.error(f"Batch upload failed: {e}")
        await message.answer(f"❌ Error processing file: {e}")
    finally:
        await state.clear()

@router.message(Command("assign_case"))
async def cmd_assign_case(message: types.Message, state: FSMContext):
    # Flow: Ask for Case ID -> Ask for User ID (Student/Prof)
    await message.answer("🆔 Enter the Case ID (from DB or list):")
    await state.set_state(AdminStates.waiting_for_case_id)

@router.message(AdminStates.waiting_for_case_id)
async def process_case_id(message: types.Message, state: FSMContext):
    await state.update_data(case_id=message.text.strip())
    await message.answer("👤 Enter the Student/Professor Telegram ID to assign to:")
    await state.set_state(AdminStates.waiting_for_assignee)

@router.message(AdminStates.waiting_for_assignee)
async def process_assignee(message: types.Message, state: FSMContext):
    data = await state.get_data()
    case_id = data.get("case_id")
    assignee_id = message.text.strip()
    
    # Try to convert to int usually, but assume string ID for now if user provided string
    try:
        assignee_id = int(assignee_id)
        from bson import ObjectId
        case_oid = ObjectId(case_id)
    except:
        await message.answer("❌ Invalid ID format.")
        return

    repo = CaseRepository(MongoDB.get_db())
    
    # Try assign to student (default)
    # Ideally we check role, but sticking to command simplicity
    success = await repo.assign_case_to_student(case_oid, assignee_id)
    if success:
        await message.answer(f"✅ Case {case_id} assigned to Student {assignee_id}")
    else:
        await message.answer(f"❌ Failed to find case or assign.")
    
    await state.clear()
