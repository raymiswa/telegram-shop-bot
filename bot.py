import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest

load_dotenv()

DB_PATH = "shop.db"


@dataclass
class Settings:
    bot_token: str
    wallet: str
    product_name: str
    product_price: float
    pickup_text: str


def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        wallet=os.getenv("TRC20_WALLET", "").strip(),
        product_name=os.getenv("PRODUCT_NAME", "Physical product"),
        product_price=float(os.getenv("PRODUCT_PRICE_USDT", "10.0")),
        pickup_text=os.getenv("PICKUP_TEXT", "Где забрать товар..."),
    )


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            product_name TEXT,
            amount_usdt REAL,
            status TEXT,
            created_at INTEGER
        )
    """)
    con.commit()
    con.close()


def create_order(user_id, username, product, amount):
    con = db()
    cur = con.execute(
        """
        INSERT INTO orders (user_id, username, product_name, amount_usdt, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
        """,
        (user_id, username, product, amount, int(time.time())),
    )
    con.commit()
    oid = cur.lastrowid
    con.close()
    return oid


def get_last_order(user_id):
    con = db()
    order = con.execute(
        "SELECT * FROM orders WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    con.close()
    return order


def mark_paid(order_id):
    con = db()
    con.execute(
        "UPDATE orders SET status='paid' WHERE id=?",
        (order_id,),
    )
    con.commit()
    con.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Купить", callback_data="buy")],
        [InlineKeyboardButton("✅ Я оплатил (тест)", callback_data="test_paid")]
    ])

    await update.message.reply_text(
        f"Товар: {settings.product_name}\nЦена: {settings.product_price} USDT",
        reply_markup=kb
    )


async def on_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user = q.from_user
    order_id = create_order(user.id, user.username, settings.product_name, settings.product_price)

    await q.message.reply_text(
        f"Заказ создан ✅\nOrder ID: {order_id}\n\n"
        f"Оплатите: {settings.product_price} USDT\n"
        f"(это тест, можно не платить)"
    )


async def test_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    order = get_last_order(q.from_user.id)

    if not order:
        await q.message.reply_text("Нет активного заказа")
        return

    mark_paid(order["id"])

    await q.message.reply_text(
        "ТЕСТОВАЯ ОПЛАТА ПРОШЛА ✅\n\n" + settings.pickup_text
    )


if __name__ == "__main__":
    settings = get_settings()
    init_db()

    request = HTTPXRequest(proxy=None)

    app = Application.builder().token(settings.bot_token).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_buy, pattern="^buy$"))
    app.add_handler(CallbackQueryHandler(test_paid, pattern="^test_paid$"))

    print("Bot is running...")
    app.run_polling()
