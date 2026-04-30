import os
import logging
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.request import HTTPXRequest

# ===== ЛОГИ =====
logging.basicConfig(level=logging.INFO)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

# ===== ТОВАРЫ =====
PRODUCTS = [
    {"id": 1, "name": "Gold", "price": 60},
    {"id": 2, "name": "Silver", "price": 1},
    {"id": 3, "name": "Platinum", "price": 30},
]

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop")]
    ]

    await update.message.reply_text(
        "Добро пожаловать!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== КНОПКИ =====
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    print("CLICK:", data)

    try:
        # ===== МАГАЗИН =====
        if data == "shop":
            keyboard = []

            for p in PRODUCTS:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{p['name']} — ${p['price']}",
                        callback_data=f"product_{p['id']}"
                    )
                ])

            await context.bot.send_message(
                chat_id=user_id,
                text="📦 Каталог:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # ===== ТОВАР =====
        elif data.startswith("product_"):
            pid = int(data.split("_")[1])
            product = next(p for p in PRODUCTS if p["id"] == pid)

            keyboard = [
                [InlineKeyboardButton("💰 Купить", callback_data=f"buy_{pid}")]
            ]

            await context.bot.send_message(
                chat_id=user_id,
                text=f"{product['name']}\nЦена: ${product['price']}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # ===== ПОКУПКА =====
        elif data.startswith("buy_"):
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Заказ создан (тест)"
            )

    except Exception as e:
        print("ERROR:", e)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Ошибка: {e}"
        )

# ===== МЕНЮ TELEGRAM =====
async def set_menu(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
    ])

# ===== ЗАПУСК =====
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Нет BOT_TOKEN")

    # 🔥 ФИКСЫ для Railway + таймауты
    request = HTTPXRequest(
        proxy=None,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    app = Application.builder().token(TOKEN).request(request).build()

    app.post_init = set_menu

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    print("Bot started...")

    app.run_polling(
        drop_pending_updates=True,
        timeout=30,
        read_timeout=30,
    )
