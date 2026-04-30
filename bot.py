import logging
import os
from datetime import datetime
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    LabeledPrice
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== КОНФИГУРАЦИЯ =====
TOKEN = os.getenv("BOT_TOKEN", "8061201371:AAEHogHvhKiWYqjdTEt6QNl3RI8lohM4c4k")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "")  # Получи в @BotFather -> Payments

# ID администраторов (ЗАМЕНИ НА СВОИ!)
ADMINS = [123456789, 987654321]  # Узнать свой ID: @userinfobot

# Состояния для ConversationHandler
ADDING_PRODUCT_NAME, ADDING_PRODUCT_DESC, ADDING_PRODUCT_PRICE, ADDING_PRODUCT_PHOTO, ADDING_PRODUCT_CATEGORY = range(5)
EDITING_PRODUCT_FIELD = range(1)

# ===== БАЗА ДАННЫХ (в памяти, для production используй SQLite/PostgreSQL) =====
PRODUCTS = {
    "pizza_1": {
        "name": "🍕 Пицца Маргарита",
        "description": "Томаты, моцарелла, базилик",
        "price": 450,
        "photo": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500"
    },
    "pizza_2": {
        "name": "🍕 Пицца Пепперони",
        "description": "Пепперони, сыр, томатный соус",
        "price": 520,
        "photo": "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=500"
    },
    "burger_1": {
        "name": "🍔 Чизбургер",
        "description": "Говядина, сыр чеддер, соус",
        "price": 350,
        "photo": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500"
    },
    "drink_1": {
        "name": "🥤 Кока-Кола 0.5л",
        "description": "Освежающий напиток",
        "price": 100,
        "photo": "https://images.unsplash.com/photo-1554866585-cd94860890b7?w=500"
    },
}

CATEGORIES = {
    "pizza": {"name": "🍕 Пицца", "items": ["pizza_1", "pizza_2"]},
    "burgers": {"name": "🍔 Бургеры", "items": ["burger_1"]},
    "drinks": {"name": "🥤 Напитки", "items": ["drink_1"]},
}

# Корзины пользователей: {user_id: {product_id: quantity}}
carts = {}

# Заказы: {order_id: {user_id, items, total, address, status, timestamp}}
orders = {}
order_counter = 1

# Статистика
stats = {
    "total_orders": 0,
    "total_revenue": 0,
    "product_sales": {}  # {product_id: quantity}
}

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def is_admin(user_id: int) -> bool:
    """Проверка админских прав"""
    return user_id in ADMINS

def get_cart(user_id: int) -> dict:
    """Получить корзину пользователя"""
    if user_id not in carts:
        carts[user_id] = {}
    return carts[user_id]

def get_cart_total(user_id: int) -> int:
    """Получить сумму корзины"""
    cart = get_cart(user_id)
    total = 0
    for product_id, quantity in cart.items():
        total += PRODUCTS[product_id]["price"] * quantity
    return total

def get_cart_text(user_id: int) -> str:
    """Сформировать текст корзины"""
    cart = get_cart(user_id)
    if not cart:
        return "🛒 Ваша корзина пуста"
    
    text = "🛒 <b>Ваша корзина:</b>\n\n"
    for product_id, quantity in cart.items():
        product = PRODUCTS[product_id]
        text += f"{product['name']} x{quantity}\n"
        text += f"   {product['price']} ₽ × {quantity} = {product['price'] * quantity} ₽\n\n"
    
    text += f"<b>Итого: {get_cart_total(user_id)} ₽</b>"
    return text

# ===== ГЛАВНОЕ МЕНЮ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - главное меню"""
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🛒 Каталог товаров", callback_data="catalog")],
        [InlineKeyboardButton("🧺 Моя корзина", callback_data="cart")],
        [InlineKeyboardButton("ℹ️ О магазине", callback_data="about")],
    ]
    
    # Добавляем админскую кнопку для администраторов
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👨‍💼 Админ-панель", callback_data="admin")])
    
    text = (
        "👋 <b>Добро пожаловать в наш магазин!</b>\n\n"
        "Выберите раздел из меню ниже:"
    )
    
    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await update.callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

