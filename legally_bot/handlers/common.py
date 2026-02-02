from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from legally_bot.database.users_repo import UserRepository
from legally_bot.keyboards.keyboards import get_main_menu
from legally_bot.services.access_control import AccessControl
import logging

from legally_bot.services.i18n import I18n
from legally_bot.keyboards.keyboards import get_main_menu, language_selection_kb, role_selection_kb
from legally_bot.states.states import RegistrationState
import logging

from legally_bot.services.i18n import I18n
from legally_bot.config import settings

router = Router()

@router.message(Command("request_role"))
async def cmd_request_role(message: types.Message):
    user = await UserRepository.get_user(message.from_user.id)
    if not user:
        return # User not registered
    
    lang = user.get("language", "ru")
    actual_role = user.get("actual_role", "guest")
    requested_role = user.get("requested_role")

    if requested_role and requested_role != actual_role:
        return await message.answer(I18n.t("already_requested", lang, role=requested_role))
    
    await message.answer(I18n.t("request_role_prompt", lang), reply_markup=role_selection_kb(prefix="req_"))

@router.callback_query(F.data.startswith("req_"))
async def process_role_request(callback: types.CallbackQuery, bot: Bot):
    role = callback.data.split("_")[1]
    user = await UserRepository.get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    
    await UserRepository.set_requested_role(callback.from_user.id, role)
    
    await callback.message.edit_text(I18n.t("role_request_sent", lang, role=role), parse_mode="Markdown")
    
    # Notify Admin
    for admin_id in settings.admin_ids_list:
        try:
            from legally_bot.keyboards.keyboards import admin_request_kb
            await bot.send_message(
                admin_id,
                f"🔔 **New Role Request**\nUser: {user['full_name']} (@{callback.from_user.username})\nID: `{callback.from_user.id}`\nRequested: **{role}**",
                reply_markup=admin_request_kb(callback.from_user.id, role),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")
            
    await callback.answer()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} called /start")
    user = await UserRepository.get_user(message.from_user.id)
    if not user:
        await message.answer(I18n.t("select_language"), reply_markup=language_selection_kb())
        await state.set_state(RegistrationState.waiting_for_language)
    else:
        role = user.get("actual_role", user.get("role", "guest"))
        lang = user.get("language", "ru")
        await message.answer(
            f"Welcome back, {user.get('full_name')}! You are logged in as **{role}**.",
            reply_markup=get_main_menu(role, lang),
            parse_mode="Markdown"
        )

@router.callback_query(RegistrationState.waiting_for_language, F.data.startswith("lang_"))
async def process_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(language=lang)
    await callback.message.edit_text(I18n.t("welcome", lang), parse_mode="Markdown")
    await state.set_state(RegistrationState.waiting_for_name)
    await callback.answer()

