from aiogram import Router, types, F
from aiogram.filters import Command
from legally_bot.services.access_control import AccessControl
from legally_bot.database.users_repo import UserRepository
import logging

router = Router()

@router.message(F.text == "👥 Manage Users")
@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    logging.info(f"Admin {message.from_user.id} accessed User Management")
    if not await AccessControl.is_admin(message.from_user.id):
        return await message.answer("Access Denied.")
    
    pending = await UserRepository.get_pending_role_requests()
    if not pending:
        await message.answer("No pending role requests.")
        return
    
    text = "Pending Requests:\n\n"
    for u in pending:
        text += f"ID: `{u['telegram_id']}` | Name: {u['full_name']} | Requested: {u['requested_role']}\n"
    
    text += "\nTo approve, use: `/promote <id> <role>`"
    await message.answer(text, parse_mode="Markdown")

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
