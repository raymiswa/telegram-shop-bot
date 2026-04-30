from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import config


def admin_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_IDS:
            from database.database import AsyncSessionLocal
            from database.crud import is_admin
            async with AsyncSessionLocal() as session:
                if not await is_admin(session, user_id):
                    await update.effective_message.reply_text("⛔ Нет доступа.")
                    return
        return await func(update, context, *args, **kwargs)
    return wrapper
