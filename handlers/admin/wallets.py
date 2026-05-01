from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_all_wallets, get_wallet, create_wallet,
    toggle_wallet, delete_wallet,
)
from keyboards.admin import wallets_list_keyboard, wallet_actions_keyboard
from utils.decorators import admin_required
from utils.validators import validate_trc20_address

ADD_ADDRESS = 0


@admin_required
async def show_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        wallets = await get_all_wallets(session)
    text = f"💎 *USDT кошельки* ({len(wallets)}):"
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=wallets_list_keyboard(wallets))
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=wallets_list_keyboard(wallets))


@admin_required
async def show_wallet_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wallet_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        wallet = await get_wallet(session, wallet_id)
    if not wallet:
        await query.edit_message_text("❌ Кошелёк не найден.")
        return
    text = (
        f"💎 *USDT TRC20 кошелёк*\n\n"
        f"Адрес:\n`{wallet.address}`\n\n"
        f"Статус: {'✅ Активен' if wallet.is_active else '❌ Неактивен'}\n"
        f"Добавлен: {wallet.created_at.strftime('%d.%m.%Y')}"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=wallet_actions_keyboard(wallet.id, wallet.is_active),
    )


@admin_required
async def add_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="💎 *Новый USDT кошелёк*\n\nВведите TRC20 адрес кошелька:",
        parse_mode="Markdown",
    )
    return ADD_ADDRESS


async def add_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    if not validate_trc20_address(address):
        await update.message.reply_text(
            "❌ Неверный TRC20 адрес.\n"
            "Адрес должен начинаться с T и содержать 34 символа.\n"
            "Попробуйте ещё раз:"
        )
        return ADD_ADDRESS

    async with AsyncSessionLocal() as session:
        try:
            wallet = await create_wallet(session, address)
        except Exception:
            await update.message.reply_text("❌ Этот адрес уже существует.")
            return ConversationHandler.END

    await update.message.reply_text(
        f"✅ Кошелёк добавлен!\n`{wallet.address}`",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


@admin_required
async def toggle_wal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wallet_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        wallet = await toggle_wallet(session, wallet_id)
    if wallet:
        status = "активирован" if wallet.is_active else "деактивирован"
        await query.edit_message_text(
            f"✅ Кошелёк {status}.",
            reply_markup=wallet_actions_keyboard(wallet.id, wallet.is_active),
        )


@admin_required
async def delete_wal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wallet_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        await delete_wallet(session, wallet_id)
    await query.edit_message_text("🗑 Кошелёк удалён.")


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_start, pattern="^admin_add_wallet$")],
        states={
            ADD_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_wallet_address)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
        per_chat=True,
        per_user=True,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💎 USDT кошельки$"), show_wallets))
    app.add_handler(CallbackQueryHandler(show_wallets, pattern="^admin_wallets$"))
    app.add_handler(CallbackQueryHandler(show_wallet_detail, pattern=r"^admin_wallet:\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_wal, pattern=r"^admin_toggle_wallet:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_wal, pattern=r"^admin_delete_wallet:\d+$"))
