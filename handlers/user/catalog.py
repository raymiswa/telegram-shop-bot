from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from database.database import AsyncSessionLocal
from database.crud import (
    get_active_categories, get_products_by_category,
    count_products_by_category, get_product, get_category
)
from keyboards.user import categories_keyboard, products_keyboard, product_keyboard
import config


async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        categories = await get_active_categories(session)
    if not categories:
        await update.effective_message.reply_text("😔 Каталог пока пуст.")
        return
    text = "🛍 *Каталог товаров*\n\nВыберите категорию:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=categories_keyboard(categories), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=categories_keyboard(categories), parse_mode="Markdown")


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if "_page_" in data:
        parts = data.split("_page_")
        category_id = int(parts[0].replace("cat_", ""))
        page = int(parts[1])
    else:
        category_id = int(data.replace("cat_", ""))
        page = 0

    async with AsyncSessionLocal() as session:
        cat = await get_category(session, category_id)
        total = await count_products_by_category(session, category_id)
        products = await get_products_by_category(
            session, category_id,
            offset=page * config.PRODUCTS_PER_PAGE,
            limit=config.PRODUCTS_PER_PAGE
        )

    if not products:
        await query.edit_message_text("😔 Товары в этой категории недоступны.",
                                      reply_markup=categories_keyboard([]))
        return

    text = f"📦 *{cat.emoji} {cat.name}*\n\nСтраница {page + 1}/{max(1, -(-total // config.PRODUCTS_PER_PAGE))}"
    await query.edit_message_text(
        text,
        reply_markup=products_keyboard(products, category_id, page, total, config.PRODUCTS_PER_PAGE),
        parse_mode="Markdown",
    )


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("prod_", ""))
    context.user_data[f"qty_{product_id}"] = context.user_data.get(f"qty_{product_id}", 1)

    async with AsyncSessionLocal() as session:
        p = await get_product(session, product_id)

    if not p:
        await query.edit_message_text("Товар не найден.")
        return

    qty = context.user_data.get(f"qty_{product_id}", 1)
    stock_text = f"В наличии: {p.stock_quantity} шт." if p.stock_quantity else "Нет в наличии"
    text = (
        f"*{p.name}*\n\n"
        f"{p.description or ''}\n\n"
        f"💰 Цена: {float(p.price):,.0f} ₽\n"
        f"📦 {stock_text}"
    )

    if p.photo_url:
        try:
            await query.message.reply_photo(
                photo=p.photo_url,
                caption=text,
                reply_markup=product_keyboard(product_id, qty),
                parse_mode="Markdown",
            )
            await query.message.delete()
            return
        except Exception:
            pass

    await query.edit_message_text(text, reply_markup=product_keyboard(product_id, qty), parse_mode="Markdown")


async def handle_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("qty_inc_"):
        product_id = int(data.replace("qty_inc_", ""))
        qty = context.user_data.get(f"qty_{product_id}", 1) + 1
    elif data.startswith("qty_dec_"):
        product_id = int(data.replace("qty_dec_", ""))
        qty = max(1, context.user_data.get(f"qty_{product_id}", 1) - 1)
    else:
        return

    context.user_data[f"qty_{product_id}"] = qty

    async with AsyncSessionLocal() as session:
        p = await get_product(session, product_id)

    if p and p.stock_quantity and qty > p.stock_quantity:
        qty = p.stock_quantity
        context.user_data[f"qty_{product_id}"] = qty

    await query.edit_message_reply_markup(reply_markup=product_keyboard(product_id, qty))


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Добавлено в корзину!")
    parts = query.data.replace("add_cart_", "").split("_")
    product_id = int(parts[0])
    qty = int(parts[1])

    cart = context.user_data.setdefault("cart", {})
    cart[product_id] = cart.get(product_id, 0) + qty
    context.user_data[f"qty_{product_id}"] = 1

    from keyboards.user import main_menu_keyboard
    cart_count = sum(cart.values())
    await query.message.reply_text(
        f"✅ Товар добавлен в корзину!\n🛒 Итого в корзине: {cart_count} шт.",
        reply_markup=main_menu_keyboard(cart_count),
    )


async def back_to_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("back_to_cat_", ""))
    async with AsyncSessionLocal() as session:
        p = await get_product(session, product_id)
        if p:
            cat = await get_category(session, p.category_id)
            total = await count_products_by_category(session, p.category_id)
            products = await get_products_by_category(session, p.category_id, limit=config.PRODUCTS_PER_PAGE)
    await query.edit_message_text(
        f"📦 *{cat.emoji} {cat.name}*",
        reply_markup=products_keyboard(products, p.category_id, 0, total, config.PRODUCTS_PER_PAGE),
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🛍 Каталог товаров$"), show_catalog))
    app.add_handler(CallbackQueryHandler(show_catalog, pattern="^catalog$"))
    app.add_handler(CallbackQueryHandler(show_category, pattern=r"^cat_\d+(_page_\d+)?$"))
    app.add_handler(CallbackQueryHandler(show_product, pattern=r"^prod_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_qty, pattern=r"^qty_(inc|dec)_\d+$"))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern=r"^add_cart_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(back_to_category, pattern=r"^back_to_cat_\d+$"))
