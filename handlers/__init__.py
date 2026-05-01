def register_all_handlers(app):
    from handlers.user import start, catalog, cart, orders, payment
    from handlers.admin import (
        panel, orders as admin_orders, payments, products,
        categories, pickup_points, wallets, stats, broadcast, users,
    )

    # ═══════════════════════════════════════════════════
    # ПОРЯДОК РЕГИСТРАЦИИ КРИТИЧЕН!
    # 1. Сначала простые хендлеры
    # 2. ПОТОМ ConversationHandler'ы
    # ═══════════════════════════════════════════════════

    # 1. Простые хендлеры
    start.register(app)
    catalog.register(app)
    cart.register(app)
    orders.register(app)
    panel.register(app)
    admin_orders.register(app)
    stats.register(app)
    users.register(app)

    # 2. ConversationHandler'ы (только после простых!)
    payment.register(app)
    payments.register(app)
    products.register(app)
    categories.register(app)
    pickup_points.register(app)
    wallets.register(app)
    broadcast.register(app)
