from telegram import Update
from telegram.ext import (
    ContextTypes, MessageHandler, CallbackQueryHandler,
    ConversationHandler, CommandHandler, filters
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_all_categories, get_category, create_category,
    update_category, delete_category
)
from keyboards.admin import categories_list_keyboard, category_actions_keyboard
from utils.decorators import admin_required

ADD_NAME, ADD_EMOJI, ADD_DESC = range(3)


@admin_required
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        cats = await get_all_categories(session)
    text = f"📁 *Категории* ({len(cats)}):"
    kb = categories_list_keyboard(cats)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def category_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.replace("admin_cat_", ""))
    async with AsyncSessionLocal() as session:
        cat = await get_category(session, cat_id)
    if not cat:
        await query.edit_message_text("Категория не найдена.")
        return
    text = (
        f"📁 *{cat.emoji} {cat.name}*\n\n"
        f"Описание: {cat.description or '—'}\n"
        f"Статус: {'✅ Активна' if cat.is_active else '❌ Неактивна'}"
    )
    await query.edit_message_text(text, reply_markup=category_actions_keyboard(cat), parse_mode="Markdown")


async def toggle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.replace("admin_cat_toggle_", ""))
    async with AsyncSessionLocal() as session:
        cat = await get_category(session, cat_id)
        await update_category(session, cat_id, is_active=not cat.is_active)
        cat = await get_category(session, cat_id)
    await query.edit_message_reply_markup(reply_markup=category_actions_keyboard(cat))


async def delete_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.replace("admin_cat_delete_", ""))
    async with AsyncSessionLocal() as session:
        await delete_category(session, cat_id)
    await query.edit_message_text("🗑 Категория удалена.")


async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите название новой категории:")
    return ADD_NAME


async def add_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_cat"] = {"name": update.message.text.strip()}
    await update.message.reply_text("Введите эмодзи для категории (например 📦) или /skip:")
    return ADD_EMOJI


async def add_category_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "/skip":
        context.user_data["new_cat"]["emoji"] = update.message.text.strip()
    await update.message.reply_text("Введите описание категории или /skip:")
    return ADD_DESC


async def add_category_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "/skip":
        context.user_data["new_cat"]["description"] = update.message.text.strip()
    data = context.user_data.pop("new_cat", {})
    async with AsyncSessionLocal() as session:
        cat = await create_category(session, **data)
    await update.message.reply_text(f"✅ Категория '{cat.emoji} {cat.name}' добавлена!")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_category_start, pattern="^admin_add_category$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_name)],
            ADD_EMOJI: [
                CommandHandler("skip", add_category_emoji),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_emoji),
            ],
            ADD_DESC: [
                CommandHandler("skip", add_category_desc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_desc),
            ],
        },
        fallbacks=[],
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📁 Категории$"), show_categories))
    app.add_handler(CallbackQueryHandler(show_categories, pattern="^admin_categories$"))
    app.add_handler(CallbackQueryHandler(category_detail, pattern=r"^admin_cat_\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_category, pattern=r"^admin_cat_toggle_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_category_handler, pattern=r"^admin_cat_delete_\d+$"))
