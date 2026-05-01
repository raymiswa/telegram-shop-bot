import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from database.database import AsyncSessionLocal
from database.crud import get_active_categories, get_products_by_category, get_product
from keyboards.user import categories_keyboard, products_keyboard, product_keyboard
import config

logger = logging.getLogger(__name__)


async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔥 show_catalog вызвана!")
    query = update.callback_query
    await query.answer()
    async with AsyncSessionLocal() as session:
        categories = await get_active_categories(session)
    logger.info(f"✅ Найдено категорий: {len(categories)}")
    if not categories:
        await query.edit_message_text("😔 Каталог пуст. Загляните позже!")
        return
    await query.edit_message_text(
        "📦 *Каталог товаров*\n\nВыберите категорию:",
        parse_mode="Markdown",
        reply_markup=categories_keyboard(categories),
    )
    logger.info("✅ show_catalog завершена успешно")


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"🔥🔥🔥 show_category ВЫЗВАНА! callback_data={query.data}")
    await query.answer()
    data = query.data  # cat:ID or cat:ID:p:PAGE

    parts = data.split(":")
    category_id = int(parts[1])
    page = int(parts[3]) if len(parts) >= 4 else 1

    logger.info(f"📦 Категория ID={category_id}, страница={page}")

    context.user_data["last_category_id"] = category_id
    context.user_data["last_page"] = page

    async with AsyncSessionLocal() as session:
        products, total, total_pages = await get_products_by_category(
            session, category_id, page, config.PRODUCTS_PER_PAGE
        )
    
    logger.info(f"✅✅✅ Найдено товаров: {len(products)}, всего: {total}, страниц: {total_pages}")
    
    if not products:
        logger.warning("⚠️ Товары не найдены!")
        await query.edit_message_text(
            "😔 В этой категории нет товаров.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К категориям", callback_data="catalog")]
            ]),
        )
        return
    
    text = f"🛍 *Товары* (стр. {page}/{total_pages}, всего {total}):"
    
    logger.info(f"📤 Отправляю сообщение с {len(products)} товарами")
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=products_keyboard(products, page, total_pages, category_id),
        )
        logger.info("✅✅✅ Сообщение отправлено УСПЕШНО!")
    except Exception as e:
        logger.error(f"❌❌❌ ОШИБКА отправки сообщения: {e}")
        raise


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔥 show_product вызвана!")
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[1])
    context.user_data["current_product_id"] = product_id
    context.user_data[f"qty_{product_id}"] = context.user_data.get(f"qty_{product_id}", 1)

    async with AsyncSessionLocal() as session:
        product = await get_product(session, product_id)

    if not product:
        await query.edit_message_text("❌ Товар не найден.")
        return

    qty = context.user_data.get(f"qty_{product_id}", 1)
    stock_text = f"📦 На складе: {product.stock_quantity} шт." if product.stock_quantity > 0 else "❌ Нет в наличии"
    text = (
        f"*{product.name}*\n\n"
        f"{product.description or ''}\n\n"
        f"💰 Цена: *{float(product.price):.0f}₽*\n"
        f"{stock_text}"
    )
    keyboard = product_keyboard(product_id, qty)

    if product.photo_url:
        try:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=product.photo_url,
                caption=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            logger.info("✅ show_product завершена (с фото)")
            return
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить фото: {e}")

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    logger.info("✅ show_product завершена (без фото)")


async def handle_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, product_id_str, action = query.data.split(":")
    product_id = int(product_id_str)

    current_qty = context.user_data.get(f"qty_{product_id}", 1)
    if action == "+" and current_qty < 99:
        current_qty += 1
    elif action == "-" and current_qty > 1:
        current_qty -= 1
    context.user_data[f"qty_{product_id}"] = current_qty

    async with AsyncSessionLocal() as session:
        product = await get_product(session, product_id)

    if not product:
        return

    stock_text = f"📦 На складе: {product.stock_quantity} шт." if product.stock_quantity > 0 else "❌ Нет в наличии"
    text = (
        f"*{product.name}*\n\n"
        f"{product.description or ''}\n\n"
        f"💰 Цена: *{float(product.price):.0f}₽*\n"
        f"{stock_text}"
    )
    try:
        await query.edit_message_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=product_keyboard(product_id, current_qty),
        )
    except Exception:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=product_keyboard(product_id, current_qty),
        )


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Добавлено в корзину!")
    product_id = int(query.data.split(":")[1])
    qty = context.user_data.get(f"qty_{product_id}", 1)

    async with AsyncSessionLocal() as session:
        product = await get_product(session, product_id)

    if not product:
        return

    cart = context.user_data.setdefault("cart", {})
    pid_str = str(product_id)
    if pid_str in cart:
        cart[pid_str]["qty"] += qty
    else:
        cart[pid_str] = {
            "name": product.name,
            "price": float(product.price),
            "qty": qty,
        }
    context.user_data[f"qty_{product_id}"] = 1


async def back_to_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category_id = context.user_data.get("last_category_id")
    page = context.user_data.get("last_page", 1)
    if not category_id:
        await show_catalog(update, context)
        return
    query.data = f"cat:{category_id}:p:{page}"
    await show_category(update, context)


def register(app):
    logger.info("📝 Регистрация хендлеров каталога...")
    app.add_handler(CallbackQueryHandler(show_catalog, pattern="^catalog$"))
    app.add_handler(CallbackQueryHandler(show_category, pattern=r"^cat:\d+(:\w+:\d+)?$"))
    app.add_handler(CallbackQueryHandler(show_product, pattern=r"^prod:\d+$"))
    app.add_handler(CallbackQueryHandler(handle_qty, pattern=r"^qty:\d+:[+-]$"))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern=r"^add:\d+$"))
    app.add_handler(CallbackQueryHandler(back_to_products, pattern="^back_prod$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^noop$"))
    logger.info("✅ Хендлеры каталога зарегистрированы!")
