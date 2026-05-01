from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from keyboards.admin import admin_main_keyboard
from utils.decorators import admin_required


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔧 *Панель администратора*\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=admin_main_keyboard(),
    )


def register(app):
    app.add_handler(CommandHandler("admin", admin_panel))
