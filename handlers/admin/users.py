from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from database.database import AsyncSessionLocal
from database.crud import get_all_users
from utils.decorators import admin_required
from utils.formatters import fmt_dt


@admin_required
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        users = await get_all_users(session)

    if not users:
        await update.message.reply_text("👥 Пользователей нет.")
        return

    lines = [
        f"@{u.username or '—'} (ID: {u.telegram_id}) | {'🚫' if u.is_blocked else '✅'} | {fmt_dt(u.created_at)}"
        for u in users[:50]
    ]
    text = f"👥 *Пользователи* ({len(users)}):\n\n" + "\n".join(lines)
    if len(users) > 50:
        text += f"\n\n... и ещё {len(users) - 50}"
    await update.message.reply_text(text, parse_mode="Markdown")


def register(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^👥 Пользователи$"), show_users))
