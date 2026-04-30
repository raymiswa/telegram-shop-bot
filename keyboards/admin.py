from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def admin_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📋 Заказы", "💰 Платежи"],
            ["📦 Товары", "📁 Категории"],
            ["📍 Точки выдачи", "💳 Кошельки USDT"],
            ["👥 Пользователи", "📊 Статистика"],
            ["📬 Рассылка"],
        ],
        resize_keyboard=True,
    )


def back_to_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬆️ Админ-панель", callback_data="admin_panel")]])


def orders_filter_keyboard(current: str = "all") -> InlineKeyboardMarkup:
    filters = [
        ("Все", "all"), ("Новые", "new"), ("Ожид. оплаты", "awaiting_payment"),
        ("Оплачены", "paid"), ("Готовы", "ready"), ("Выданы", "completed"), ("Отменены", "cancelled"),
    ]
    rows = []
    row = []
    for label, key in filters:
        prefix = "✅ " if current == key else ""
        row.append(InlineKeyboardButton(f"{prefix}{label}", callback_data=f"admin_orders_filter_{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬆️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


def order_actions_keyboard(order) -> InlineKeyboardMarkup:
    buttons = []
    if order.payment_method == "usdt" and order.payment_address:
        buttons.append([InlineKeyboardButton("🔍 Проверить в Tronscan",
                                             url=f"https://tronscan.org/#/address/{order.payment_address}")])
    if order.status in ("awaiting_payment",):
        buttons.append([
            InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"admin_confirm_{order.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{order.id}"),
        ])
    if order.status == "paid":
        buttons.append([InlineKeyboardButton("📦 Готов к выдаче", callback_data=f"admin_ready_{order.id}")])
    if order.status == "ready":
        buttons.append([InlineKeyboardButton("✔️ Выдан", callback_data=f"admin_complete_{order.id}")])
    if order.status not in ("completed", "cancelled"):
        buttons.append([InlineKeyboardButton("❌ Отменить", callback_data=f"admin_cancel_{order.id}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад к заказам", callback_data="admin_orders_back")])
    return InlineKeyboardMarkup(buttons)


def payment_confirm_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"admin_confirm_{order_id}"),
         InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{order_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_payments")],
    ])


def payments_list_keyboard(orders: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"#{o.id} — {float(o.total_price_usdt or 0):.2f} USDT — @{o.user.username or o.user.telegram_id}",
            callback_data=f"admin_payment_{o.id}"
        )]
        for o in orders
    ]
    buttons.append([InlineKeyboardButton("⬆️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def products_list_keyboard(products: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{p.name} — {float(p.price):,.0f} ₽", callback_data=f"admin_prod_{p.id}")]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")])
    buttons.append([InlineKeyboardButton("⬆️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def product_actions_keyboard(product) -> InlineKeyboardMarkup:
    avail_label = "🔴 Скрыть" if product.is_available else "🟢 Показать"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить цену", callback_data=f"admin_prod_price_{product.id}"),
         InlineKeyboardButton("📦 Изменить остаток", callback_data=f"admin_prod_stock_{product.id}")],
        [InlineKeyboardButton(avail_label, callback_data=f"admin_prod_toggle_{product.id}"),
         InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_prod_delete_{product.id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_products")],
    ])


def categories_list_keyboard(categories: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{c.emoji} {c.name}", callback_data=f"admin_cat_{c.id}")]
        for c in categories
    ]
    buttons.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="admin_add_category")])
    buttons.append([InlineKeyboardButton("⬆️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def category_actions_keyboard(cat) -> InlineKeyboardMarkup:
    active_label = "🔴 Деактивировать" if cat.is_active else "🟢 Активировать"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(active_label, callback_data=f"admin_cat_toggle_{cat.id}"),
         InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_cat_delete_{cat.id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_categories")],
    ])


def pickup_points_list_keyboard(points: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{'✅' if p.is_active else '❌'} {p.name}",
            callback_data=f"admin_pp_{p.id}"
        )]
        for p in points
    ]
    buttons.append([InlineKeyboardButton("➕ Добавить точку", callback_data="admin_add_pp")])
    buttons.append([InlineKeyboardButton("⬆️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def pickup_point_actions_keyboard(pp) -> InlineKeyboardMarkup:
    toggle_label = "🔴 Деактивировать" if pp.is_active else "🟢 Активировать"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"admin_pp_toggle_{pp.id}"),
         InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_pp_delete_{pp.id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_pickup_points")],
    ])


def wallets_list_keyboard(wallets: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{'✅' if w.is_active else '❌'} {w.address[:6]}...{w.address[-4:]}",
            callback_data=f"admin_wallet_{w.id}"
        )]
        for w in wallets
    ]
    buttons.append([InlineKeyboardButton("➕ Добавить кошелёк", callback_data="admin_add_wallet")])
    buttons.append([InlineKeyboardButton("⬆️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def wallet_actions_keyboard(wallet) -> InlineKeyboardMarkup:
    toggle_label = "🔴 Деактивировать" if wallet.is_active else "🟢 Активировать"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"admin_wallet_toggle_{wallet.id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_wallets")],
    ])
