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
    await message.answer(I18n.t("select_role", lang), reply_markup=role_selection_kb())
    await state.set_state(RegistrationState.waiting_for_role)

@router.callback_query(RegistrationState.waiting_for_role, F.data.startswith("role_"))
async def process_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    logging.info(f"User {callback.from_user.id} selected role: {role}")
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    await UserRepository.create_user(
        telegram_id=callback.from_user.id,
        full_name=data['full_name'],
        email=data['email'],
        role=role,
        language=lang
    )
    
    # We could translate these too, but for brevity I'll use a translated wrapper
    await callback.message.edit_text(
        I18n.t("reg_received", lang, role=role) + "\n\n" + I18n.t("guest_info", lang),
        parse_mode="Markdown"
    )
    
    # Mock Admin Notification
    logging.info(f"🔔 [ADMIN NOTIFICATION] User {callback.from_user.id} ({data['full_name']}) requested role: {role}")
    
    # Refresh menu
    await callback.message.answer(I18n.t("main_menu", lang), reply_markup=get_main_menu("guest", lang))
    await state.clear()
    await callback.answer()
