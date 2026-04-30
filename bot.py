import logging
import os
from telegram.ext import Application

from config import BOT_TOKEN
from database.database import init_db
from handlers import register_all_handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Главная функция запуска бота"""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан в .env")
    
    # Автоматическая инициализация тестовых данных
    if os.getenv('RUN_INIT_DATA') == 'true':
        logger.info("🔧 Запуск инициализации тестовых данных...")
        import asyncio
        from init_data import init_default_data
        
        # Инициализируем БД и добавляем данные
        asyncio.get_event_loop().run_until_complete(init_db())
        asyncio.get_event_loop().run_until_complete(init_default_data())
        logger.info("✅ Тестовые данные добавлены!")
    
    # Создание приложения
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация всех хендлеров
    register_all_handlers(app)
    
    logger.info("Хендлеры зарегистрированы")
    logger.info("Бот запущен")
    
    # Запуск polling
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    # Инициализация БД
    import asyncio
    asyncio.get_event_loop().run_until_complete(init_db())
    logger.info("База данных инициализирована")
    
    main()
