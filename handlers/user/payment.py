import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, CommandHandler, filters
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, get_product, get_active_pickup_points,
    get_active_wallets, get_setting, create_order, get_order,
    update_order_status, mark_wallet_used, get_all_admins
)
from keyboards.user import (
    delivery_keyboard, pickup_points_keyboard, payment_keyboard,
    usdt_payment_keyboard, main_menu_keyboard, order_pickup_map_keyboard
)
from utils.validators import validate_phone, normalize_phone
from utils.payment_helpers import convert_to_usdt, generate_pickup_code
from utils.qr_generator import generate_qr_code
from utils.formatters import fmt_price, fmt_usdt, fmt_dt
import config

logger = logging.getLogger(__name__)

DELIVERY, PICKUP_POINT, PHONE, COMMENT, PAYMENT = range(5)


async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart: dict = context.user_data.get("cart", {})
    if not cart:
        await query.edit_message_text("🛒 Корзина пуста.")
        return ConversationHandler.END

    async with AsyncSessionLocal() as session:
        total = 0.0
        for pid, qty in cart.items():
            p = await get_product(session, int(pid))
            if p:
                total += float(p.price) * qty

    context.user_data["order_total"] = total
    await query.edit_message_text(
        f"✅ Оформление заказа\n\n💰 Сумма: {fmt_price(total)}\n\nВыберите способ получения:",
        reply_markup=delivery_keyboard(),
    )
    return DELIVERY


async def choose_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "order_cancel":
        await query.edit_message_text("❌ Оформление отменено.")
        return ConversationHandler.END

    delivery_type = "pickup" if query.data == "delivery_pickup" else "delivery"
    context.user_data["delivery_type"] = delivery_type

    if delivery_type == "pickup":
        async with AsyncSessionLocal() as session:
            points = await get_active_pickup_points(session)
        if not points:
            await query.edit_message_text("😔 Нет доступных точек выдачи.")
            return ConversationHandler.END
        await query.edit_message_text("📍 Выберите точку самовывоза:", reply_markup=pickup_points_keyboard(points))
        return PICKUP_POINT
    else:
        context.user_data["pickup_point_id"] = None
        await query.edit_message_text("📱 Введите номер телефона (+7XXXXXXXXXX):")
        return PHONE


async def choose_pickup_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "order_cancel":
        await query.edit_message_text("❌ Оформление отменено.")
        return ConversationHandler.END

    point_id = int(query.data.replace("pickup_point_", ""))
    context.user_data["pickup_point_id"] = point_id
    await query.edit_message_text("📱 Введите номер телефона (+7XXXXXXXXXX):")
    return PHONE


async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.text.strip())
    if not validate_phone(phone):
        await update.message.reply_text("❌ Неверный формат. Введите номер вида +7XXXXXXXXXX:")
        return PHONE
    context.user_data["order_phone"] = phone
    await update.message.reply_text(
        "💬 Введите комментарий к заказу или отправьте /skip:",
    )
    return COMMENT


async def enter_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "/skip":
        context.user_data["order_comment"] = None
    else:
        context.user_data["order_comment"] = update.message.text.strip()

    async with AsyncSessionLocal() as session:
        rate_str = await get_setting(session, "usdt_rate")
    rate = float(rate_str) if rate_str else config.USDT_RATE
    total = context.user_data["order_total"]
    usdt_amount = convert_to_usdt(total, rate)
    context.user_data["order_usdt_amount"] = usdt_amount

    await update.message.reply_text(
        f"💳 Выберите способ оплаты:\n\n"
        f"💰 Сумма: {fmt_price(total)}\n"
        f"💎 В USDT: {fmt_usdt(usdt_amount)}",
        reply_markup=payment_keyboard(),
    )
    return PAYMENT


async def choose_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "order_cancel":
        await query.edit_message_text("❌ Оформление отменено.")
        return ConversationHandler.END

    payment_method = "usdt" if query.data == "pay_usdt" else "cash"
    context.user_data["payment_method"] = payment_method

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        cart = context.user_data.get("cart", {})
        total = context.user_data["order_total"]
        usdt_amount = context.user_data.get("order_usdt_amount")
        phone = context.user_data.get("order_phone")
        comment = context.user_data.get("order_comment")
        delivery_type = context.user_data.get("delivery_type", "pickup")
        pickup_point_id = context.user_data.get("pickup_point_id")

        wallet_address = None
        if payment_method == "usdt":
            wallets = await get_active_wallets(session)
            if not wallets:
                await query.edit_message_text("❌ Нет доступных кошельков для оплаты. Обратитесь к администратору.")
                return ConversationHandler.END
            wallet = wallets[0]
            wallet_address = wallet.address
            await mark_wallet_used(session, wallet.id)

        order = await create_order(
            session,
            user_id=user.id,
            items=cart,
            total_price=total,
            total_price_usdt=usdt_amount if payment_method == "usdt" else None,
            delivery_type=delivery_type,
            pickup_point_id=pickup_point_id,
            phone=phone,
            comment=comment,
            payment_method=payment_method,
            payment_address=wallet_address,
        )

    context.user_data["cart"] = {}
    context.user_data["current_order_id"] = order.id

    if payment_method == "usdt":
        await _send_usdt_payment_info(query, context, order, wallet_address)
    else:
        await _send_cash_order_confirmation(query, context, order)
        await _notify_admins_new_order(context, order)

    return ConversationHandler.END


