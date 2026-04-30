import asyncio
import logging
from telegram.ext import Application
from database.database import init_db
from handlers import register_all_handlers
import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main():
    if not config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан в .env")

    await init_db()
    logger.info("База данных инициализирована")

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    register_all_handlers(app)
    logger.info("Хендлеры зарегистрированы")

    logger.info("Бот запущен")
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