# ===== КАТАЛОГ =====
async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать категории товаров"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for cat_id, cat_data in CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(cat_data["name"], callback_data=f"category_{cat_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="start")])
    
    await query.edit_message_text(
        "📂 <b>Выберите категорию:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== КАТЕГОРИЯ =====
async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать товары категории"""
    query = update.callback_query
    await query.answer()
    
    cat_id = query.data.split("_")[1]
    category = CATEGORIES[cat_id]
    
    keyboard = []
    for product_id in category["items"]:
        product = PRODUCTS[product_id]
        keyboard.append([InlineKeyboardButton(
            product["name"], 
            callback_data=f"product_{product_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к категориям", callback_data="catalog")])
    
    await query.edit_message_text(
        f"📦 <b>{category['name']}</b>\n\nВыберите товар:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== КАРТОЧКА ТОВАРА =====
async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали товара"""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[1]
    product = PRODUCTS[product_id]
    
    # Находим категорию товара
    cat_id = None
    for cid, cdata in CATEGORIES.items():
        if product_id in cdata["items"]:
            cat_id = cid
            break
    
    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data=f"decrease_{product_id}"),
            InlineKeyboardButton("🛒 В корзину", callback_data=f"add_{product_id}"),
            InlineKeyboardButton("➕", callback_data=f"increase_{product_id}"),
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"category_{cat_id}")]
    ]
    
    text = (
        f"<b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 Цена: <b>{product['price']} ₽</b>"
    )
    
    try:
        # Пробуем отправить фото
        await query.message.delete()
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=product["photo"],
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки фото: {e}")
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

# ===== ДОБАВЛЕНИЕ В КОРЗИНУ =====
async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить товар в корзину"""
    query = update.callback_query
    await query.answer("✅ Добавлено в корзину!")
    
    product_id = query.data.split("_")[1]
    user_id = query.from_user.id
    
    cart = get_cart(user_id)
    if product_id in cart:
        cart[product_id] += 1
    else:
        cart[product_id] = 1

# ===== КОРЗИНА =====
async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать корзину"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cart = get_cart(user_id)
    
    if not cart:
        keyboard = [[InlineKeyboardButton("⬅️ В магазин", callback_data="catalog")]]
        await query.edit_message_text(
            "🛒 Ваша корзина пуста\n\nДобавьте товары из каталога!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for product_id in cart.keys():
        product = PRODUCTS[product_id]
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 {product['name']}", 
                callback_data=f"remove_{product_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart")])
    keyboard.append([InlineKeyboardButton("⬅️ Продолжить покупки", callback_data="catalog")])
    
    await query.edit_message_text(
        get_cart_text(user_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== УДАЛЕНИЕ ИЗ КОРЗИНЫ =====
async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить товар из корзины"""
    query = update.callback_query
    await query.answer("🗑 Товар удален")
    
    product_id = query.data.split("_")[1]
    user_id = query.from_user.id
    
    cart = get_cart(user_id)
    if product_id in cart:
        del cart[product_id]
    
    await show_cart(update, context)

