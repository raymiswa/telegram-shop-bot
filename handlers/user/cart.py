from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from database.database import AsyncSessionLocal
from database.crud import get_product
from keyboards.user import cart_items_keyboard, main_menu_keyboard
from utils.formatters import fmt_price


async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart: dict = context.user_data.get("cart", {})
    if not cart:
        text = "🛒 Ваша корзина пуста."
        kb = None
    else:
        async with AsyncSessionLocal() as session:
            lines = []
            total = 0.0
            cart_products = []
            for pid, qty in list(cart.items()):
                p = await get_product(session, int(pid))
                if p and p.is_available:
                    subtotal = float(p.price) * qty
                    total += subtotal
                    lines.append(f"• {p.name} × {qty} = {fmt_price(subtotal)}")
                    cart_products.append((pid, p.name))
                else:
                    del cart[pid]

        if not lines:
            text = "🛒 Ваша корзина пуста."
            kb = None
        else:
            text = "🛒 *Ваша корзина:*\n\n" + "\n".join(lines) + f"\n\n💰 Итого: {fmt_price(total)}"
            kb = cart_items_keyboard(cart_products)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Удалено из корзины")
    product_id = int(query.data.replace("cart_remove_", ""))
    cart = context.user_data.get("cart", {})
    cart.pop(product_id, None)
    await show_cart(update, context)


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Корзина очищена")
    context.user_data["cart"] = {}
    cart_count = 0
    await query.edit_message_text("🛒 Корзина очищена.", reply_markup=None)
    await query.message.reply_text("Выберите раздел:", reply_markup=main_menu_keyboard(cart_count))


def register(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🛒 Моя корзина"), show_cart))
    app.add_handler(CallbackQueryHandler(remove_from_cart, pattern=r"^cart_remove_\d+$"))
    app.add_handler(CallbackQueryHandler(clear_cart, pattern="^cart_clear$"))
