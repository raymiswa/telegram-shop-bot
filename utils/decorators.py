from functools import wraps
from config import ADMIN_IDS


def admin_required(func):
    @wraps(func)
    async def wrapper(update, context):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("❌ Нет доступа!")
            elif update.message:
                await update.message.reply_text("❌ У вас нет доступа к админ-панели!")
            return
        return await func(update, context)
    return wrapper
