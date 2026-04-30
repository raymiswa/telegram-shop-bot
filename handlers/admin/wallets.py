from telegram import Update
from telegram.ext import (
    ContextTypes, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_all_wallets, create_wallet, update_wallet, count_wallet_transactions
)
from keyboards.admin import wallets_list_keyboard, wallet_actions_keyboard
from utils.decorators import admin_required
from utils.payment_helpers import validate_trc20_address
from utils.formatters import fmt_dt

ADD_ADDRESS = 0


@admin_required
async def show_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        wallets = await get_all_wallets(session)

    if not wallets:
        text = "💳 Кошельков USDT нет."
    else:
        lines = []
        for w in wallets:
            status = "✅" if w.is_active else "❌"
            lines.append(f"{status} `{w.address}`\nПоследнее использование: {fmt_dt(w.last_used_at)}")
        text = "💳 *КОШЕЛЬКИ USDT TRC20*\n\n" + "\n\n".join(lines)

    kb = wallets_list_keyboard(wallets)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def wallet_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wallet_id = int(query.data.replace("admin_wallet_", ""))
    async with AsyncSessionLocal() as session:
        wallets = await get_all_wallets(session)
        wallet = next((w for w in wallets if w.id == wallet_id), None)
        if wallet:
            tx_count = await count_wallet_transactions(session, wallet.address)

    if not wallet:
        await query.edit_message_text("Кошелёк не найден.")
        return

    text = (
        f"💳 *Кошелёк USDT TRC20*\n\n"
        f"Адрес: `{wallet.address}`\n"
        f"Статус: {'✅ Активен' if wallet.is_active else '❌ Неактивен'}\n"
        f"Добавлен: {fmt_dt(wallet.created_at)}\n"
        f"Последнее использование: {fmt_dt(wallet.last_used_at)}\n"
        f"Транзакций: {tx_count}"
    )
    await query.edit_message_text(text, reply_markup=wallet_actions_keyboard(wallet), parse_mode="Markdown")


async def toggle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wallet_id = int(query.data.replace("admin_wallet_toggle_", ""))
    async with AsyncSessionLocal() as session:
        wallets = await get_all_wallets(session)
        wallet = next((w for w in wallets if w.id == wallet_id), None)
        if wallet:
            await update_wallet(session, wallet_id, is_active=not wallet.is_active)
            wallets = await get_all_wallets(session)
            wallet = next((w for w in wallets if w.id == wallet_id), None)
    await query.edit_message_reply_markup(reply_markup=wallet_actions_keyboard(wallet))


async def add_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите адрес USDT TRC20 кошелька (начинается с T, 34 символа):")
    return ADD_ADDRESS


async def add_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    if not validate_trc20_address(address):
        await update.message.reply_text("❌ Неверный адрес TRC20. Должен начинаться с 'T' и содержать 34 символа.\nПопробуйте снова:")
        return ADD_ADDRESS
    async with AsyncSessionLocal() as session:
        w = await create_wallet(session, address)
    await update.message.reply_text(f"✅ Кошелёк добавлен:\n`{w.address}`", parse_mode="Markdown")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_start, pattern="^admin_add_wallet$")],
        states={ADD_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_wallet_address)]},
        fallbacks=[],
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💳 Кошельки USDT$"), show_wallets))
    app.add_handler(CallbackQueryHandler(show_wallets, pattern="^admin_wallets$"))
    app.add_handler(CallbackQueryHandler(wallet_detail, pattern=r"^admin_wallet_\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_wallet, pattern=r"^admin_wallet_toggle_\d+$"))
