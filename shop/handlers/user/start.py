from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from database.database import AsyncSessionLocal
from database.crud import get_or_create_user
from keyboards.user import main_menu_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with AsyncSessionLocal() as session:
        await get_or_create_user(session, user.id, user.username)
    cart_count = sum(context.user_data.get("cart", {}).values())
    await update.message.reply_text(
        f"👋 Добро пожаловать в магазин, {user.first_name}!\n\nВыберите раздел:",
        reply_markup=main_menu_keyboard(cart_count),
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *О магазине*\n\n"
        "🛍 Широкий ассортимент товаров\n"
        "💎 Оплата USDT TRC20 и наличными\n"
        "🏪 Самовывоз из удобных точек\n\n"
        "По вопросам: обращайтесь к администратору.",
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^ℹ️ О магазине$"), about))
