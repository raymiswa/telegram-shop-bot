from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard(cart_count: int = 0) -> ReplyKeyboardMarkup:
    cart_label = f"🛒 Моя корзина ({cart_count})" if cart_count else "🛒 Моя корзина"
    return ReplyKeyboardMarkup(
        [
            ["🛍 Каталог товаров"],
            [cart_label],
            ["📦 Мои заказы", "ℹ️ О магазине"],
        ],
        resize_keyboard=True,
    )


def categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{c.emoji} {c.name}", callback_data=f"cat_{c.id}")]
        for c in categories
    ]
    buttons.append([InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products: list, category_id: int, page: int, total: int, per_page: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{p.name} — {float(p.price):,.0f} ₽", callback_data=f"prod_{p.id}")]
        for p in products
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"cat_{category_id}_page_{page - 1}"))
    if (page + 1) * per_page < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"cat_{category_id}_page_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Категории", callback_data="catalog")])
    return InlineKeyboardMarkup(buttons)


def product_keyboard(product_id: int, qty: int = 1) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data=f"qty_dec_{product_id}"),
            InlineKeyboardButton(str(qty), callback_data=f"qty_show_{product_id}"),
            InlineKeyboardButton("➕", callback_data=f"qty_inc_{product_id}"),
        ],
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"add_cart_{product_id}_{qty}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_cat_{product_id}")],
    ])


def cart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Очистить", callback_data="cart_clear"),
         InlineKeyboardButton("✅ Оформить", callback_data="cart_checkout")],
    ])


def cart_items_keyboard(cart_products: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"❌ Удалить: {name}", callback_data=f"cart_remove_{pid}")]
        for pid, name in cart_products
    ]
    buttons.append([
        InlineKeyboardButton("🗑 Очистить", callback_data="cart_clear"),
        InlineKeyboardButton("✅ Оформить", callback_data="cart_checkout"),
    ])
    return InlineKeyboardMarkup(buttons)


def delivery_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Самовывоз", callback_data="delivery_pickup"),
         InlineKeyboardButton("🚚 Доставка", callback_data="delivery_courier")],
        [InlineKeyboardButton("❌ Отмена", callback_data="order_cancel")],
    ])


def pickup_points_keyboard(points: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"📍 {p.name}", callback_data=f"pickup_point_{p.id}")]
        for p in points
    ]
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="order_cancel")])
    return InlineKeyboardMarkup(buttons)


def payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 USDT TRC20", callback_data="pay_usdt"),
         InlineKeyboardButton("💵 Наличные", callback_data="pay_cash")],
        [InlineKeyboardButton("❌ Отмена", callback_data="order_cancel")],
    ])


def usdt_payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_order_{order_id}")],
    ])


def order_pickup_map_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗺 Показать на карте", callback_data=f"order_map_{order_id}")]
    ])


def orders_filter_keyboard(current: str = "all") -> InlineKeyboardMarkup:
    filters = [
        ("Все", "all"), ("Ожидают оплаты", "awaiting_payment"),
        ("Оплачены", "paid"), ("Готовы", "ready"), ("Выданы", "completed"),
    ]
    buttons = [
        [InlineKeyboardButton(f"{'✅ ' if current == key else ''}{label}", callback_data=f"orders_filter_{key}")]
        for label, key in filters
    ]
    return InlineKeyboardMarkup(buttons)


def order_detail_keyboard(order) -> InlineKeyboardMarkup:
    buttons = []
    if order.status in ("new", "awaiting_payment"):
        buttons.append([InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_order_{order.id}")])
    return InlineKeyboardMarkup(buttons) if buttons else None
