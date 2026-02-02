from legally_bot.database.mongo_db import db
from datetime import datetime

class UserRepository:
    collection = "users"

    @classmethod
    async def get_user(cls, telegram_id: int):
        return await db.get_db()[cls.collection].find_one({"telegram_id": telegram_id})

    @classmethod
    async def create_user(cls, telegram_id: int, full_name: str, email: str, role: str, language: str = "ru"):
        user_data = {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "email": email,
            "requested_role": role,
            "actual_role": "guest",  # Default role
            "language": language,
            "cases_solved_count": 0,
            "created_at": datetime.utcnow()
        }
        await db.get_db()[cls.collection].insert_one(user_data)
        return user_data

    @classmethod
    async def update_language(cls, telegram_id: int, language: str):
        await db.get_db()[cls.collection].update_one(
            {"telegram_id": telegram_id},
            {"$set": {"language": language}}
        )

    @classmethod
    async def update_role(cls, telegram_id: int, new_role: str):
        await db.get_db()[cls.collection].update_one(
            {"telegram_id": telegram_id},
            {"$set": {"actual_role": new_role}}
        )

    @classmethod
    async def get_users_by_role(cls, role: str):
        cursor = db.get_db()[cls.collection].find({"role": role})
        return await cursor.to_list(length=100)
    
    @classmethod
    async def get_pending_role_requests(cls):
        # Users who have a requested_role different from their actual_role (and actual is still 'user')
        cursor = db.get_db()[cls.collection].find({
            "requested_role": {"$ne": "user"},
            "actual_role": "user"
        })
        return await cursor.to_list(length=100)

    @classmethod
    async def increment_cases_solved(cls, telegram_id: int):
        await db.get_db()[cls.collection].update_one(
            {"telegram_id": telegram_id},
            {"$inc": {"cases_solved": 1}}
        )
