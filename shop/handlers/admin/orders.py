from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from database.database import AsyncSessionLocal
from database.crud import get_all_orders, count_all_orders, get_order, update_order_status
from keyboards.admin import orders_filter_keyboard, order_actions_keyboard, back_to_admin_keyboard
from utils.decorators import admin_required
from utils.formatters import fmt_price, fmt_usdt, fmt_status, fmt_dt
import config


@admin_required
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("admin_orders_filter", "all")
    status_filter = context.user_data.get("admin_orders_filter", "all")
    page = context.user_data.get("admin_orders_page", 0)
    sf = None if status_filter == "all" else status_filter

    async with AsyncSessionLocal() as session:
        total = await count_all_orders(session, sf)
        orders = await get_all_orders(session, sf, page * config.ORDERS_PER_PAGE, config.ORDERS_PER_PAGE)

    if not orders:
        text = "📋 Заказов нет."
    else:
        lines = [
            f"#{o.id} | {fmt_status(o.status)} | {fmt_price(o.total_price)} | @{o.user.username or o.user.telegram_id}"
            for o in orders
        ]
        text = f"📋 *Заказы* ({total}):\n\n" + "\n".join(lines)

    kb = orders_filter_keyboard(status_filter)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def filter_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    status_filter = query.data.replace("admin_orders_filter_", "")
    context.user_data["admin_orders_filter"] = status_filter
    context.user_data["admin_orders_page"] = 0
    await show_orders(update, context)


async def order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("admin_order_", ""))

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)

    if not order:
        await query.edit_message_text("Заказ не найден.")
        return

    user = order.user
    items_text = "\n".join(
        f"• {i.product_name} × {i.quantity} = {fmt_price(float(i.price) * i.quantity)}"
        for i in order.items
    )
    payment_text = ""
    if order.payment_method == "usdt":
        payment_text = f"\n💳 Адрес: `{order.payment_address}`"
        if order.payment_txid:
            payment_text += f"\n🔗 TXID: `{order.payment_txid}`"

    pickup_text = ""
    if order.pickup_point:
        pickup_text = f"\n📍 Точка: {order.pickup_point.name}\n🔑 Код: {order.pickup_code}"

    text = (
        f"📋 *Заказ #{order.id}*\n\n"
        f"👤 @{user.username or '—'} (ID: {user.telegram_id})\n"
        f"📱 Телефон: {order.phone}\n"
        f"🚚 Получение: {'Самовывоз' if order.delivery_type == 'pickup' else 'Доставка'}"
        f"{pickup_text}\n\n"
        f"📦 Состав:\n{items_text}\n\n"
        f"💰 Итого: {fmt_price(order.total_price)}"
        + (f" ({fmt_usdt(order.total_price_usdt)})" if order.total_price_usdt else "")
        + f"\n💳 Оплата: {'USDT TRC20' if order.payment_method == 'usdt' else 'Наличные'}"
        f"\nСтатус: {fmt_status(order.status)}"
        f"{payment_text}"
        f"\n⏰ Создан: {fmt_dt(order.created_at)}"
    )

    await query.edit_message_text(text, reply_markup=order_actions_keyboard(order), parse_mode="Markdown")


async def set_order_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("admin_ready_", ""))
    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)
        await update_order_status(session, order_id, "ready")
    try:
        await context.bot.send_message(
            order.user.telegram_id,
            f"📦 Ваш заказ #{order_id} готов к выдаче!\n🔑 Код: {order.pickup_code}"
        )
    except Exception:
        pass
    await query.edit_message_text(f"✅ Заказ #{order_id} переведён в статус 'Готов к выдаче'.")


async def set_order_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("admin_complete_", ""))
    async with AsyncSessionLocal() as session:
        await update_order_status(session, order_id, "completed")
    await query.edit_message_text(f"✔️ Заказ #{order_id} выдан.")


async def cancel_order_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("admin_cancel_", ""))
    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)
        await update_order_status(session, order_id, "cancelled")
    try:
        await context.bot.send_message(
            order.user.telegram_id,
            f"❌ Ваш заказ #{order_id} отменён администратором."
        )
    except Exception:
        pass
    await query.edit_message_text(f"❌ Заказ #{order_id} отменён.")


def register(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📋 Заказы$"), show_orders))
    app.add_handler(CallbackQueryHandler(filter_orders, pattern=r"^admin_orders_filter_"))
    app.add_handler(CallbackQueryHandler(show_orders, pattern="^admin_orders_back$"))
    app.add_handler(CallbackQueryHandler(order_detail, pattern=r"^admin_order_\d+$"))
    app.add_handler(CallbackQueryHandler(set_order_ready, pattern=r"^admin_ready_\d+$"))
    app.add_handler(CallbackQueryHandler(set_order_complete, pattern=r"^admin_complete_\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_order_admin, pattern=r"^admin_cancel_\d+$"))