# ===== ОЧИСТКА КОРЗИНЫ =====
async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистить всю корзину"""
    query = update.callback_query
    await query.answer("🗑 Корзина очищена")
    
    user_id = query.from_user.id
    carts[user_id] = {}
    
    await show_cart(update, context)

# ===== ОФОРМЛЕНИЕ ЗАКАЗА =====
async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оформление заказа"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cart = get_cart(user_id)
    
    if not cart:
        await query.answer("❌ Корзина пуста!", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 Ввести адрес доставки", callback_data="enter_address")],
        [InlineKeyboardButton("⬅️ Назад к корзине", callback_data="cart")]
    ]
    
    text = (
        "📋 <b>Оформление заказа</b>\n\n"
        f"{get_cart_text(user_id)}\n\n"
        "Укажите адрес доставки:"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== ВВОД АДРЕСА =====
async def enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос адреса доставки"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['awaiting_address'] = True
    
    await query.edit_message_text(
        "📍 Введите адрес доставки:\n\n"
        "Например: ул. Ленина, д. 10, кв. 5"
    )

# ===== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ =====
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений (адрес, телефон и т.д.)"""
    if context.user_data.get('awaiting_address'):
        address = update.message.text
        user_id = update.message.from_user.id
        
        context.user_data['awaiting_address'] = False
        context.user_data['address'] = address
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить заказ", callback_data="confirm_order")],
            [InlineKeyboardButton("⬅️ Изменить адрес", callback_data="enter_address")]
        ]
        
        text = (
            "✅ <b>Подтверждение заказа</b>\n\n"
            f"{get_cart_text(user_id)}\n\n"
            f"📍 Адрес доставки:\n{address}\n\n"
            "Подтвердите заказ или измените адрес:"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

# ===== ПОДТВЕРЖДЕНИЕ ЗАКАЗА =====
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальное подтверждение заказа"""
    query = update.callback_query
    await query.answer()
    
    global order_counter
    user_id = query.from_user.id
    address = context.user_data.get('address', 'Не указан')
    cart = get_cart(user_id).copy()
    total = get_cart_total(user_id)
    
    # Создаем заказ
    order_id = order_counter
    order_counter += 1
    
    orders[order_id] = {
        "user_id": user_id,
        "username": query.from_user.username or "Без username",
        "items": cart,
        "total": total,
        "address": address,
        "status": "новый",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Обновляем статистику
    stats["total_orders"] += 1
    stats["total_revenue"] += total
    for product_id, quantity in cart.items():
        if product_id not in stats["product_sales"]:
            stats["product_sales"][product_id] = 0
        stats["product_sales"][product_id] += quantity
    
    # Формируем текст заказа
    order_text = (
        f"🎉 <b>Заказ #{order_id} принят!</b>\n\n"
        f"{get_cart_text(user_id)}\n\n"
        f"📍 Адрес: {address}\n\n"
        "⏱ Ожидаемое время доставки: 30-40 минут\n\n"
        "Спасибо за заказ! 💚"
    )
    
    # Очищаем корзину
    carts[user_id] = {}
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="start")]]
    
    await query.edit_message_text(
        order_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    # Отправляем уведомление всем администраторам
    admin_text = (
        f"🔔 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
        f"👤 Клиент: @{query.from_user.username or 'Без username'} (ID: {user_id})\n"
        f"📍 Адрес: {address}\n\n"
        f"<b>Состав заказа:</b>\n"
    )
    
    for product_id, quantity in cart.items():
        product = PRODUCTS[product_id]
        admin_text += f"{product['name']} x{quantity} = {product['price'] * quantity} ₽\n"
    
    admin_text += f"\n💰 <b>Итого: {total} ₽</b>"
    
    admin_keyboard = [
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"order_accept_{order_id}"),
            InlineKeyboardButton("❌ Отменить", callback_data=f"order_cancel_{order_id}")
        ],
        [InlineKeyboardButton("👨‍💼 Админ-панель", callback_data="admin")]
    ]
    
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(
                admin_id,
                admin_text,
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")

# ===== О МАГАЗИНЕ =====
async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о магазине"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "ℹ️ <b>О нашем магазине</b>\n\n"
        "🍕 Доставка еды\n"
        "⏱ Режим работы: 10:00 - 23:00\n"
        "🚚 Бесплатная доставка от 500 ₽\n"
        "📞 Телефон: +7 (999) 123-45-67\n\n"
        "Спасибо, что выбираете нас! 💚"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Главное меню", callback_data="start")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== АДМИН-ПАНЕЛЬ =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню админ-панели"""
    query = update.callback_query
    user_id = query.from_user.id if query else update.effective_user.id
    
    if not is_admin(user_id):
        if query:
            await query.answer("❌ У вас нет доступа к админ-панели!", show_alert=True)
        return
    
    if query:
        await query.answer()
    
    # Считаем активные заказы
    active_orders = len([o for o in orders.values() if o["status"] == "новый"])
    
    text = (
        "👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"📊 Всего заказов: {stats['total_orders']}\n"
        f"🔔 Активных заказов: {active_orders}\n"
        f"💰 Общая выручка: {stats['total_revenue']} ₽\n"
        f"📦 Товаров в каталоге: {len(PRODUCTS)}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton("📦 Товары", callback_data="admin_products")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📁 Категории", callback_data="admin_categories")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="start")]
    ]
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

# ===== АДМИН - ЗАКАЗЫ =====
async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список заказов"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа!", show_alert=True)
        return
    
    if not orders:
        text = "📋 <b>Заказов пока нет</b>"
        keyboard = [[InlineKeyboardButton("⬅️ Админ-панель", callback_data="admin")]]
    else:
        text = "📋 <b>СПИСОК ЗАКАЗОВ</b>\n\n"
        keyboard = []
        
        # Сортируем заказы по ID (новые сверху)
        sorted_orders = sorted(orders.items(), key=lambda x: x[0], reverse=True)
        
        for order_id, order in sorted_orders[:10]:  # Показываем последние 10
            status_emoji = "🔔" if order["status"] == "новый" else "✅" if order["status"] == "принят" else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} Заказ #{order_id} - {order['total']} ₽",
                    callback_data=f"admin_order_{order_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Админ-панель", callback_data="admin")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== АДМИН - ДЕТАЛИ ЗАКАЗА =====
