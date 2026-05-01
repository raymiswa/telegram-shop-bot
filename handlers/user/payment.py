import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_or_create_user, get_active_wallets, mark_wallet_used,
    create_order, get_order, cancel_order, get_all_admins,
)
from keyboards.user import payment_keyboard, payment_method_keyboard
from keyboards.admin import payment_actions_keyboard
from utils.validators import validate_phone, convert_to_usdt
from utils.qr_generator import generate_qr_code
import config

logger = logging.getLogger(__name__)

PHONE, COMMENT, PAYMENT_METHOD = range(3)


async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = context.user_data.get("cart", {})
    if not cart:
        await query.edit_message_text("🧺 Корзина пуста!")
        return ConversationHandler.END

    total = sum(item["price"] * item["qty"] for item in cart.values())
    context.user_data["checkout_total"] = total

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            f"📝 *Оформление заказа*\n\n"
            f"💰 Сумма: *{total:.0f}₽*\n\n"
            f"📞 Введите ваш номер телефона (формат: +79991234567):"
        ),
        parse_mode="Markdown",
    )
    return PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not validate_phone(phone):
        await update.message.reply_text(
            "❌ Неверный формат телефона.\n"
            "Введите в формате *+79991234567*:",
            parse_mode="Markdown",
        )
        return PHONE

    context.user_data["checkout_phone"] = phone
    await update.message.reply_text(
        "💬 Введите комментарий к заказу или отправьте /skip:"
    )
    return COMMENT


async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.strip() == "/skip":
        context.user_data["checkout_comment"] = None
    else:
        context.user_data["checkout_comment"] = update.message.text.strip()

    await update.message.reply_text(
        "💳 Выберите способ оплаты:",
        reply_markup=payment_method_keyboard(),
    )
    return PAYMENT_METHOD


async def receive_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split(":")[1]

    if method == "cancel_checkout":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ Оформление отменено.",
        )
        return ConversationHandler.END

    user = update.effective_user
    cart = context.user_data.get("cart", {})
    phone = context.user_data.get("checkout_phone", "")
    comment = context.user_data.get("checkout_comment")
    total = context.user_data.get("checkout_total", 0.0)

    async with AsyncSessionLocal() as session:
        db_user = await get_or_create_user(session, user.id, user.username, user.first_name or "")

        if method == "usdt_trc20":
            wallets = await get_active_wallets(session)
            if not wallets:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ USDT кошелёк не настроен. Выберите другой способ оплаты.",
                )
                return PAYMENT_METHOD

            wallet = wallets[0]
            total_usdt = convert_to_usdt(total, config.USDT_RATE)

            order = await create_order(
                session,
                user_id=db_user.id,
                cart=cart,
                phone=phone,
                comment=comment,
                payment_method="usdt_trc20",
                total_price=total,
                total_price_usdt=total_usdt,
                payment_address=wallet.address,
                pickup_point_id=None,
            )
            await mark_wallet_used(session, wallet.id)

        else:
            order = await create_order(
                session,
                user_id=db_user.id,
                cart=cart,
                phone=phone,
                comment=comment,
                payment_method="cash",
                total_price=total,
                total_price_usdt=None,
                payment_address=None,
                pickup_point_id=None,
            )

    context.user_data["cart"] = {}

    if method == "usdt_trc20":
        qr = generate_qr_code(order.payment_address)
        timeout_min = config.PAYMENT_TIMEOUT_MINUTES
        caption = (
            f"💎 *ОПЛАТА USDT TRC20*\n\n"
            f"📋 Заказ: *#{order.id}*\n"
            f"💰 Сумма: *{float(order.total_price_usdt):.2f} USDT*\n\n"
            f"📥 Адрес кошелька:\n`{order.payment_address}`\n\n"
            f"⏱ У вас *{timeout_min} минут* на оплату.\n\n"
            f"После перевода нажмите кнопку ниже:"
        )
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=qr,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=payment_keyboard(order.id),
        )
        context.job_queue.run_once(
            _payment_timeout_job,
            when=timeout_min * 60,
            data={"order_id": order.id, "chat_id": query.message.chat_id},
            name=f"payment_timeout_{order.id}",
        )
    else:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                f"✅ *Заказ #{order.id} создан!*\n\n"
                f"💵 Оплата наличными при получении.\n"
                f"💰 Сумма: *{total:.0f}₽*\n\n"
                f"📦 Код получения: *{order.pickup_code}*\n\n"
                f"Ожидайте подтверждения от администратора."
            ),
            parse_mode="Markdown",
        )
        await _notify_admins_new_order(context, order)

    return ConversationHandler.END


async def paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ Уведомляем администратора...")
    order_id = int(query.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)
        admins = await get_all_admins(session)

    if not order or order.status != "awaiting_payment":
        await query.edit_message_caption(
            caption="❌ Заказ не найден или уже обработан.",
        )
        return

    text = (
        f"💰 *Клиент заявил об оплате!*\n\n"
        f"📋 Заказ: *#{order.id}*\n"
        f"👤 @{order.user.username or '—'} (ID: {order.user.telegram_id})\n"
        f"💎 USDT: *{float(order.total_price_usdt):.2f}*\n"
        f"💰 RUB: *{float(order.total_price):.0f}₽*\n"
        f"📥 Адрес: `{order.payment_address}`"
    )
    keyboard = payment_actions_keyboard(order.id, order.payment_address)

    admin_ids = set(config.ADMIN_IDS)
    for admin in admins:
        admin_ids.add(admin.telegram_id)

    for admin_id in admin_ids:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            pass

    await query.edit_message_caption(
        caption=(
            f"✅ Администратор уведомлён!\n\n"
            f"Заказ #{order.id} ожидает подтверждения.\n"
            f"Мы сообщим вам о результате."
        )
    )


async def _payment_timeout_job(context):
    data = context.job.data
    order_id = data["order_id"]
    chat_id = data["chat_id"]

    async with AsyncSessionLocal() as session:
        order = await get_order(session, order_id)
        if order and order.status == "awaiting_payment":
            await cancel_order(session, order_id)
            try:
                await context.bot.send_message(
                    chat_id,
                    f"⏰ Время оплаты заказа *#{order_id}* истекло.\n"
                    f"Заказ отменён. Вы можете оформить новый.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass


async def _notify_admins_new_order(context, order):
    admin_ids = set(config.ADMIN_IDS)
    text = (
        f"🆕 *Новый заказ #{order.id}*\n\n"
        f"💵 Оплата наличными\n"
        f"💰 Сумма: *{float(order.total_price):.0f}₽*\n"
        f"📞 Телефон: {order.phone}"
    )
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception:
            pass


async def cancel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer("❌ Отменено")
        await context.bot.send_message(
            update.callback_query.message.chat_id,
            "❌ Оформление заказа отменено.",
        )
    elif update.message:
        await update.message.reply_text("❌ Оформление заказа отменено.")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^checkout$")],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
            COMMENT: [
                CommandHandler("skip", receive_comment),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment),
            ],
            PAYMENT_METHOD: [
                CallbackQueryHandler(cancel_checkout, pattern="^cancel_checkout$"),
                CallbackQueryHandler(receive_payment_method, pattern=r"^pay:(usdt_trc20|cash)$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_checkout)],
        per_chat=True,
        per_user=True,
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(paid_callback, pattern=r"^paid:\d+$"))
