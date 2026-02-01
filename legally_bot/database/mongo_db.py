from motor.motor_asyncio import AsyncIOMotorClient
from legally_bot.config import settings
import logging

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    def connect(cls):
        try:
            cls.client = AsyncIOMotorClient(settings.MONGO_URI)
            cls.db = cls.client[settings.DB_NAME]
            logging.info(f"✅ Connected to MongoDB: {settings.DB_NAME}")
        except Exception as e:
            logging.error(f"Could not connect to MongoDB: {e}", exc_info=True)
            raise e

    @classmethod
    def close(cls):
        if cls.client:
            cls.client.close()
            logging.info("Closed MongoDB connection")

    @classmethod
    def get_db(cls):
        return cls.db

db = MongoDB
