import asyncio
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

DB_PATH = "shop.db"
USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


@dataclass
class Settings:
    bot_token: str
    wallet: str
    product_name: str
    product_price: float
    pickup_text: str
    check_interval: int


def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    wallet = os.getenv("TRC20_WALLET", "").strip()
    if not token or not wallet:
        raise RuntimeError("Set BOT_TOKEN and TRC20_WALLET in .env")

    return Settings(
        bot_token=token,
        wallet=wallet,
        product_name=os.getenv("PRODUCT_NAME", "Physical product"),
        product_price=float(os.getenv("PRODUCT_PRICE_USDT", "10.0")),
        pickup_text=os.getenv("PICKUP_TEXT", "Оплата получена. Где забрать: ..."),
        check_interval=int(os.getenv("CHECK_INTERVAL_SEC", "20")),
    )


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    con = db()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            product_name TEXT NOT NULL,
            amount_usdt REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            paid_at INTEGER,
            tx_id TEXT
        )
        """
    )
    con.commit()
    con.close()


def create_order(user_id: int, username: Optional[str], product: str, amount: float) -> int:
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


def get_pending_orders():
    con = db()
    rows = con.execute("SELECT * FROM orders WHERE status='pending'").fetchall()
    con.close()
    return rows


def mark_paid(order_id: int, tx_id: str) -> None:
    con = db()
    con.execute(
        "UPDATE orders SET status='paid', paid_at=?, tx_id=? WHERE id=?",
        (int(time.time()), tx_id, order_id),
    )
    con.commit()
    con.close()


def fetch_recent_usdt_trc20_transfers(wallet: str):
    url = "https://apilist.tronscanapi.com/api/token_trc20/transfers"
    params = {
        "relatedAddress": wallet,
        "contract_address": USDT_TRC20_CONTRACT,
        "limit": 50,
        "start": 0,
        "sort": "-timestamp",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json().get("token_transfers", [])
    return data


def transfer_matches_order(transfer: dict, order, settings) -> bool:
    to_addr = transfer.get("to_address", "")
    raw_amount = transfer.get("quant", "0")
    decimals = int(transfer.get("tokenInfo", {}).get("tokenDecimal", 6))
    amount = float(raw_amount) / (10 ** decimals)
    ts_ms = int(transfer.get("block_ts", 0))
    order_created_ms = int(order["created_at"]) * 1000

    return (
        to_addr == settings.wallet
        and amount >= float(order["amount_usdt"])
        and ts_ms >= order_created_ms
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛒 Купить", callback_data="buy")]]
    )
    await update.message.reply_text(
        f"Товар: {settings.product_name}\nЦена: {settings.product_price:.2f} USDT (TRC20)",
        reply_markup=kb,
    )


async def on_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    user = q.from_user

    order_id = create_order(user.id, user.username, settings.product_name, settings.product_price)

    await q.message.reply_text(
        "Заказ создан ✅\n"
        f"Order ID: {order_id}\n"
        f"Оплатите: {settings.product_price:.2f} USDT (TRC20)\n"
        f"Кошелек: `{settings.wallet}`\n\n"
        "После подтверждения транзакции вы получите сообщение с местом выдачи.",
        parse_mode="Markdown",
    )


async def payment_watcher(app: Application) -> None:
    while True:
        try:
            transfers = fetch_recent_usdt_trc20_transfers(settings.wallet)
            pending = get_pending_orders()
            for order in pending:
                for t in transfers:
                    if transfer_matches_order(t, order, settings):
                        tx_id = t.get("transaction_id", "unknown")
                        mark_paid(order["id"], tx_id)
                        await app.bot.send_message(
                            chat_id=order["user_id"],
                            text=(
                                "Оплата подтверждена ✅\n"
                                f"TX: {tx_id}\n\n"
                                f"{settings.pickup_text}"
                            ),
                        )
                        break
        except Exception as e:
            print("watcher error:", e)

        await asyncio.sleep(settings.check_interval)


async def post_init(app: Application) -> None:
    app.create_task(payment_watcher(app))


if __name__ == "__main__":
    settings = get_settings()
    init_db()

    app = Application.builder().token(settings.bot_token).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_buy, pattern="^buy$"))

    print("Bot is running...")
    app.run_polling()
