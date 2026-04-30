import asyncio
import logging
from telegram.ext import Application

from config import BOT_TOKEN
from database.database import init_db
from handlers.user import start, catalog, cart, orders, payment
from handlers.admin import (
    panel, orders as admin_orders, payments, products,
    categories, pickup_points, wallets, stats, broadcast, users
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан в .env")
    
    # Инициализация БД
    await init_db()
    logger.info("База данных инициализирована")
    
    # Создание приложения
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация хендлеров пользователей
    start.register_handlers(app)
    catalog.register_handlers(app)
    cart.register_handlers(app)
    orders.register_handlers(app)
    payment.register_handlers(app)
    
    # Регистрация хендлеров админов
    panel.register_handlers(app)
    admin_orders.register_handlers(app)
    payments.register_handlers(app)
    products.register_handlers(app)
    categories.register_handlers(app)
    pickup_points.register_handlers(app)
    wallets.register_handlers(app)
    stats.register_handlers(app)
    broadcast.register_handlers(app)
    users.register_handlers(app)
    
    logger.info("Хендлеры зарегистрированы")
    logger.info("Бот запущен")
    
    # Запуск polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    # Держим бота активным
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
