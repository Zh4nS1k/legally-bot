from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from legally_bot.services.access_control import AccessControl
from legally_bot.services.ingestion_service import IngestionService
from legally_bot.states.states import IngestionState
from legally_bot.keyboards.keyboards import developer_kb
from io import BytesIO
import logging

from legally_bot.database.users_repo import UsersRepository
from legally_bot.services.i18n import I18n

router = Router()
ingest_service = IngestionService()

@router.message(F.text.in_(["⚙️ Developer Tools", "⚙️ Инструменты разработчика"]))
@router.message(Command("dev"))
async def cmd_dev(message: types.Message):
    logging.info(f"Developer {message.from_user.id} accessed Dev Tools")
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    if not await AccessControl.is_developer(message.from_user.id):
        return await message.answer(I18n.t("no_access", lang))
    
    await message.answer("Developer Tools:", reply_markup=developer_kb())

@router.message(Command("upload"))
@router.message(F.text == "/upload")
async def start_upload(message: types.Message, state: FSMContext):
    if not await AccessControl.is_developer(message.from_user.id):
        return
    
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    if lang == "en":
        msg = "Send me a PDF, DOCX, MD, or TXT file to ingest."
    elif lang == "kk":
        msg = "Маған жүктеу үшін PDF, DOCX, MD немесе TXT файлын жіберіңіз."
    else:
        msg = "Отправьте мне файл PDF, DOCX, MD или TXT для загрузки."
    await message.answer(msg)
    await state.set_state(IngestionState.waiting_for_file)

@router.message(IngestionState.waiting_for_file, F.document)
async def handle_document(message: types.Message, state: FSMContext, bot: Bot):
    if not await AccessControl.is_developer(message.from_user.id):
        return
    
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    
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
    elif file_name.endswith('.txt'):
        file_type = "txt"
    
    if file_type:
        if lang == "en":
            progress_text = "⏳ Ingesting..."
        elif lang == "kk":
            progress_text = "⏳ Жүктелуде..."
        else:
            progress_text = "⏳ Загрузка..."
        
        progress_msg = await message.answer(progress_text)
        last_percent = 0

        async def progress_callback(processed, total):
            nonlocal last_percent
            if total == 0: return
            percent = int((processed / total) * 100)
            if percent - last_percent >= 20 or percent == 100:
                new_text = f"{progress_text} {percent}%"
                try:
                    await progress_msg.edit_text(new_text)
                    last_percent = percent
                except Exception:
                    pass

        count = await ingest_service.ingest_file(file_content, file_name, file_type, progress_callback=progress_callback)
        
        try:
            await progress_msg.delete()
        except Exception:
            pass

        if lang == "en":
            msg = f"✅ Successfully indexed {count} chunks from {file_name}."
        elif lang == "kk":
            msg = f"✅ {file_name} файлынан {count} фрагмент сәтті индекстелді."
        else:
            msg = f"✅ Успешно проиндексировано {count} фрагментов из {file_name}."
        await message.answer(msg)
        await state.clear()
    else:
        if lang == "en":
            msg = "❌ Unsupported file format. Please send PDF, DOCX, MD, or TXT."
        elif lang == "kk":
            msg = "❌ Қолдау көрсетілмейтін файл пішімі. PDF, DOCX, MD немесе TXT жіберіңіз."
        else:
            msg = "❌ Неподдерживаемый формат файла. Пожалуйста, отправьте PDF, DOCX, MD или TXT."
        await message.answer(msg)

@router.message(Command("ingest_link"))
@router.message(F.text == "/ingest_link")
async def start_link_ingest(message: types.Message, state: FSMContext):
    if not await AccessControl.is_developer(message.from_user.id):
        return
    
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    if lang == "en":
        msg = "Please send me the URL you want to ingest."
    elif lang == "kk":
        msg = "Жүктегіңіз келетін URL мекенжайын жіберіңіз."
    else:
        msg = "Пожалуйста, отправьте мне URL, который вы хотите загрузить."
    await message.answer(msg)
    await state.set_state(IngestionState.waiting_for_url)

@router.message(IngestionState.waiting_for_url, F.text.startswith("http"))
async def handle_link(message: types.Message, state: FSMContext):
    if not await AccessControl.is_developer(message.from_user.id):
        return
    
    user = await UsersRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    
    url = message.text
    logging.info(f"Developer {message.from_user.id} started ingestion of URL {url}")
    
    if lang == "en":
        progress_text = "⏳ Ingesting..."
    elif lang == "kk":
        progress_text = "⏳ Жүктелуде..."
    else:
        progress_text = "⏳ Загрузка..."
    
    progress_msg = await message.answer(progress_text)
    last_percent = 0

    async def progress_callback(processed, total):
        nonlocal last_percent
        if total == 0: return
        percent = int((processed / total) * 100)
        if percent - last_percent >= 20 or percent == 100:
            new_text = f"{progress_text} {percent}%"
            try:
                await progress_msg.edit_text(new_text)
                last_percent = percent
            except Exception:
                pass

    count = await ingest_service.ingest_url(url, progress_callback=progress_callback)
    
    try:
        await progress_msg.delete()
    except Exception:
        pass

    if lang == "en":
        msg = f"✅ Successfully indexed {count} chunks from {url}."
    elif lang == "kk":
        msg = f"✅ {url} мекенжайынан {count} фрагмент сәтті индекстелді."
    else:
        msg = f"✅ Успешно проиндексировано {count} фрагментов из {url}."
    await message.answer(msg)
    await state.clear()
