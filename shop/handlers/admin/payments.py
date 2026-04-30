from telegram import Update
from telegram.ext import (
    ContextTypes, MessageHandler, CallbackQueryHandler,
    ConversationHandler, CommandHandler, filters
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_awaiting_payment_orders, get_order, confirm_payment,
    update_order_status, get_all_admins
)
from keyboards.admin import payments_list_keyboard, payment_confirm_keyboard, back_to_admin_keyboard
from utils.decorators import admin_required
from utils.formatters import fmt_price, fmt_usdt, fmt_dt
import config

WAITING_TXID = 1


@admin_required
async def show_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        orders = await get_awaiting_payment_orders(session)

    if not orders:
        text = "💰 Нет ожидающих подтверждения платежей."
        kb = back_to_admin_keyboard()
    else:
        text = f"💰 *ОЖИДАЮТ ОПЛАТЫ*\n\nВсего: {len(orders)} заказов"
        kb = payments_list_keyboard(orders)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def payment_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("admin_payment_", ""))

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

    from datetime import datetime
    remaining = ""
    if order.created_at:
        elapsed = (datetime.utcnow() - order.created_at).total_seconds()
        left = max(0, config.PAYMENT_TIMEOUT_MINUTES * 60 - elapsed)
        mins = int(left // 60)
        secs = int(left % 60)
        remaining = f"\n⏱ Осталось: {mins:02d}:{secs:02d}"

    text = (
        f"💰 *ПЛАТЁЖ #{order.id}*\n\n"
        f"👤 Клиент: @{user.username or '—'} (ID: {user.telegram_id})\n"
        f"📱 Телефон: {order.phone}\n"
        f"💰 Сумма: {fmt_price(order.total_price)} ({fmt_usdt(order.total_price_usdt)})\n\n"
        f"📦 Состав:\n{items_text}\n\n"
        f"💳 Адрес кошелька:\n`{order.payment_address}`\n"
        f"⏰ Создан: {fmt_dt(order.created_at)}"
        f"{remaining}"
    )

    await query.edit_message_text(
        text,
        reply_markup=payment_confirm_keyboard(order.id),
        parse_mode="Markdown",
    )


async def confirm_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("admin_confirm_", ""))
    context.user_data["confirming_order_id"] = order_id
    await query.edit_message_text(
        f"💰 Подтверждение оплаты заказа #{order_id}\n\nВведите TXID транзакции или /skip:"
    )
    return WAITING_TXID


async def confirm_payment_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txid = None if update.message.text == "/skip" else update.message.text.strip()
    order_id = context.user_data.pop("confirming_order_id", None)
    if not order_id:
        await update.message.reply_text("Ошибка: заказ не найден.")
        return ConversationHandler.END

    async with AsyncSessionLocal() as session:
        order = await confirm_payment(session, order_id, update.effective_user.id, txid)
        admins = await get_all_admins(session)

    await update.message.reply_text(f"✅ Оплата заказа #{order_id} подтверждена!")

    # Notify client
    user = order.user
    pickup_text = ""
    if order.pickup_point:
        pickup_text = (
            f"\n\n📍 *ТОЧКА ВЫДАЧИ:*\n"
            f"{order.pickup_point.name}\n"
            f"{order.pickup_point.address}\n\n"
            f"⏰ Время работы:\n{order.pickup_point.working_hours or '—'}\n\n"
            f"🔑 *КОД ПОЛУЧЕНИЯ:*\n`{order.pickup_code}`\n\n"
            f"Инструкция: покажите этот код оператору в точке выдачи"
        )

    client_text = (
        f"✅ *ОПЛАТА ПРИНЯТА МАГАЗИНОМ!*\n\n"
        f"📦 Ваш заказ #{order.id} успешно оплачен"
        f"{pickup_text}"
    )

    try:
        await context.bot.send_message(user.telegram_id, client_text, parse_mode="Markdown")
        if order.pickup_point and order.pickup_point.latitude:
            await context.bot.send_location(
                user.telegram_id,
                latitude=float(order.pickup_point.latitude),
                longitude=float(order.pickup_point.longitude),
            )
    except Exception:
        pass

    # Notify other admins
    notify_text = f"✅ Оплата заказа #{order_id} подтверждена администратором @{update.effective_user.username or update.effective_user.id}"
    for admin in admins:
        if admin.telegram_id != update.effective_user.id:
            try:
                await context.bot.send_message(admin.telegram_id, notify_text)
            except Exception:
                pass

    return ConversationHandler.END


async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("admin_reject_", ""))

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)
        if order:
            await update_order_status(session, order_id, "cancelled")
            user = order.user

    try:
        await context.bot.send_message(
            user.telegram_id,
            f"❌ Ваш платёж по заказу #{order_id} не подтверждён. Заказ отменён.\nПо вопросам обращайтесь к администратору.",
        )
    except Exception:
        pass

    await query.edit_message_text(f"❌ Платёж по заказу #{order_id} отклонён.")


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(confirm_payment_start, pattern=r"^admin_confirm_\d+$")],
        states={
            WAITING_TXID: [
                CommandHandler("skip", confirm_payment_txid),
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_payment_txid),
            ],
        },
        fallbacks=[],
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💰 Платежи$"), show_payments))
    app.add_handler(CallbackQueryHandler(show_payments, pattern="^admin_payments$"))
    app.add_handler(CallbackQueryHandler(payment_detail, pattern=r"^admin_payment_\d+$"))
    app.add_handler(CallbackQueryHandler(reject_payment, pattern=r"^admin_reject_\d+$"))
