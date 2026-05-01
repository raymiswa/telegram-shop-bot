from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from keyboards.user import cart_keyboard


async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart = context.user_data.get("cart", {})

    if not cart:
        from keyboards.user import main_menu_keyboard
        await query.edit_message_text(
            "🧺 Ваша корзина пуста.\n\nДобавьте товары из каталога!",
            reply_markup=main_menu_keyboard(0),
        )
        return

    lines = []
    total = 0.0
    for pid, item in cart.items():
        subtotal = item["price"] * item["qty"]
        total += subtotal
        lines.append(f"• {item['name']} ×{item['qty']} = {subtotal:.0f}₽")

    text = "🧺 *Ваша корзина:*\n\n" + "\n".join(lines) + f"\n\n💰 *Итого: {total:.0f}₽*"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=cart_keyboard(cart))


async def delete_cart_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = query.data.split(":")[1]
    cart = context.user_data.get("cart", {})
    cart.pop(product_id, None)
    context.user_data["cart"] = cart
    query.data = "cart"
    await show_cart(update, context)


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🗑 Корзина очищена")
    context.user_data["cart"] = {}
    from keyboards.user import main_menu_keyboard
    await query.edit_message_text(
        "🧺 Корзина очищена.",
        reply_markup=main_menu_keyboard(0),
    )


def register(app):
    app.add_handler(CallbackQueryHandler(show_cart, pattern="^cart$"))
    app.add_handler(CallbackQueryHandler(delete_cart_item, pattern=r"^del_cart:\d+$"))
    app.add_handler(CallbackQueryHandler(clear_cart, pattern="^clear_cart$"))
