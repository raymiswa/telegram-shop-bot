from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_all_products, get_product, create_product,
    toggle_product, delete_product, get_all_categories,
)
from keyboards.admin import products_list_keyboard, product_actions_keyboard, categories_list_keyboard
from utils.decorators import admin_required

SELECT_CATEGORY, ADD_NAME, ADD_DESCRIPTION, ADD_PRICE, ADD_PHOTO, ADD_STOCK = range(6)


@admin_required
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        products = await get_all_products(session)
    text = f"🛒 *Товары* ({len(products)}):"
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=products_list_keyboard(products))
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=products_list_keyboard(products))


@admin_required
async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        product = await get_product(session, product_id)
    if not product:
        await query.edit_message_text("❌ Товар не найден.")
        return
    text = (
        f"🛒 *{product.name}*\n\n"
        f"Описание: {product.description or '—'}\n"
        f"Цена: *{float(product.price):.0f}₽*\n"
        f"Склад: {product.stock_quantity} шт.\n"
        f"Статус: {'✅ Доступен' if product.is_available else '❌ Скрыт'}"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=product_actions_keyboard(product.id, product.is_available),
    )


@admin_required
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    async with AsyncSessionLocal() as session:
        categories = await get_all_categories(session)
    if not categories:
        await context.bot.send_message(
            query.message.chat_id,
            "❌ Сначала создайте категорию!",
        )
        return ConversationHandler.END
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🛒 *Новый товар*\n\nВыберите категорию:",
        parse_mode="Markdown",
        reply_markup=categories_list_keyboard(categories),
    )
    return SELECT_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split(":")[1])
    context.user_data["new_prod_cat_id"] = cat_id
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Введите название товара:",
    )
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_name"] = update.message.text.strip()
    await update.message.reply_text("Введите описание товара или /skip:")
    return ADD_DESCRIPTION


async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "/skip":
        context.user_data["new_prod_desc"] = None
    else:
        context.user_data["new_prod_desc"] = update.message.text.strip()
    await update.message.reply_text("Введите цену товара (в рублях, только число):")
    return ADD_PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Неверная цена. Введите число (например: 999.90):")
        return ADD_PRICE
    context.user_data["new_prod_price"] = price
    await update.message.reply_text("Отправьте фото товара или /skip:")
    return ADD_PHOTO


async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.strip() == "/skip":
        context.user_data["new_prod_photo"] = None
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data["new_prod_photo"] = file_id
    else:
        context.user_data["new_prod_photo"] = None
    await update.message.reply_text("Введите количество на складе (целое число):")
    return ADD_STOCK


async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stock = int(update.message.text.strip())
        if stock < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Неверное количество. Введите целое число:")
        return ADD_STOCK

    cat_id = context.user_data.pop("new_prod_cat_id", None)
    name = context.user_data.pop("new_prod_name", "")
    desc = context.user_data.pop("new_prod_desc", None)
    price = context.user_data.pop("new_prod_price", 0.0)
    photo = context.user_data.pop("new_prod_photo", None)

    async with AsyncSessionLocal() as session:
        product = await create_product(session, cat_id, name, desc, price, photo, stock)

    await update.message.reply_text(
        f"✅ Товар *{product.name}* создан!\n"
        f"Цена: {float(product.price):.0f}₽, Склад: {product.stock_quantity} шт.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


@admin_required
async def toggle_prod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        product = await toggle_product(session, product_id)
    if product:
        status = "доступен" if product.is_available else "скрыт"
        await query.edit_message_text(
            f"✅ Товар {status}.",
            reply_markup=product_actions_keyboard(product.id, product.is_available),
        )


@admin_required
async def delete_prod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        await delete_product(session, product_id)
    await query.edit_message_text("🗑 Товар удалён.")


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_product_start, pattern="^admin_add_product$")],
        states={
            SELECT_CATEGORY: [CallbackQueryHandler(select_category, pattern=r"^cat:\d+$")],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_DESCRIPTION: [
                CommandHandler("skip", add_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_description),
            ],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
            ADD_PHOTO: [
                CommandHandler("skip", add_photo),
                MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), add_photo),
            ],
            ADD_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_stock)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
        per_chat=True,
        per_user=True,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🛒 Товары$"), show_products))
    app.add_handler(CallbackQueryHandler(show_products, pattern="^admin_products$"))
    app.add_handler(CallbackQueryHandler(show_product_detail, pattern=r"^admin_product:\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_prod, pattern=r"^admin_toggle_product:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_prod, pattern=r"^admin_delete_product:\d+$"))
