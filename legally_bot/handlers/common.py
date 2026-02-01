from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from legally_bot.database.users_repo import UserRepository
from legally_bot.keyboards.keyboards import get_main_menu
from legally_bot.services.access_control import AccessControl
import logging

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} called /start")
    user = await UserRepository.get_user(message.from_user.id)
    if not user:
        from legally_bot.handlers.registration import start_registration
        await start_registration(message, state)
    else:
        role = user.get("actual_role", user.get("role", "guest"))
        await message.answer(
            f"Welcome back, {user.get('full_name')}! You are logged in as **{role}**.",
            reply_markup=get_main_menu(role),
            parse_mode="Markdown"
        )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    logging.info(f"User {message.from_user.id} called /help")
    user = await UserRepository.get_user(message.from_user.id)
    role = "guest"
    if user:
        role = user.get('actual_role', user.get('role', 'guest'))
    
    help_text = (
        "⚖️ **Legally Bot: User Guide**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "This bot is designed to assist with legal training and document management using AI.\n\n"
        "**General Navigation:**\n"
        "• `/start` - Return to the main menu at any time.\n"
        "• `/help` - View this instruction manual.\n"
        "• `👤 Profile` - Check your status and stats.\n\n"
        "**Your Role-Specific Guide:**\n"
    )
    
    if role == "guest":
        help_text += (
            "**👋 Welcome, Guest!**\n"
            "To unlock the bot's full potential, you must register:\n"
            "1. Type `/start` if you haven't.\n"
            "2. Provide your Full Name and Email.\n"
            "3. Select a role (Student or Professor).\n"
            "4. Wait for Admin approval."
        )
    elif role == "student":
        help_text += (
            "**🎓 Student Instruction:**\n"
            "1. **Solve Cases**: Click `🎓 Get Case`. AI will analyze a legal scenario. Read the answer and check the `📚 Sources`.\n"
            "2. **Give Feedback**: After an AI answer, use the buttons:\n"
            "   - ✅ `Everything Correct`: If you agree with the AI.\n"
            "   - ⚠️ `Logic Error`: If the reasoning is flawed.\n"
            "   - ❌ `Wrong Article`: If a legal article is cited incorrectly.\n"
            "3. **Track Progress**: Click `📊 My Stats` to see your solved cases count."
        )
    elif role == "professor":
        help_text += (
            "**📝 Professor Instruction:**\n"
            "Your goal is to validate AI accuracy based on student feedback.\n"
            "1. Click `📝 Review Corrections` to see pending feedback.\n"
            "2. Read the student's comment and the original AI answer.\n"
            "3. **Approve**: If the student's correction is valid.\n"
            "4. **Reject**: If the AI was actually correct or the feedback is invalid."
        )
    elif role == "admin":
        help_text += (
            "**👑 Admin/Manager Instruction:**\n"
            "You have full system control.\n"
            "1. **Manage Users**: Click `👥 Manage Users` to see pending registrations.\n"
            "2. **Promote**: Use `/promote <id> <role>` to grant access (e.g., `/promote 12345 student`).\n"
            "3. **System Audit**: Use `/help` and `👤 Profile` to monitor all role abilities.\n"
            "4. **Knowledge Base**: Use `⚙️ Developer Tools` to add legal documents."
        )
    elif role == "developer":
        help_text += (
            "**⚙️ Developer Instruction:**\n"
            "Manage the RAG knowledge base.\n"
            "1. **Ingest Files**: Use `/upload` and send a PDF, DOCX, or MD file.\n"
            "2. **Ingest Links**: Use `/ingest_link` and provide a URL to scrape.\n"
            "3. **Verification**: The bot will confirm how many 'chunks' were added to Pinecone."
        )
    
    await message.answer(help_text, parse_mode="Markdown")

@router.message(F.text == "👤 Profile")
async def show_profile(message: types.Message):
    logging.info(f"User {message.from_user.id} requested Profile")
    user = await UserRepository.get_user(message.from_user.id)
    if user:
        role = user.get('actual_role', user.get('role', 'guest'))
        
        # Define role-specific abilities
        abilities = {
            "guest": "• **Register**: Complete the registration form.\n• **Wait**: Admin must approve your requested role.",
            "student": (
                "• 🎓 **Solve Cases**: Get AI-generated answers for legal scenarios.\n"
                "• 📊 **Track Progress**: Monitor your solved cases count.\n"
                "• 📝 **Improve AI**: Suggest corrections if the AI makes a mistake."
            ),
            "professor": (
                "• 📝 **Review Queue**: Validate student-suggested corrections.\n"
                "• ✅ **Approve/Reject**: Maintain legal accuracy in the system."
            ),
            "admin": (
                "• 👑 **System Control**: Access all Student and Professor tools.\n"
                "• 👥 **User Management**: Approve or manually change user roles.\n"
                "• ⚙️ **Data Ingestion**: Add new legal documents to the knowledge base."
            ),
            "developer": (
                "• 📥 **Document Ingestion**: Upload PDF/DOCX/MD files.\n"
                "• 🔗 **Web Scraping**: Ingest content directly from URLs."
            )
        }
        
        ability_text = abilities.get(role, "No specific info available.")
        
        text = (
            f"👤 **Profile**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Name: {user.get('full_name')}\n"
            f"Role: `{role}`\n"
            f"Requested: `{user.get('requested_role')}`\n"
            f"Cases Solved: {user.get('cases_solved_count', user.get('cases_solved', 0))}\n\n"
            f"✨ **Your Abilities:**\n"
            f"{ability_text}"
        )
        await message.answer(text, parse_mode="Markdown")