async def admin_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детали конкретного заказа"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    order_id = int(query.data.split("_")[-1])
    order = orders.get(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден!", show_alert=True)
        return
    
    status_emoji = "🔔" if order["status"] == "новый" else "✅" if order["status"] == "принят" else "❌"
    
    text = (
        f"{status_emoji} <b>ЗАКАЗ #{order_id}</b>\n\n"
        f"👤 Клиент: @{order['username']} (ID: {order['user_id']})\n"
        f"📍 Адрес: {order['address']}\n"
        f"🕐 Время: {order['timestamp']}\n"
        f"📊 Статус: {order['status']}\n\n"
        "<b>Состав заказа:</b>\n"
    )
    
    for product_id, quantity in order["items"].items():
        product = PRODUCTS[product_id]
        text += f"{product['name']} x{quantity} = {product['price'] * quantity} ₽\n"
    
    text += f"\n💰 <b>Итого: {order['total']} ₽</b>"
    
    keyboard = []
    if order["status"] == "новый":
        keyboard.append([
            InlineKeyboardButton("✅ Принять", callback_data=f"order_accept_{order_id}"),
            InlineKeyboardButton("❌ Отменить", callback_data=f"order_cancel_{order_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ К списку заказов", callback_data="admin_orders")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== АДМИН - УПРАВЛЕНИЕ СТАТУСОМ ЗАКАЗА =====
async def admin_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменение статуса заказа"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Нет доступа!", show_alert=True)
        return
    
    action, order_id = query.data.split("_")[1], int(query.data.split("_")[-1])
    order = orders.get(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден!", show_alert=True)
        return
    
    if action == "accept":
        order["status"] = "принят"
        await query.answer("✅ Заказ принят!")
        
        # Уведомляем клиента
        try:
            await context.bot.send_message(
                order["user_id"],
                f"✅ Ваш заказ #{order_id} принят в работу!\n\n"
                "🚚 Готовим и везём к вам! ⏱ 30-40 минут"
            )
        except:
            pass
            
    elif action == "cancel":
        order["status"] = "отменён"
        await query.answer("❌ Заказ отменён!")
        
        # Уведомляем клиента
        try:
            await context.bot.send_message(
                order["user_id"],
                f"❌ К сожалению, ваш заказ #{order_id} отменён.\n\n"
                "Свяжитесь с нами для уточнения деталей."
            )
        except:
            pass
    
    # Обновляем сообщение
    await admin_order_details(update, context)

# ===== АДМИН - ТОВАРЫ =====
async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление товарами"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    text = f"📦 <b>УПРАВЛЕНИЕ ТОВАРАМИ</b>\n\nВсего товаров: {len(PRODUCTS)}"
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton("📝 Редактировать товар", callback_data="admin_edit_product_list")],
        [InlineKeyboardButton("🗑 Удалить товар", callback_data="admin_delete_product_list")],
        [InlineKeyboardButton("⬅️ Админ-панель", callback_data="admin")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== АДМИН - СПИСОК ТОВАРОВ ДЛЯ РЕДАКТИРОВАНИЯ =====
async def admin_edit_product_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список товаров для редактирования"""
    query = update.callback_query
    await query.answer()
    
    text = "📝 <b>Выберите товар для редактирования:</b>"
    keyboard = []
    
    for product_id, product in PRODUCTS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{product['name']} - {product['price']} ₽",
                callback_data=f"admin_edit_product_{product_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_products")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== АДМИН - РЕДАКТИРОВАНИЕ ТОВАРА =====
async def admin_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование конкретного товара"""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    product = PRODUCTS[product_id]
    
    text = (
        f"📝 <b>Редактирование товара</b>\n\n"
        f"ID: {product_id}\n"
        f"Название: {product['name']}\n"
        f"Описание: {product['description']}\n"
        f"Цена: {product['price']} ₽\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить цену", callback_data=f"edit_price_{product_id}")],
        [InlineKeyboardButton("✏️ Изменить название", callback_data=f"edit_name_{product_id}")],
        [InlineKeyboardButton("✏️ Изменить описание", callback_data=f"edit_desc_{product_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_edit_product_list")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== АДМИН - СПИСОК ТОВАРОВ ДЛЯ УДАЛЕНИЯ =====
async def admin_delete_product_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список товаров для удаления"""
    query = update.callback_query
    await query.answer()
    
    text = "🗑 <b>Выберите товар для удаления:</b>\n\n⚠️ Это действие необратимо!"
    keyboard = []
    
    for product_id, product in PRODUCTS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 {product['name']}",
                callback_data=f"admin_delete_confirm_{product_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_products")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== АДМИН - ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ =====
async def admin_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление товара"""
    query = update.callback_query
    
    product_id = query.data.split("_")[-1]
    product_name = PRODUCTS[product_id]["name"]
    
    # Удаляем из всех категорий
    for category in CATEGORIES.values():
        if product_id in category["items"]:
            category["items"].remove(product_id)
    
    # Удаляем товар
    del PRODUCTS[product_id]
    
    await query.answer(f"✅ Товар '{product_name}' удалён!", show_alert=True)
    await admin_products(update, context)

# ===== АДМИН - СТАТИСТИКА =====
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика продаж"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    text = (
        "📊 <b>СТАТИСТИКА ПРОДАЖ</b>\n\n"
        f"📋 Всего заказов: {stats['total_orders']}\n"
        f"💰 Общая выручка: {stats['total_revenue']} ₽\n"
    )
    
    if stats['total_orders'] > 0:
        text += f"💵 Средний чек: {stats['total_revenue'] // stats['total_orders']} ₽\n\n"
    
    if stats["product_sales"]:
        text += "<b>Топ продаж:</b>\n"
        sorted_sales = sorted(
            stats["product_sales"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for i, (product_id, quantity) in enumerate(sorted_sales[:5], 1):
            if product_id in PRODUCTS:
                product = PRODUCTS[product_id]
                revenue = quantity * product["price"]
                text += f"{i}. {product['name']}: {quantity} шт. ({revenue} ₽)\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Админ-панель", callback_data="admin")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== АДМИН - КАТЕГОРИИ =====
async def admin_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление категориями"""
    query = update.callback_query
    await query.answer()
    
    text = "📁 <b>КАТЕГОРИИ</b>\n\n"
    
    for cat_id, cat_data in CATEGORIES.items():
        text += f"{cat_data['name']}: {len(cat_data['items'])} товаров\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Админ-панель", callback_data="admin")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ===== РОУТЕР CALLBACK =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех кнопок"""
    query = update.callback_query
    data = query.data
    
    # Роутинг по callback_data
    if data == "start":
        await start(update, context)
    elif data == "catalog":
        await show_catalog(update, context)
    elif data.startswith("category_"):
        await show_category(update, context)
    elif data.startswith("product_"):
        await show_product(update, context)
    elif data.startswith("add_"):
        await add_to_cart(update, context)
    elif data == "cart":
        await show_cart(update, context)
    elif data.startswith("remove_"):
        await remove_from_cart(update, context)
    elif data == "clear_cart":
        await clear_cart(update, context)
    elif data == "checkout":
        await checkout(update, context)
    elif data == "enter_address":
        await enter_address(update, context)
    elif data == "confirm_order":
        await confirm_order(update, context)
    elif data == "about":
        await show_about(update, context)
    
    # АДМИНСКИЕ ФУНКЦИИ
    elif data == "admin":
        await admin_panel(update, context)
    elif data == "admin_orders":
        await admin_orders(update, context)
    elif data.startswith("admin_order_"):
        await admin_order_details(update, context)
    elif data.startswith("order_accept_") or data.startswith("order_cancel_"):
        await admin_order_status(update, context)
    elif data == "admin_products":
        await admin_products(update, context)
    elif data == "admin_edit_product_list":
        await admin_edit_product_list(update, context)
    elif data.startswith("admin_edit_product_"):
        await admin_edit_product(update, context)
    elif data == "admin_delete_product_list":
        await admin_delete_product_list(update, context)
    elif data.startswith("admin_delete_confirm_"):
        await admin_delete_product(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_categories":
        await admin_categories(update, context)

# ===== ЗАПУСК БОТА =====
def main():
    """Запуск приложения"""
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))  # Быстрый доступ для админов
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запускаем бота
    logger.info("🚀 Бот запущен!")
    logger.info(f"👨‍💼 Администраторы: {ADMINS}")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
