from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_all_categories, get_category, create_category,
    toggle_category, delete_category,
)
from keyboards.admin import categories_list_keyboard, category_actions_keyboard
from utils.decorators import admin_required

ADD_NAME, ADD_EMOJI, ADD_DESCRIPTION = range(3)


@admin_required
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        categories = await get_all_categories(session)
    text = f"📂 *Категории* ({len(categories)}):"
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=categories_list_keyboard(categories))
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=categories_list_keyboard(categories))


@admin_required
async def show_category_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        cat = await get_category(session, cat_id)
    if not cat:
        await query.edit_message_text("❌ Категория не найдена.")
        return
    emoji = cat.emoji or ""
    text = (
        f"📂 *{emoji} {cat.name}*\n\n"
        f"Описание: {cat.description or '—'}\n"
        f"Статус: {'✅ Активна' if cat.is_active else '❌ Неактивна'}"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=category_actions_keyboard(cat.id, cat.is_active))


@admin_required
async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📂 *Новая категория*\n\nВведите название категории:",
        parse_mode="Markdown",
    )
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_cat_name"] = update.message.text.strip()
    await update.message.reply_text("Введите emoji категории или /skip:")
    return ADD_EMOJI


async def add_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "/skip":
        context.user_data["new_cat_emoji"] = None
    else:
        context.user_data["new_cat_emoji"] = update.message.text.strip()
    await update.message.reply_text("Введите описание категории или /skip:")
    return ADD_DESCRIPTION


async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "/skip":
        description = None
    else:
        description = update.message.text.strip()

    name = context.user_data.pop("new_cat_name", "")
    emoji = context.user_data.pop("new_cat_emoji", None)

    async with AsyncSessionLocal() as session:
        cat = await create_category(session, name, emoji, description)

    await update.message.reply_text(
        f"✅ Категория *{emoji or ''} {cat.name}* создана!",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


@admin_required
async def toggle_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        cat = await toggle_category(session, cat_id)
    if cat:
        status = "активирована" if cat.is_active else "деактивирована"
        await query.edit_message_text(
            f"✅ Категория {status}.",
            reply_markup=category_actions_keyboard(cat.id, cat.is_active),
        )


@admin_required
async def delete_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        await delete_category(session, cat_id)
    await query.edit_message_text("🗑 Категория удалена.")


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_category_start, pattern="^admin_add_category$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_EMOJI: [
                CommandHandler("skip", add_emoji),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_emoji),
            ],
            ADD_DESCRIPTION: [
                CommandHandler("skip", add_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_description),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
        per_chat=True,
        per_user=True,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📂 Категории$"), show_categories))
    app.add_handler(CallbackQueryHandler(show_categories, pattern="^admin_categories$"))
    app.add_handler(CallbackQueryHandler(show_category_detail, pattern=r"^admin_category:\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_cat, pattern=r"^admin_toggle_category:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_cat, pattern=r"^admin_delete_category:\d+$"))
