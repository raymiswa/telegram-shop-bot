from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.database import AsyncSessionLocal
from database.crud import get_or_create_user
from keyboards.user import main_menu_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with AsyncSessionLocal() as session:
        await get_or_create_user(session, user.id, user.username, user.first_name or "")

    cart = context.user_data.get("cart", {})
    cart_count = sum(v["qty"] for v in cart.values())
    text = (
        f"👋 Добро пожаловать, {user.first_name}!\n\n"
        "🛍 Это наш магазин. Выберите раздел:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(cart_count))
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(cart_count))


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "ℹ️ *О магазине*\n\n"
        "Мы рады приветствовать вас в нашем магазине!\n"
        "Принимаем оплату: 💎 USDT TRC20 и 💵 наличными.\n\n"
        "По вопросам обращайтесь к администратору.",
        parse_mode="Markdown",
        reply_markup=__import__("telegram").InlineKeyboardMarkup([
            [__import__("telegram").InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]),
    )


def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(about, pattern="^about$"))
