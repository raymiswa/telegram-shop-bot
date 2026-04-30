from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from utils.decorators import admin_required
from keyboards.admin import admin_main_keyboard


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "⚙️ *Админ-панель*\n\nВыберите раздел:",
        reply_markup=admin_main_keyboard(),
        parse_mode="Markdown",
    )


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚙️ *Админ-панель*\n\nВыберите раздел:",
        parse_mode="Markdown",
    )
    await query.message.reply_text("Меню:", reply_markup=admin_main_keyboard())


def register(app):
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
