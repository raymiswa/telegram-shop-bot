import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "8061201371:AAEHogHvhKiWYqjdTEt6QNl3RI8lohM4c4k")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        [InlineKeyboardButton("✅ Тест кнопки 1", callback_data="test1")],
        [InlineKeyboardButton("✅ Тест кнопки 2", callback_data="test2")],
        [InlineKeyboardButton("✅ Тест кнопки 3", callback_data="test3")],
    ]
    
    await update.message.reply_text(
        "🧪 <b>Тест inline-кнопок</b>\n\nНажми на любую кнопку:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    
    # КРИТИЧНО: отвечаем на callback
    await query.answer()
    
    logger.info(f"🔘 Нажата кнопка: {query.data}")
    
    # Обрабатываем нажатие
    if query.data == "test1":
        await query.edit_message_text(
            "✅ Кнопка 1 работает!\n\nВернуться: /start",
            parse_mode="HTML"
        )
    elif query.data == "test2":
        await query.edit_message_text(
            "✅ Кнопка 2 работает!\n\nВернуться: /start",
            parse_mode="HTML"
        )
    elif query.data == "test3":
        await query.edit_message_text(
            "✅ Кнопка 3 работает!\n\nВернуться: /start",
            parse_mode="HTML"
        )

def main():
    """Запуск бота"""
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Тестовый бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
