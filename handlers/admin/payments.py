import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from database.database import AsyncSessionLocal
from database.crud import get_order, confirm_payment, cancel_order, get_all_admins
from keyboards.admin import payments_list_keyboard
from utils.decorators import admin_required
from utils.formatters import fmt_price, fmt_dt
import config

logger = logging.getLogger(__name__)

WAITING_TXID = 0


@admin_required
async def show_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.crud import get_awaiting_payment_orders
    async with AsyncSessionLocal() as session:
        orders = await get_awaiting_payment_orders(session)

    text = f"💰 *Ожидают подтверждения* ({len(orders)}):"
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=payments_list_keyboard(orders),
    )


@admin_required
async def show_payment_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)

    if not order:
        await query.edit_message_text("❌ Заказ не найден.")
        return

    from keyboards.admin import payment_actions_keyboard
    text = (
        f"💰 *Платёж #{order.id}*\n\n"
        f"👤 @{order.user.username or '—'} (ID: {order.user.telegram_id})\n"
        f"💎 {float(order.total_price_usdt):.2f} USDT\n"
        f"💰 {fmt_price(order.total_price)}\n"
        f"📥 Адрес: `{order.payment_address}`\n"
        f"🕐 Создан: {fmt_dt(order.created_at)}"
    )
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=payment_actions_keyboard(order.id, order.payment_address),
    )


@admin_required
async def confirm_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])
    context.user_data["confirming_order_id"] = order_id

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            f"✅ *Подтверждение оплаты заказа #{order_id}*\n\n"
            f"Введите TXID транзакции или отправьте /skip:"
        ),
        parse_mode="Markdown",
    )
    return WAITING_TXID


async def receive_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("confirming_order_id")
    if not order_id:
        await update.message.reply_text("❌ Ошибка. Начните заново.")
        return ConversationHandler.END

    txid = None if update.message.text.strip() == "/skip" else update.message.text.strip()
    admin_telegram_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        order = await confirm_payment(session, order_id, admin_telegram_id, txid)

    if not order:
        await update.message.reply_text("❌ Заказ не найден или уже подтверждён.")
        return ConversationHandler.END

    await update.message.reply_text(f"✅ Заказ #{order_id} подтверждён!")

    pickup_info = ""
    map_text = ""
    if order.pickup_point:
        pp = order.pickup_point
        pickup_info = (
            f"\n📍 *ТОЧКА ВЫДАЧИ:*\n"
            f"{pp.name}\n"
            f"📍 {pp.address}\n"
            f"🕐 Режим работы: {pp.working_hours}\n"
        )
        map_text = f"\n🗺 [Показать на карте](https://maps.google.com/?q={pp.latitude},{pp.longitude})"

    client_text = (
        f"✅ *ВАША ОПЛАТА ПОДТВЕРЖДЕНА!*\n\n"
        f"📦 Заказ #{order_id} оплачен\n"
        f"📦 Код получения: *{order.pickup_code}*"
        + pickup_info
        + map_text
    )

    try:
        await context.bot.send_message(
            order.user.telegram_id,
            client_text,
            parse_mode="Markdown",
        )
        if order.pickup_point:
            await context.bot.send_location(
                order.user.telegram_id,
                latitude=float(order.pickup_point.latitude),
                longitude=float(order.pickup_point.longitude),
            )
    except Exception as e:
        logger.error(f"Failed to notify client: {e}")

    async with AsyncSessionLocal() as session:
        admins = await get_all_admins(session)

    admin_ids = set(config.ADMIN_IDS)
    for adm in admins:
        admin_ids.add(adm.telegram_id)

    notify_text = f"✅ Заказ #{order_id} подтверждён администратором @{update.effective_user.username or '—'}"
    for aid in admin_ids:
        if aid != admin_telegram_id:
            try:
                await context.bot.send_message(aid, notify_text)
            except Exception:
                pass

    return ConversationHandler.END


@admin_required
async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        order = await cancel_order(session, order_id)

    if not order:
        await query.edit_message_text("❌ Заказ не найден.")
        return

    await query.edit_message_text(f"❌ Заказ #{order_id} отклонён.")

    try:
        await context.bot.send_message(
            order.user.telegram_id,
            f"❌ *Ваш платёж по заказу #{order_id} отклонён.*\n\n"
            f"Пожалуйста, свяжитесь с администратором или оформите новый заказ.",
            parse_mode="Markdown",
        )
    except Exception:
        pass


async def cancel_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Подтверждение отменено.")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(confirm_payment_start, pattern=r"^confirm_payment:\d+$")
        ],
        states={
            WAITING_TXID: [
                CommandHandler("skip", receive_txid),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_txid),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_confirm)],
        per_chat=True,
        per_user=True,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💰 Платежи$"), show_payments))
    app.add_handler(CallbackQueryHandler(show_payment_detail, pattern=r"^admin_payment:\d+$"))
    app.add_handler(CallbackQueryHandler(reject_payment, pattern=r"^reject_payment:\d+$"))
