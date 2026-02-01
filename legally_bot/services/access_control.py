from legally_bot.database.users_repo import UserRepository

class AccessControl:
    @staticmethod
    async def is_admin(telegram_id: int) -> bool:
        user = await UserRepository.get_user(telegram_id)
        if not user:
            return False
        return user.get("actual_role") == "admin"

    @staticmethod
    async def is_professor(telegram_id: int) -> bool:
        user = await UserRepository.get_user(telegram_id)
        if not user:
            return False
        return user.get("actual_role") in ["professor", "admin"]

    @staticmethod
    async def is_student(telegram_id: int) -> bool:
        user = await UserRepository.get_user(telegram_id)
        if not user:
            return False
        return user.get("actual_role") in ["student", "admin", "professor"]

    @staticmethod
    async def is_developer(telegram_id: int) -> bool:
        user = await UserRepository.get_user(telegram_id)
        if not user:
            return False
        
        role = user.get("actual_role")
        if role == "admin":
            return True
            
        # Also check against hardcoded admin IDs in config for Developer access
        from legally_bot.config import settings
        return telegram_id in settings.admin_ids_list
