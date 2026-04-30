from telegram import Update
from telegram.ext import (
    ContextTypes, MessageHandler, CallbackQueryHandler,
    ConversationHandler, CommandHandler, filters
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_all_products, get_product, update_product, delete_product,
    get_all_categories, create_product
)
from keyboards.admin import products_list_keyboard, product_actions_keyboard, back_to_admin_keyboard
from utils.decorators import admin_required

ADD_NAME, ADD_CATEGORY, ADD_PRICE, ADD_DESC, ADD_PHOTO, ADD_STOCK = range(6)
EDIT_PRICE, EDIT_STOCK = range(2)


@admin_required
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        products = await get_all_products(session)
    text = f"📦 *Товары* ({len(products)}):"
    kb = products_list_keyboard(products)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("admin_prod_", ""))
    async with AsyncSessionLocal() as session:
        p = await get_product(session, product_id)
    if not p:
        await query.edit_message_text("Товар не найден.")
        return
    text = (
        f"📦 *{p.name}*\n\n"
        f"Цена: {float(p.price):,.0f} ₽\n"
        f"Остаток: {p.stock_quantity} шт.\n"
        f"Доступен: {'✅' if p.is_available else '❌'}\n"
        f"Описание: {p.description or '—'}"
    )
    await query.edit_message_text(text, reply_markup=product_actions_keyboard(p), parse_mode="Markdown")


async def toggle_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("admin_prod_toggle_", ""))
    async with AsyncSessionLocal() as session:
        p = await get_product(session, product_id)
        await update_product(session, product_id, is_available=not p.is_available)
        p = await get_product(session, product_id)
    await query.edit_message_reply_markup(reply_markup=product_actions_keyboard(p))


async def delete_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("admin_prod_delete_", ""))
    async with AsyncSessionLocal() as session:
        await delete_product(session, product_id)
    await query.edit_message_text("🗑 Товар удалён.")


async def edit_price_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("admin_prod_price_", ""))
    context.user_data["editing_product_id"] = product_id
    await query.edit_message_text("Введите новую цену (число):")
    return EDIT_PRICE


async def edit_price_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите число:")
        return EDIT_PRICE
    product_id = context.user_data.pop("editing_product_id", None)
    async with AsyncSessionLocal() as session:
        await update_product(session, product_id, price=price)
    await update.message.reply_text(f"✅ Цена обновлена: {price:,.0f} ₽")
    return ConversationHandler.END


async def edit_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("admin_prod_stock_", ""))
    context.user_data["editing_product_id"] = product_id
    await query.edit_message_text("Введите новый остаток (число):")
    return EDIT_STOCK


async def edit_stock_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stock = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите целое число:")
        return EDIT_STOCK
    product_id = context.user_data.pop("editing_product_id", None)
    async with AsyncSessionLocal() as session:
        await update_product(session, product_id, stock_quantity=stock)
    await update.message.reply_text(f"✅ Остаток обновлён: {stock} шт.")
    return ConversationHandler.END


async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите название нового товара:")
    return ADD_NAME


async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"] = {"name": update.message.text.strip()}
    async with AsyncSessionLocal() as session:
        cats = await get_all_categories(session)
    from keyboards.admin import categories_list_keyboard
    buttons_text = "\n".join(f"{i + 1}. {c.emoji} {c.name} (ID: {c.id})" for i, c in enumerate(cats))
    context.user_data["_cats"] = {c.id: c for c in cats}
    await update.message.reply_text(f"Выберите категорию (введите ID):\n{buttons_text}")
    return ADD_CATEGORY


async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cat_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введите числовой ID категории:")
        return ADD_CATEGORY
    context.user_data["new_product"]["category_id"] = cat_id
    await update.message.reply_text("Введите цену (число):")
    return ADD_PRICE


async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введите число:")
        return ADD_PRICE
    context.user_data["new_product"]["price"] = price
    await update.message.reply_text("Введите описание или /skip:")
    return ADD_DESC


async def add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "/skip":
        context.user_data["new_product"]["description"] = update.message.text.strip()
    await update.message.reply_text("Отправьте URL фото или /skip:")
    return ADD_PHOTO


async def add_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "/skip":
        context.user_data["new_product"]["photo_url"] = update.message.text.strip()
    await update.message.reply_text("Введите остаток (количество):")
    return ADD_STOCK


async def add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stock = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введите целое число:")
        return ADD_STOCK
    data = context.user_data.pop("new_product", {})
    data["stock_quantity"] = stock
    async with AsyncSessionLocal() as session:
        p = await create_product(session, **data)
    await update.message.reply_text(f"✅ Товар '{p.name}' добавлен!")
    return ConversationHandler.END


def register(app):
    edit_price_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_price_start, pattern=r"^admin_prod_price_\d+$")],
        states={EDIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_price_done)]},
        fallbacks=[],
    )
    edit_stock_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_stock_start, pattern=r"^admin_prod_stock_\d+$")],
        states={EDIT_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_stock_done)]},
        fallbacks=[],
    )
    add_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_product_start, pattern="^admin_add_product$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_name)],
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_category)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_price)],
            ADD_DESC: [
                CommandHandler("skip", add_product_desc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_desc),
            ],
            ADD_PHOTO: [
                CommandHandler("skip", add_product_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_photo),
            ],
            ADD_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_stock)],
        },
        fallbacks=[],
    )
    app.add_handler(edit_price_conv)
    app.add_handler(edit_stock_conv)
    app.add_handler(add_product_conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📦 Товары$"), show_products))
    app.add_handler(CallbackQueryHandler(show_products, pattern="^admin_products$"))
    app.add_handler(CallbackQueryHandler(product_detail, pattern=r"^admin_prod_\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_product, pattern=r"^admin_prod_toggle_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_product_handler, pattern=r"^admin_prod_delete_\d+$"))