async def _send_usdt_payment_info(query, context, order, wallet_address: str):
    usdt_amount = float(order.total_price_usdt)
    qr = generate_qr_code(wallet_address)
    timeout_min = config.PAYMENT_TIMEOUT_MINUTES

    caption = (
        f"💎 *ОПЛАТА USDT TRC20*\n\n"
        f"Адрес кошелька:\n`{wallet_address}`\n\n"
        f"Сумма к оплате: *{usdt_amount:.2f} USDT*\n\n"
        f"⏱ Осталось времени: {timeout_min}:00\n\n"
        f"Инструкция:\n"
        f"1. Откройте ваш USDT кошелёк (TronLink, Trust Wallet и т.д.)\n"
        f"2. Отправьте ТОЧНУЮ сумму на указанный адрес\n"
        f"3. Используйте сеть TRC20 (Tron)\n"
        f"4. После оплаты нажмите \"Я оплатил\""
    )

    await query.message.reply_photo(
        photo=qr,
        caption=caption,
        reply_markup=usdt_payment_keyboard(order.id),
        parse_mode="Markdown",
    )
    await query.message.delete()

    context.job_queue.run_once(
        _payment_timeout_job,
        when=timeout_min * 60,
        data={"order_id": order.id, "chat_id": query.message.chat_id},
        name=f"payment_timeout_{order.id}",
    )


async def _send_cash_order_confirmation(query, context, order):
    text = (
        f"✅ *Заказ #{order.id} оформлен!*\n\n"
        f"💵 Оплата: наличными\n"
        f"💰 Сумма: {fmt_price(order.total_price)}\n\n"
        f"Ожидайте подтверждения от администратора."
    )
    await query.edit_message_text(text, parse_mode="Markdown")


async def _notify_admins_new_order(context, order):
    async with AsyncSessionLocal() as session:
        admins = await get_all_admins(session)
        user = order.user

    text = (
        f"🆕 *НОВЫЙ ЗАКАЗ #{order.id}*\n\n"
        f"👤 Клиент: @{user.username or '—'} (ID: {user.telegram_id})\n"
        f"📱 Телефон: {order.phone}\n"
        f"💰 Сумма: {fmt_price(order.total_price)}\n"
        f"💳 Оплата: {'USDT TRC20' if order.payment_method == 'usdt' else 'Наличные'}\n"
        f"⏰ Создан: {fmt_dt(order.created_at)}"
    )
    for admin in admins:
        try:
            await context.bot.send_message(admin.telegram_id, text, parse_mode="Markdown")
        except Exception:
            pass

    for admin_id in config.ADMIN_IDS:
        if not any(a.telegram_id == admin_id for a in admins):
            try:
                await context.bot.send_message(admin_id, text, parse_mode="Markdown")
            except Exception:
                pass


async def paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("paid_", ""))

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)
        admins = await get_all_admins(session)

    if not order or order.status != "awaiting_payment":
        await query.edit_message_caption("Заказ уже обработан или не найден.")
        return

    from keyboards.admin import payment_confirm_keyboard
    user = order.user
    text = (
        f"🔔 *ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ ОПЛАТЫ*\n\n"
        f"Заказ #{order.id}\n"
        f"Клиент: @{user.username or '—'} (ID: {user.telegram_id})\n"
        f"Телефон: {order.phone}\n"
        f"Сумма: {float(order.total_price_usdt):.2f} USDT\n"
        f"Кошелёк: {order.payment_address}\n"
        f"Время создания: {fmt_dt(order.created_at)}"
    )

    for admin in admins:
        try:
            await context.bot.send_message(
                admin.telegram_id, text,
                reply_markup=payment_confirm_keyboard(order.id),
                parse_mode="Markdown",
            )
        except Exception:
            pass

    for admin_id in config.ADMIN_IDS:
        if not any(a.telegram_id == admin_id for a in admins):
            try:
                await context.bot.send_message(
                    admin_id, text,
                    reply_markup=payment_confirm_keyboard(order.id),
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    await query.edit_message_caption(
        "✅ Уведомление отправлено администратору.\nОжидайте подтверждения оплаты.",
        parse_mode="Markdown",
    )


async def _payment_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    order_id = data["order_id"]
    chat_id = data["chat_id"]

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)
        if order and order.status == "awaiting_payment":
            await update_order_status(session, order_id, "cancelled")

    try:
        await context.bot.send_message(
            chat_id,
            f"⏰ Время оплаты заказа #{order_id} истекло. Заказ отменён.\n"
            f"Вы можете оформить новый заказ.",
        )
    except Exception:
        pass


async def show_order_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.replace("order_map_", ""))

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)

    if order and order.pickup_point and order.pickup_point.latitude:
        await context.bot.send_location(
            query.message.chat_id,
            latitude=float(order.pickup_point.latitude),
            longitude=float(order.pickup_point.longitude),
        )


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_checkout, pattern="^cart_checkout$")],
        states={
            DELIVERY: [CallbackQueryHandler(choose_delivery, pattern=r"^(delivery_pickup|delivery_courier|order_cancel)$")],
            PICKUP_POINT: [CallbackQueryHandler(choose_pickup_point, pattern=r"^(pickup_point_\d+|order_cancel)$")],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)],
            COMMENT: [
                CommandHandler("skip", enter_comment),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_comment),
            ],
            PAYMENT: [CallbackQueryHandler(choose_payment, pattern=r"^(pay_usdt|pay_cash|order_cancel)$")],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(paid_callback, pattern=r"^paid_\d+$"))
    app.add_handler(CallbackQueryHandler(show_order_map, pattern=r"^order_map_\d+$"))
