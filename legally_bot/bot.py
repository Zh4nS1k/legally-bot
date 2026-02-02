import os
import asyncio
import logging

from legally_bot.services.logging_setup import setup_logging

# Configure logging using custom setup
setup_logging()

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from legally_bot.config import settings
from legally_bot.database.mongo_db import MongoDB

# Import handlers
from legally_bot.handlers import common, registration, developer_tools, admin, student_mode, professor_mode, chat_handler

async def main():
    logging.info("✅ Logging initialized (File + Console)")
    
    # Initialize DB
    logging.info("🔌 Connecting to MongoDB...")
    MongoDB.connect()
    
    # Initialize Bot & Dispatcher
    logging.info("🤖 Initializing Bot...")
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Include Routers
    dp.include_router(common.router)
    dp.include_router(registration.router)
    dp.include_router(chat_handler.router)
    dp.include_router(student_mode.router)
    dp.include_router(professor_mode.router)
    dp.include_router(admin.router)
    dp.include_router(developer_tools.router)
    
    # Register Middleware
    from legally_bot.middlewares.logging_middleware import LoggingMiddleware
    dp.update.middleware(LoggingMiddleware())

    # Start Polling
    try:
        logging.info("🚀 Starting Legally Bot polling...")
        
        @dp.error()
        async def error_handler(event: types.ErrorEvent):
            logging.error(f"❌ Unhandled Exception in handler: {event.exception}", exc_info=event.exception)
            # Optionally notify the user or admin
            if event.update.message:
                await event.update.message.answer("⚠️ An internal error occurred. Our developers have been notified.")
        
        await dp.start_polling(bot)
    finally:
        MongoDB.close()
        await bot.session.close()

if __name__ == "__main__":
    logging.info("🚀 Launching Legally Bot...")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped by user.")
    except Exception as e:
        logging.error(f"❌ Critical Error: {e}")
        import traceback
        logging.error(traceback.format_exc())
