from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from legally_bot.states.states import RegistrationState
from legally_bot.keyboards.keyboards import role_selection_kb, get_main_menu
from legally_bot.database.users_repo import UserRepository
import logging

from legally_bot.services.i18n import I18n

router = Router()

# start_registration is no longer called directly from cmd_start, 
# it's integrated into the language selection flow in common.py

@router.message(RegistrationState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} provided name: {message.text}")
    await state.update_data(full_name=message.text)
    data = await state.get_data()
    lang = data.get("language", "ru")
    await message.answer(I18n.t("enter_email", lang), parse_mode="Markdown")
    await state.set_state(RegistrationState.waiting_for_email)

@router.message(RegistrationState.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} provided email: {message.text}")
    await state.update_data(email=message.text)
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    role = "guest"
    
    await UserRepository.create_user(
        telegram_id=message.from_user.id,
        full_name=data['full_name'],
        email=data['email'],
        role=role,
        language=lang
    )
    
    await message.answer(
        I18n.t("reg_received", lang, role=role) + "\n\n" + I18n.t("guest_info", lang),
        reply_markup=get_main_menu("guest", lang),
        parse_mode="Markdown"
    )
    
    logging.info(f"User {message.from_user.id} registered as {role}")
    await state.clear()
