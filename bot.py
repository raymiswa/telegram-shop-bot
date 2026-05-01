import logging
import asyncio
from telegram.ext import Application

from config import BOT_TOKEN
from database.database import init_db
from handlers import register_all_handlers

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
    
    # Регистрация всех хендлеров
    register_all_handlers(app)
    
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
    asyncio.run(main())
