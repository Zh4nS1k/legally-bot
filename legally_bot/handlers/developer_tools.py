from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from legally_bot.services.access_control import AccessControl
from legally_bot.services.ingestion_service import IngestionService
from legally_bot.states.states import IngestionState
from legally_bot.keyboards.keyboards import developer_kb
from io import BytesIO
import logging

router = Router()
ingest_service = IngestionService()

@router.message(Command("dev"))
async def cmd_dev(message: types.Message):
    logging.info(f"Developer {message.from_user.id} accessed Dev Tools")
    if not await AccessControl.is_developer(message.from_user.id):
        return await message.answer("STRICTLY CONFIDENTIAL.")
    
    await message.answer("Developer Tools:", reply_markup=developer_kb())

@router.message(Command("upload"))
@router.message(F.text == "/upload")
async def start_upload(message: types.Message, state: FSMContext):
    if not await AccessControl.is_developer(message.from_user.id):
        return
    
    await message.answer("Send me a PDF, DOCX, or MD file to ingest.")
    await state.set_state(IngestionState.waiting_for_file)

@router.message(IngestionState.waiting_for_file, F.document)
async def handle_document(message: types.Message, state: FSMContext, bot: Bot):
    if not await AccessControl.is_developer(message.from_user.id):
        return
    
    doc = message.document
    file_id = doc.file_id
    file_name = doc.file_name
    
    logging.info(f"Developer {message.from_user.id} started ingestion of {file_name}")
    
    file_content = BytesIO()
    await bot.download(file_id, destination=file_content)
    file_content.seek(0)
    
    file_type = None
    if file_name.endswith('.pdf'):
        file_type = "pdf"
    elif file_name.endswith('.docx'):
        file_type = "docx"
    elif file_name.endswith('.md'):
        file_type = "md"
    
    if file_type:
        count = await ingest_service.ingest_file(file_content, file_name, file_type)
        await message.answer(f"✅ Successfully indexed {count} chunks from {file_name}.")
        await state.clear()
    else:
        await message.answer("❌ Unsupported file format. Please send PDF, DOCX, or MD.")

@router.message(Command("ingest_link"))
@router.message(F.text == "/ingest_link")
async def start_link_ingest(message: types.Message, state: FSMContext):
    if not await AccessControl.is_developer(message.from_user.id):
        return
    
    await message.answer("Please send me the URL you want to ingest.")
    await state.set_state(IngestionState.waiting_for_url)

@router.message(IngestionState.waiting_for_url, F.text.startswith("http"))
async def handle_link(message: types.Message, state: FSMContext):
    if not await AccessControl.is_developer(message.from_user.id):
        return
    
    url = message.text
    logging.info(f"Developer {message.from_user.id} started ingestion of URL {url}")
    count = await ingest_service.ingest_url(url)
    await message.answer(f"✅ Successfully indexed {count} chunks from {url}.")
    await state.clear()
