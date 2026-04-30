from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from database.database import AsyncSessionLocal
from database.crud import get_user_by_telegram_id, get_user_orders, count_user_orders, get_order, update_order_status
from keyboards.user import orders_filter_keyboard, order_detail_keyboard
from utils.formatters import fmt_price, fmt_usdt, fmt_status, fmt_dt
import config


async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("orders_filter", "all")
    status_filter = context.user_data.get("orders_filter", "all")
    page = context.user_data.get("orders_page", 0)

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if not user:
            await update.effective_message.reply_text("❌ Пользователь не найден.")
            return
        sf = None if status_filter == "all" else status_filter
        total = await count_user_orders(session, user.id, sf)
        orders = await get_user_orders(session, user.id, sf, page * config.ORDERS_PER_PAGE, config.ORDERS_PER_PAGE)

    if not orders:
        text = "📦 У вас пока нет заказов."
        kb = orders_filter_keyboard(status_filter)
    else:
        lines = []
        for o in orders:
            lines.append(
                f"#{o.id} | {fmt_status(o.status)} | {fmt_price(o.total_price)} | {fmt_dt(o.created_at)}"
            )
        text = f"📦 *Мои заказы* ({total}):\n\n" + "\n".join(lines)
        kb = orders_filter_keyboard(status_filter)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def filter_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    status_filter = query.data.replace("orders_filter_", "")
    context.user_data["orders_filter"] = status_filter
    context.user_data["orders_page"] = 0
    await show_my_orders(update, context)


async def show_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("my_order_", ""))

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)

    if not order:
        await query.edit_message_text("Заказ не найден.")
        return

    items_text = "\n".join(
        f"• {item.product_name} × {item.quantity} = {fmt_price(float(item.price) * item.quantity)}"
        for item in order.items
    )
    usdt_text = f"\n💎 USDT: {fmt_usdt(order.total_price_usdt)}" if order.total_price_usdt else ""
    pickup_text = ""
    if order.pickup_point:
        pickup_text = f"\n📍 Точка: {order.pickup_point.name}\n🔑 Код: {order.pickup_code}"

    text = (
        f"📦 *Заказ #{order.id}*\n\n"
        f"Статус: {fmt_status(order.status)}\n"
        f"Дата: {fmt_dt(order.created_at)}\n\n"
        f"*Состав:*\n{items_text}\n\n"
        f"💰 Итого: {fmt_price(order.total_price)}{usdt_text}"
        f"\n\nСпособ получения: {'Самовывоз' if order.delivery_type == 'pickup' else 'Доставка'}"
        f"{pickup_text}"
    )

    kb = order_detail_keyboard(order)
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


async def cancel_own_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("cancel_order_", ""))

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)
        if order and order.status in ("new", "awaiting_payment"):
            await update_order_status(session, order_id, "cancelled")
            await query.edit_message_text(f"❌ Заказ #{order_id} отменён.")
        else:
            await query.edit_message_text("Невозможно отменить этот заказ.")


def register(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📦 Мои заказы$"), show_my_orders))
    app.add_handler(CallbackQueryHandler(filter_orders, pattern=r"^orders_filter_"))
    app.add_handler(CallbackQueryHandler(show_order_detail, pattern=r"^my_order_\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_own_order, pattern=r"^cancel_order_\d+$"))
