from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(cart_count: int = 0) -> InlineKeyboardMarkup:
    cart_text = f"🧺 Корзина ({cart_count})" if cart_count > 0 else "🧺 Корзина"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Каталог товаров", callback_data="catalog")],
        [InlineKeyboardButton(cart_text, callback_data="cart")],
        [InlineKeyboardButton("📋 Мои заказы", callback_data="orders:all")],
        [InlineKeyboardButton("ℹ️ О магазине", callback_data="about")],
    ])


def categories_keyboard(categories) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        label = f"{cat.emoji} {cat.name}" if cat.emoji else cat.name
        buttons.append([InlineKeyboardButton(label, callback_data=f"cat:{cat.id}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products, page: int, total_pages: int, category_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for prod in products:
        price_str = f"{float(prod.price):.0f}₽"
        status = "" if prod.is_available and prod.stock_quantity > 0 else " ❌"
        buttons.append([InlineKeyboardButton(
            f"{prod.name} — {price_str}{status}",
            callback_data=f"prod:{prod.id}",
        )])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"cat:{category_id}:p:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"cat:{category_id}:p:{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 К категориям", callback_data="catalog")])
    return InlineKeyboardMarkup(buttons)


def product_keyboard(product_id: int, quantity: int = 1) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data=f"qty:{product_id}:-"),
            InlineKeyboardButton(str(quantity), callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"qty:{product_id}:+"),
        ],
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"add:{product_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_prod")],
    ])


def cart_keyboard(cart: dict) -> InlineKeyboardMarkup:
    buttons = []
    for pid, item in cart.items():
        buttons.append([InlineKeyboardButton(
            f"❌ {item['name']} ×{item['qty']}",
            callback_data=f"del_cart:{pid}",
        )])
    buttons.append([
        InlineKeyboardButton("🗑 Очистить", callback_data="clear_cart"),
        InlineKeyboardButton("✅ Оформить", callback_data="checkout"),
    ])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid:{order_id}")],
        [InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_order:{order_id}")],
    ])


def orders_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Все", callback_data="orders:all"),
            InlineKeyboardButton("Активные", callback_data="orders:active"),
        ],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ])


def order_detail_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == "awaiting_payment":
        buttons.append([InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_order:{order_id}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="orders:all")])
    return InlineKeyboardMarkup(buttons)


def payment_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 USDT TRC20", callback_data="pay:usdt_trc20")],
        [InlineKeyboardButton("💵 Наличные при получении", callback_data="pay:cash")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_checkout")],
    ])
