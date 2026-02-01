from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from legally_bot.states.states import RegistrationState
from legally_bot.keyboards.keyboards import role_selection_kb, get_main_menu
from legally_bot.database.users_repo import UserRepository
import logging

router = Router()

async def start_registration(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} started registration")
    await message.answer("Welcome to Legally! Let's get you registered.\nPlease enter your **Full Name**:")
    await state.set_state(RegistrationState.waiting_for_name)

@router.message(RegistrationState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} provided name: {message.text}")
    await state.update_data(full_name=message.text)
    await message.answer("Great! Now please enter your **Email Address**:")
    await state.set_state(RegistrationState.waiting_for_email)

@router.message(RegistrationState.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} provided email: {message.text}")
    await state.update_data(email=message.text)
    await message.answer("Which role would you like to apply for?", reply_markup=role_selection_kb())
    await state.set_state(RegistrationState.waiting_for_role)

@router.callback_query(RegistrationState.waiting_for_role, F.data.startswith("role_"))
async def process_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    logging.info(f"User {callback.from_user.id} selected role: {role}")
    data = await state.get_data()
    
    await UserRepository.create_user(
        telegram_id=callback.from_user.id,
        full_name=data['full_name'],
        email=data['email'],
        role=role
    )
    
    abilities = {
        "student": "• Solve legal cases with AI.\n• Suggest corrections to AI answers.",
        "professor": "• Review student corrections.\n• Validate legal accuracy.",
        "admin": "• Manage users and system tools.",
        "developer": "• Ingest documents and links into the knowledge base."
    }
    role_info = abilities.get(role, "Access to role-specific features.")

    await callback.message.edit_text(
        f"✅ **Registration Received!**\n\n"
        f"You requested the **{role}** role. An admin will review it shortly.\n\n"
        f"Your future abilities as a **{role}**:\n"
        f"{role_info}\n\n"
        f"You currently have 'guest' access.",
        parse_mode="Markdown"
    )
    
    # Mock Admin Notification
    logging.info(f"🔔 [ADMIN NOTIFICATION] User {callback.from_user.id} ({data['full_name']}) requested role: {role}")
    
    # Refresh menu
    await callback.message.answer("Main Menu:", reply_markup=get_main_menu("guest"))
    await state.clear()
    await callback.answer()
