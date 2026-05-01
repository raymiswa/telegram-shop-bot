from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from database.database import AsyncSessionLocal
from database.crud import get_user_orders, get_order, cancel_order, get_or_create_user
from utils.formatters import fmt_price, fmt_dt, fmt_status


async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_filter = query.data.split(":")[1] if ":" in query.data else "all"

    user = update.effective_user
    async with AsyncSessionLocal() as session:
        db_user = await get_or_create_user(session, user.id, user.username, user.first_name or "")
        orders = await get_user_orders(session, db_user.id)

    if status_filter == "active":
        orders = [o for o in orders if o.status not in ("completed", "cancelled")]

    if not orders:
        await query.edit_message_text(
            "📋 У вас нет заказов.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
            ]),
        )
        return

    buttons = []
    for order in orders[:20]:
        label = f"#{order.id} {fmt_status(order.status)} — {fmt_price(order.total_price)}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"order:{order.id}")])

    buttons.append([
        InlineKeyboardButton("Все", callback_data="orders:all"),
        InlineKeyboardButton("Активные", callback_data="orders:active"),
    ])
    buttons.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    await query.edit_message_text(
        f"📋 *Мои заказы* ({len(orders)}):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)

    if not order:
        await query.edit_message_text("❌ Заказ не найден.")
        return

    lines = [f"• {item.product_name} ×{item.quantity} = {float(item.price) * item.quantity:.0f}₽" for item in order.items]
    pickup_info = ""
    if order.pickup_point:
        pickup_info = f"\n📍 Точка выдачи: {order.pickup_point.name}\n📦 Код: *{order.pickup_code}*"

    text = (
        f"📦 *Заказ #{order.id}*\n\n"
        f"Статус: {fmt_status(order.status)}\n"
        f"Дата: {fmt_dt(order.created_at)}\n\n"
        + "\n".join(lines)
        + f"\n\n💰 Итого: *{fmt_price(order.total_price)}*"
        + (f"\n💎 USDT: *{float(order.total_price_usdt):.2f}*" if order.total_price_usdt else "")
        + pickup_info
    )
    from keyboards.user import order_detail_keyboard
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=order_detail_keyboard(order.id, order.status))


async def cancel_user_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("❌ Заказ отменён")
    order_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        order = await cancel_order(session, order_id)

    if order:
        await query.edit_message_text(
            f"❌ Заказ #{order_id} отменён.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Мои заказы", callback_data="orders:all")]
            ]),
        )
    else:
        await query.edit_message_text("❌ Заказ не найден.")


def register(app):
    app.add_handler(CallbackQueryHandler(show_orders, pattern=r"^orders:(all|active)$"))
    app.add_handler(CallbackQueryHandler(show_order_detail, pattern=r"^order:\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_user_order, pattern=r"^cancel_order:\d+$"))
