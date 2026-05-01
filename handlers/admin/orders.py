from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from database.database import AsyncSessionLocal
from database.crud import get_all_orders, get_order, update_order_status
from keyboards.admin import admin_orders_keyboard, admin_order_actions_keyboard
from utils.decorators import admin_required
from utils.formatters import fmt_status, fmt_dt, fmt_price


@admin_required
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        orders = await get_all_orders(session)
    text = f"📦 *Заказы* ({len(orders)}):"
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_orders_keyboard(orders, "all"),
    )


@admin_required
async def show_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_filter = query.data.split(":")[1] if ":" in query.data else "all"
    status = None if status_filter == "all" else status_filter
    async with AsyncSessionLocal() as session:
        orders = await get_all_orders(session, status=status)
    text = f"📦 *Заказы* ({len(orders)}):"
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_orders_keyboard(orders, status_filter),
    )


@admin_required
async def show_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)

    if not order:
        await query.edit_message_text("❌ Заказ не найден.")
        return

    lines = [
        f"• {item.product_name} ×{item.quantity} = {float(item.price) * item.quantity:.0f}₽"
        for item in order.items
    ]
    pickup_info = ""
    if order.pickup_point:
        pickup_info = f"\n📍 {order.pickup_point.name}\n📦 Код: {order.pickup_code}"

    text = (
        f"📦 *Заказ #{order.id}*\n\n"
        f"👤 @{order.user.username or '—'} (ID: {order.user.telegram_id})\n"
        f"📞 {order.phone}\n"
        f"Статус: {fmt_status(order.status)}\n"
        f"Дата: {fmt_dt(order.created_at)}\n\n"
        + "\n".join(lines)
        + f"\n\n💰 Итого: *{fmt_price(order.total_price)}*"
        + (f"\n💎 USDT: *{float(order.total_price_usdt):.2f}*" if order.total_price_usdt else "")
        + (f"\n💬 {order.comment}" if order.comment else "")
        + pickup_info
    )
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_order_actions_keyboard(order.id, order.status),
    )


@admin_required
async def change_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    order_id = int(parts[1])
    new_status = parts[2]

    async with AsyncSessionLocal() as session:
        order = await update_order_status(session, order_id, new_status)

    if not order:
        await query.edit_message_text("❌ Заказ не найден.")
        return

    if order.user and new_status in ("ready", "completed", "cancelled"):
        status_messages = {
            "ready": f"✅ Ваш заказ #{order_id} готов к выдаче!\n📦 Код получения: *{order.pickup_code}*",
            "completed": f"✔️ Ваш заказ #{order_id} завершён. Спасибо!",
            "cancelled": f"❌ Ваш заказ #{order_id} отменён.",
        }
        try:
            await context.bot.send_message(
                order.user.telegram_id,
                status_messages[new_status],
                parse_mode="Markdown",
            )
        except Exception:
            pass

    await query.edit_message_text(
        f"✅ Статус заказа #{order_id} изменён на: {fmt_status(new_status)}",
        reply_markup=admin_order_actions_keyboard(order.id, new_status),
    )


def register(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📦 Заказы$"), show_orders))
    app.add_handler(CallbackQueryHandler(show_orders_callback, pattern=r"^admin_orders:(all|new|paid|ready|completed|cancelled)$"))
    app.add_handler(CallbackQueryHandler(show_order_detail, pattern=r"^admin_order:\d+$"))
    app.add_handler(CallbackQueryHandler(change_order_status, pattern=r"^order_status:\d+:\w+$"))