@router.message(F.text.in_(["👤 Profile", "👤 Профиль"]))
async def cmd_profile(message: types.Message):
    user = await UserRepository.get_user(message.from_user.id)
    if not user:
        return
    
    lang = user.get("language", "ru")
    role = user.get("actual_role", "guest")
    req_role = user.get("requested_role", "none")
    
    status_text = f"**{role}**"
    if req_role != role:
        status_text += f" (Requested: {req_role})"

    profile_text = (
        f"👤 **{I18n.t('profile', lang)}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"📛 Name: {user['full_name']}\n"
        f"📧 Email: {user['email']}\n"
        f"🎭 Role: {status_text}\n"
        f"📊 Solved: {user.get('cases_solved_count', 0)}\n"
    )
    await message.answer(profile_text, parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    logging.info(f"User {message.from_user.id} called /help")
    user = await UserRepository.get_user(message.from_user.id)
    role = "guest"
    lang = "ru"
    if user:
        role = user.get('actual_role', user.get('role', 'guest'))
        lang = user.get("language", "ru")
    
    help_texts = {
        "ru": {
            "header": (
                "⚖️ **Legally Bot: Руководство пользователя**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "Этот бот разработан для помощи в юридическом обучении и управлении документами с использованием ИИ.\n\n"
                "**Общая навигация:**\n"
                "• `/start` - Вернуться в главное меню в любое время.\n"
                "• `/help` - Просмотреть это руководство.\n"
                "• `/request_role` - Запросить новую роль (Студент/Профессор).\n"
                "• `👤 Профиль` - Проверить ваш статус и статистику.\n\n"
                "**Руководство для вашей роли:**\n"
            ),
            "guest": (
                "**👋 Добро пожаловать, Гость!**\n"
                "Чтобы раскрыть полный потенциал бота, вы должны зарегистрироваться:\n"
                "1. Введите `/start`, если вы еще этого не сделали.\n"
                "2. Укажите ваше полное имя и Email.\n"
                "3. Выберите роль (Студент или Профессор).\n"
                "4. Дождитесь одобрения администратора.\n"
                "**Примечание:** Вы все равно можете использовать `💬 Чат с ИИ` как гость!"
            ),
            "student": (
                "**🎓 Инструкция для Студента:**\n"
                "1. **Решение кейсов**: Нажмите `🎓 Получить кейс`. ИИ проанализирует правовой сценарий. Прочитайте ответ и проверьте `📚 Источники`.\n"
                "2. **Оставить отзыв**: После ответа ИИ используйте кнопки:\n"
                "   - ✅ `Все верно`: Если вы согласны с ИИ.\n"
                "   - ⚠️ `Логическая ошибка`: Если рассуждения неверны.\n"
                "   - ❌ `Неверная статья`: Если юридическая статья процитирована неправильно.\n"
                "3. **Отслеживание прогресса**: Нажмите `📊 Моя статистика`, чтобы увидеть количество решенных кейсов."
            ),
            "professor": (
                "**📝 Инструкция для Профессора:**\n"
                "Ваша цель — подтверждать точность ИИ на основе отзывов студентов.\n"
                "1. Нажмите `📝 Проверить исправления`, чтобы увидеть ожидающие отзывы.\n"
                "2. Прочитайте комментарий студента и оригинальный ответ ИИ.\n"
                "3. **Одобрить**: Если исправление студента верно.\n"
                "4. **Отклонить**: Если ИИ был прав или отзыв некорректен."
            ),
            "admin": (
                "**👑 Инструкция для Администратора/Менеджера:**\n"
                "У вас есть полный контроль над системой.\n"
                "1. **Управление пользователями**: Нажмите `👥 Управление пользователями`, чтобы увидеть ожидающие регистрации.\n"
                "2. **Повышение роли**: Используйте `/promote <id> <role>` для предоставления доступа (например, `/promote 12345 student`).\n"
                "3. **Аудит системы**: Используйте `/help` и `👤 Профиль` для мониторинга всех ролей.\n"
                "4. **База знаний**: Используйте `⚙️ Инструменты разработчика` для добавления документов."
            ),
            "developer": (
                "**⚙️ Инструкция для Разработчика:**\n"
                "Управление базой знаний RAG.\n"
                "1. **Загрузка файлов**: Используйте `/upload` и отправьте PDF, DOCX или MD файл.\n"
                "2. **Загрузка ссылок**: Используйте `/ingest_link` и укажите URL.\n"
                "3. **Верификация**: Бот подтвердит, сколько 'фрагментов' было добавлено в Pinecone."
            )
        },
        "en": {
            "header": (
                "⚖️ **Legally Bot: User Guide**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "This bot is designed to assist with legal training and document management using AI.\n\n"
                "**General Navigation:**\n"
                "• `/start` - Return to the main menu at any time.\n"
                "• `/help` - View this instruction manual.\n"
                "• `/request_role` - Request a new role (Student/Professor).\n"
                "• `👤 Profile` - Check your status and stats.\n\n"
                "**Your Role-Specific Guide:**\n"
            ),
            "guest": (
                "**👋 Welcome, Guest!**\n"
                "To unlock the bot's full potential, you must register:\n"
                "1. Type `/start` if you haven't.\n"
                "2. Provide your Full Name and Email.\n"
                "3. Select a role (Student or Professor).\n"
                "4. Wait for Admin approval.\n"
                "**Note:** You can still use `💬 Chat with AI` as a guest!"
            ),
            "student": (
                "**🎓 Student Instruction:**\n"
                "1. **Solve Cases**: Click `🎓 Get Case`. AI will analyze a legal scenario. Read the answer and check the `📚 Sources`.\n"
                "2. **Give Feedback**: After an AI answer, use the buttons:\n"
                "   - ✅ `Everything Correct`: If you agree with the AI.\n"
                "   - ⚠️ `Logic Error`: If the reasoning is flawed.\n"
                "   - ❌ `Wrong Article`: If a legal article is cited incorrectly.\n"
                "3. **Track Progress**: Click `📊 My Stats` to see your solved cases count."
            ),
            "professor": (
                "**📝 Professor Instruction:**\n"
                "Your goal is to validate AI accuracy based on student feedback.\n"
                "1. Click `📝 Review Corrections` to see pending feedback.\n"
                "2. Read the student's comment and the original AI answer.\n"
                "3. **Approve**: If the student's correction is valid.\n"
                "4. **Reject**: If the AI was actually correct or the feedback is invalid."
            ),
            "admin": (
                "**👑 Admin/Manager Instruction:**\n"
                "You have full system control.\n"
                "1. **Manage Users**: Click `👥 Manage Users` to see pending registrations.\n"
                "2. **Promote**: Use `/promote <id> <role>` to grant access (e.g., `/promote 12345 student`).\n"
                "3. **System Audit**: Use `/help` and `👤 Profile` to monitor all role abilities.\n"
                "4. **Knowledge Base**: Use `⚙️ Developer Tools` to add legal documents."
            ),
            "developer": (
                "**⚙️ Developer Instruction:**\n"
                "Manage the RAG knowledge base.\n"
                "1. **Ingest Files**: Use `/upload` and send a PDF, DOCX, or MD file.\n"
                "2. **Ingest Links**: Use `/ingest_link` and provide a URL to scrape.\n"
                "3. **Verification**: The bot will confirm how many 'chunks' were added to Pinecone."
            )
        }
    }
    
    h = help_texts.get(lang, help_texts["ru"])
    help_text = h["header"] + h.get(role, "")
    
    await message.answer(help_text, parse_mode="Markdown")

@router.message(F.text.in_(["👤 Profile", "👤 Профиль"]))
async def show_profile(message: types.Message):
    logging.info(f"User {message.from_user.id} requested Profile")
    user = await UserRepository.get_user(message.from_user.id)
    if user:
        role = user.get('actual_role', user.get('role', 'guest'))
        lang = user.get("language", "ru")
        
        # Define role-specific abilities
        abilities = {
            "ru": {
                "guest": "• **Чат**: Задавайте вопросы ИИ о праве Казахстана.\n• **Регистрация**: Заполните регистрационную форму.\n• **Ожидание**: Администратор должен одобрить вашу роль.",
                "student": (
                    "• 💬 **Чат**: Общайтесь с ИИ, оценивайте ответы и добавляйте комментарии.\n"
                    "• 🎓 **Решение кейсов**: Получайте ответы ИИ на правовые сценарии.\n"
                    "• 📊 **Статистика**: Следите за количеством решенных кейсов.\n"
                    "• 📝 **Улучшение ИИ**: Предлагайте исправления, если ИИ ошибается."
                ),
                "professor": (
                    "• 💬 **Чат**: Общайтесь с ИИ, оценивайте ответы и добавляйте комментарии.\n"
                    "• 📝 **Очередь проверки**: Проверяйте исправления студентов.\n"
                    "• ✅ **Одобрение/Отказ**: Поддерживайте правовую точность системы."
                ),
                "admin": (
                    "• 💬 **Чат**: Общайтесь с ИИ, оценивайте ответы и добавляйте комментарии.\n"
                    "• 👑 **Управление**: Доступ ко всем инструментам Студента и Профессора.\n"
                    "• 👥 **Управление пользователями**: Одобряйте или меняйте роли пользователей.\n"
                    "• ⚙️ **Загрузка данных**: Добавляйте новые документы в базу знаний."
                ),
                "developer": (
                    "• 💬 **Чат**: Общайтесь с ИИ, оценивайте ответы и добавляйте комментарии.\n"
                    "• 📥 **Загрузка документов**: Загружайте PDF/DOCX/MD файлы.\n"
                    "• 🔗 **Веб-скрейпинг**: Загружайте контент напрямую по URL."
                )
            },
            "en": {
                "guest": "• **Chat**: Ask questions to AI about Kazakhstan law.\n• **Register**: Complete the registration form.\n• **Wait**: Admin must approve your requested role.",
                "student": (
                    "• 💬 **Chat**: Chat with AI, rate answers, and add comments.\n"
                    "• 🎓 **Solve Cases**: Get AI-generated answers for legal scenarios.\n"
                    "• 📊 **Track Progress**: Monitor your solved cases count.\n"
                    "• 📝 **Improve AI**: Suggest corrections if the AI makes a mistake."
                ),
                "professor": (
                    "• 💬 **Chat**: Chat with AI, rate answers, and add comments.\n"
                    "• 📝 **Review Queue**: Validate student-suggested corrections.\n"
                    "• ✅ **Approve/Reject**: Maintain legal accuracy in the system."
                ),
                "admin": (
                    "• 💬 **Chat**: Chat with AI, rate answers, and add comments.\n"
                    "• 👑 **System Control**: Access all Student and Professor tools.\n"
                    "• 👥 **User Management**: Approve or manually change user roles.\n"
                    "• ⚙️ **Data Ingestion**: Add new legal documents to the knowledge base."
                ),
                "developer": (
                    "• 💬 **Chat**: Chat with AI, rate answers, and add comments.\n"
                    "• 📥 **Document Ingestion**: Upload PDF/DOCX/MD files.\n"
                    "• 🔗 **Web Scraping**: Ingest content directly from URLs."
                )
            }
        }
        
        ability_text = abilities.get(lang, abilities["ru"]).get(role, "No specific info available.")
        
        labels = {
            "ru": {"name": "Имя", "role": "Роль", "requested": "Запрошена", "solved": "Решено кейсов", "abilities": "✨ **Ваши возможности:**"},
            "en": {"name": "Name", "role": "Role", "requested": "Requested", "solved": "Cases Solved", "abilities": "✨ **Your Abilities:**"}
        }
        l = labels.get(lang, labels["ru"])

        text = (
            f"👤 **{I18n.t('profile', lang)}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{l['name']}: {user.get('full_name')}\n"
            f"{l['role']}: `{role}`\n"
            f"{l['requested']}: `{user.get('requested_role')}`\n"
            f"{l['solved']}: {user.get('cases_solved_count', user.get('cases_solved', 0))}\n\n"
            f"{l['abilities']}\n"
            f"{ability_text}"
        )
        await message.answer(text, parse_mode="Markdown")
