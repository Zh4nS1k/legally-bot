from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from legally_bot.states.states import RegistrationState
from legally_bot.keyboards.keyboards import get_main_menu
from legally_bot.database.users_repo import UserRepository
from legally_bot.services.email_service import EmailService
import logging

from legally_bot.services.i18n import I18n

router = Router()

@router.message(RegistrationState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} provided name: {message.text}")
    
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    if not EmailService.is_valid_name(message.text):
        await message.answer(I18n.t("invalid_name", lang))
        return

    await state.update_data(full_name=message.text)
    await message.answer(I18n.t("enter_email", lang), parse_mode="Markdown")
    await state.set_state(RegistrationState.waiting_for_email)

@router.message(RegistrationState.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} provided email: {message.text}")
    
    data = await state.get_data()
    lang = data.get("language", "ru")
    email = message.text.strip()
    
    if not EmailService.is_valid_email(email):
        await message.answer(I18n.t("invalid_email", lang))
        return

    # Generate and send code
    code = EmailService.generate_code()
    sent = await EmailService.send_verification_code(email, code)
    
    if sent:
        await state.update_data(email=email, verification_code=code)
        await message.answer(
            I18n.t("code_sent", lang, email=email) + "\n" + I18n.t("enter_code", lang),
            parse_mode="Markdown"
        )
        await state.set_state(RegistrationState.waiting_for_code)
    else:
        # Fallback if email fails (e.g. bad config), maybe allow to proceed or ask to retry
        # For now, let's just log and maybe accept it for testing? 
        # Or better -> tell user something went wrong
        # But per requirements we need confirmation.
        # If SMTP is not configured, it returns False.
        # Let's show generic error or just accept it if it's a dev env?
        # Reverting to accepting it if we can't send email is risky for validation. 
        # But if the user didn't setup SMTP, this blocks them.
        # I'll inform them.
        logging.error("Failed to send code. SMTP might be down.")
        await message.answer("⚠️ System Error: Could not send verification code. Please contact support.")

@router.message(RegistrationState.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    code_input = message.text.strip()
    data = await state.get_data()
    lang = data.get("language", "ru")
    correct_code = data.get("verification_code")
    
    if code_input != correct_code:
        await message.answer(I18n.t("wrong_code", lang))
        return
        
    # Code is correct, proceed to registration
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
    
    logging.info(f"User {message.from_user.id} successfully verified email and registered as {role}")
    await state.clear()
