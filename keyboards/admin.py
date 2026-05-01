from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def admin_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["📦 Заказы", "💰 Платежи"],
        ["🛒 Товары", "📂 Категории"],
        ["📍 Точки выдачи", "💎 USDT кошельки"],
        ["👥 Пользователи", "📊 Статистика"],
        ["📬 Рассылка"],
    ], resize_keyboard=True)


def payments_list_keyboard(orders) -> InlineKeyboardMarkup:
    buttons = []
    for order in orders:
        username = order.user.username or "нет ника"
        usdt = f"{float(order.total_price_usdt):.2f}" if order.total_price_usdt else "?"
        buttons.append([InlineKeyboardButton(
            f"#{order.id} — {usdt} USDT — @{username}",
            callback_data=f"admin_payment:{order.id}",
        )])
    if not buttons:
        buttons.append([InlineKeyboardButton("Нет ожидающих платежей", callback_data="noop")])
    return InlineKeyboardMarkup(buttons)


def payment_actions_keyboard(order_id: int, wallet_address: str | None = None) -> InlineKeyboardMarkup:
    buttons = []
    if wallet_address:
        buttons.append([InlineKeyboardButton(
            "🔍 Проверить в Tronscan",
            url=f"https://tronscan.org/#/address/{wallet_address}",
        )])
    buttons.append([InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"confirm_payment:{order_id}")])
    buttons.append([InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_payment:{order_id}")])
    return InlineKeyboardMarkup(buttons)


def admin_orders_keyboard(orders, status_filter: str = "all") -> InlineKeyboardMarkup:
    buttons = []
    for order in orders[:20]:
        from utils.formatters import fmt_status
        label = f"#{order.id} {fmt_status(order.status)} — {float(order.total_price):.0f}₽"
        buttons.append([InlineKeyboardButton(label, callback_data=f"admin_order:{order.id}")])
    nav = [
        InlineKeyboardButton("Все", callback_data="admin_orders:all"),
        InlineKeyboardButton("Новые", callback_data="admin_orders:new"),
        InlineKeyboardButton("Оплачены", callback_data="admin_orders:paid"),
    ]
    buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


def admin_order_actions_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    transitions = {
        "new": [("📦 Готов к выдаче", "ready"), ("❌ Отменить", "cancelled")],
        "paid": [("📦 Готов к выдаче", "ready"), ("✔️ Завершить", "completed")],
        "ready": [("✔️ Завершить", "completed")],
    }
    for label, new_status in transitions.get(status, []):
        buttons.append([InlineKeyboardButton(label, callback_data=f"order_status:{order_id}:{new_status}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_orders:all")])
    return InlineKeyboardMarkup(buttons)


def products_list_keyboard(products) -> InlineKeyboardMarkup:
    buttons = []
    for prod in products:
        status = "✅" if prod.is_available else "❌"
        buttons.append([InlineKeyboardButton(
            f"{status} {prod.name} — {float(prod.price):.0f}₽",
            callback_data=f"admin_product:{prod.id}",
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")])
    return InlineKeyboardMarkup(buttons)


def product_actions_keyboard(product_id: int, is_available: bool) -> InlineKeyboardMarkup:
    toggle_label = "❌ Скрыть" if is_available else "✅ Показать"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"admin_toggle_product:{product_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_delete_product:{product_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_products")],
    ])


def categories_list_keyboard(categories) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        status = "✅" if cat.is_active else "❌"
        emoji = cat.emoji or ""
        buttons.append([InlineKeyboardButton(
            f"{status} {emoji} {cat.name}",
            callback_data=f"admin_category:{cat.id}",
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="admin_add_category")])
    return InlineKeyboardMarkup(buttons)


def category_actions_keyboard(category_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_label = "❌ Деактивировать" if is_active else "✅ Активировать"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"admin_toggle_category:{category_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_delete_category:{category_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_categories")],
    ])


def pickup_points_list_keyboard(points) -> InlineKeyboardMarkup:
    buttons = []
    for point in points:
        status = "✅" if point.is_active else "❌"
        buttons.append([InlineKeyboardButton(
            f"{status} {point.name}",
            callback_data=f"admin_pickup:{point.id}",
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить точку", callback_data="admin_add_pickup")])
    return InlineKeyboardMarkup(buttons)


def pickup_point_actions_keyboard(point_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_label = "❌ Деактивировать" if is_active else "✅ Активировать"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"admin_toggle_pickup:{point_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_delete_pickup:{point_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_pickup_points")],
    ])


def wallets_list_keyboard(wallets) -> InlineKeyboardMarkup:
    buttons = []
    for wallet in wallets:
        status = "✅" if wallet.is_active else "❌"
        short = wallet.address[:8] + "..." + wallet.address[-6:]
        buttons.append([InlineKeyboardButton(
            f"{status} {short}",
            callback_data=f"admin_wallet:{wallet.id}",
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить кошелёк", callback_data="admin_add_wallet")])
    return InlineKeyboardMarkup(buttons)


def wallet_actions_keyboard(wallet_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_label = "❌ Деактивировать" if is_active else "✅ Активировать"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"admin_toggle_wallet:{wallet_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_delete_wallet:{wallet_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_wallets")],
    ])
