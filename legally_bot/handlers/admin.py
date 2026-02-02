from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from legally_bot.services.access_control import AccessControl
from legally_bot.database.users_repo import UserRepository
import logging

from legally_bot.services.i18n import I18n

router = Router()

@router.message(F.text.in_(["👥 Manage Users", "👥 Управление пользователями"]))
@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    logging.info(f"Admin {message.from_user.id} accessed User Management")
    user = await UserRepository.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    if not await AccessControl.is_admin(message.from_user.id):
        return await message.answer(I18n.t("no_access", lang))
    
    pending = await UserRepository.get_pending_role_requests()
    if not pending:
        msg = "No pending role requests." if lang == "en" else "Нет ожидающих запросов ролей."
        await message.answer(msg)
        return
    
    text = "Pending Requests:\n\n" if lang == "en" else "Ожидающие запросы:\n\n"
    for u in pending:
        text += f"ID: `{u['telegram_id']}` | Name: {u['full_name']} | Requested: {u['requested_role']}\n"
    
    hint = "\nTo approve, use: `/promote <id> <role>`" if lang == "en" else "\nДля одобрения используйте: `/promote <id> <role>`"
    text += hint
    await message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("adm_"))
async def process_admin_role_callback(callback: types.CallbackQuery, bot: Bot):
    if not await AccessControl.is_admin(callback.from_user.id):
        return await callback.answer("Access denied.")
    
    # adm_appr_{user_id}_{role} or adm_reje_{user_id}_{role}
    parts = callback.data.split("_")
    action = parts[1]
    target_id = int(parts[2])
    role = parts[3]
    
    user = await UserRepository.get_user(target_id)
    lang = user.get("language", "ru") if user else "ru"

    if action == "appr":
        await UserRepository.update_role(target_id, role)
        # Clear requested role once approved
        await UserRepository.set_requested_role(target_id, role)
        await callback.message.edit_text(callback.message.md_text + f"\n\n✅ **Approved as {role}**")
        try:
            await bot.send_message(target_id, I18n.t("role_approved", lang, role=role))
        except: pass
    else:
        # Reset requested role on rejection
        actual_role = user.get("actual_role", "guest")
        await UserRepository.set_requested_role(target_id, actual_role)
        await callback.message.edit_text(callback.message.md_text + f"\n\n❌ **Rejected**")
        try:
            await bot.send_message(target_id, I18n.t("role_rejected", lang, role=role))
        except: pass
        
    await callback.answer()

@router.message(Command("promote"))
async def promote_user(message: types.Message):
    if not await AccessControl.is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    logging.info(f"Admin {message.from_user.id} attempted promote: {message.text}")
    if len(args) != 3:
        await message.answer("Usage: /promote <telegram_id> <role>")
        return
    
    try:
        target_id = int(args[1])
        new_role = args[2]
        
        if new_role not in ["student", "professor", "admin", "user"]:
            await message.answer("Invalid role. Options: student, professor, admin, user")
            return
            
        await UserRepository.update_role(target_id, new_role)
        await message.answer(f"✅ User {target_id} promoted to {new_role}.")
        # Ideally, notify the user too.
    except ValueError:
        await message.answer("Invalid ID format.")
