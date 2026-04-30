import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = "8061201371:AAEHogHvhKiWYqjdTEt6QNl3RI8lohM4c4k"

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop")]
    ]

    await update.message.reply_text(
        "Добро пожаловать!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== CALLBACK =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        print("NO CALLBACK")
        return

    await query.answer()

    print("CLICK:", query.data)

    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=f"Ты нажал: {query.data}"
    )

# ===== RUN =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle, pattern=".*"))

print("Bot started...")
app.run_polling(drop_pending_updates=True)
