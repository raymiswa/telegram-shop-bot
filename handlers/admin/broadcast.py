from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters,
)
from database.database import AsyncSessionLocal
from database.crud import get_all_users
from utils.decorators import admin_required

WAITING_MESSAGE = 0


@admin_required
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📬 *Рассылка*\n\nВведите текст сообщения для отправки всем пользователям:",
        parse_mode="Markdown",
    )
    return WAITING_MESSAGE


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    async with AsyncSessionLocal() as session:
        users = await get_all_users(session)

    sent = 0
    failed = 0
    for user in users:
        if user.is_blocked:
            continue
        try:
            await context.bot.send_message(user.telegram_id, text)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ Рассылка завершена!\n\nОтправлено: {sent}\nОшибок: {failed}"
    )
    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Рассылка отменена.")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^📬 Рассылка$"), broadcast_start)],
        states={
            WAITING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", cancel_broadcast)],
        per_chat=True,
        per_user=True,
    )
    app.add_handler(conv)
