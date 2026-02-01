from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from typing import Callable, Dict, Any, Awaitable
import logging

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = "Unknown"
        username = "Unknown"
        event_type = "Unknown"

        if isinstance(event, Update):
            event_type = "Update"
            if event.message:
                user_id = event.message.from_user.id
                username = event.message.from_user.username or "NoUsername"
                text = event.message.text or "[Non-text message]"
                logging.info(f"📩 USER_ACTION | ID: {user_id} | Name: {event.message.from_user.full_name} (@{username}) | Msg: {text}")
            elif event.callback_query:
                user_id = event.callback_query.from_user.id
                username = event.callback_query.from_user.username or "NoUsername"
                data_val = event.callback_query.data
                logging.info(f"👆 USER_ACTION | ID: {user_id} | Name: {event.callback_query.from_user.full_name} (@{username}) | Callback: {data_val}")
        
        result = await handler(event, data)
        return result
