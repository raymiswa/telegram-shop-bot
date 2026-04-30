import json
import os
import sqlite3
import time
from typing import Dict, List

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

load_dotenv()

DB_PATH = "shop.db"
ADMIN_IDS = [8061201371:AAEHogHvhKiWYqjdTEt6QNl3RI8lohM4c4k]  # <-- ВСТАВЬ СВОЙ TELEGRAM ID
PICKUP_ADDRESS = "📍 Адрес получения: ул. Примерная, 10"

PRODUCTS: List[Dict] = [
    {"id": 1, "name": "Gold", "price_per_gram": 60, "description": "Золото 999", "photo_url": "https://picsum.photos/300"},
    {"id": 2, "name": "Silver", "price_per_gram": 1, "description": "Серебро 999", "photo_url": "https://picsum.photos/301"},
    {"id": 3, "name": "Platinum", "price_per_gram": 30, "description": "Платина", "photo_url": "https://picsum.photos/302"},
]

PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            grams INTEGER
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            items_json TEXT,
            total_amount REAL,
            status TEXT
        )
    """)
    con.commit()
    con.close()


def add_to_cart(user_id, product_id, grams):
    con = db()
    con.execute("INSERT INTO cart(user_id, product_id, grams) VALUES (?, ?, ?)", (user_id, product_id, grams))
    con.commit()
    con.close()


def get_cart(user_id):
    con = db()
    rows = con.execute("SELECT * FROM cart WHERE user_id=?", (user_id,)).fetchall()
    con.close()
    return rows


def clear_cart(user_id):
    con = db()
    con.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
    con.commit()
    con.close()


def create_order(user_id, username):
    rows = get_cart(user_id)
    if not rows:
        return None

    total = 0
    items = []

    for r in rows:
        product = PRODUCT_BY_ID[r["product_id"]]
        subtotal = r["grams"] * product["price_per_gram"]
        total += subtotal
        items.append({
            "name": product["name"],
            "grams": r["grams"],
            "subtotal": subtotal
        })

    con = db()
    cur = con.execute(
        "INSERT INTO orders(user_id, username, items_json, total_amount, status) VALUES (?, ?, ?, ?, 'pending')",
        (user_id, username, json.dumps(items), total)
    )
    order_id = cur.lastrowid
    con.commit()
    con.close()

    clear_cart(user_id)
    return order_id, total


def get_orders():
    con = db()
    rows = con.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    con.close()
    return rows


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Открыть магазин", callback_data="open_shop")],
        [InlineKeyboardButton("🧺 Корзина", callback_data="cart")]
    ])
    await update.message.reply_text("Добро пожаловать!", reply_markup=kb)


async def show_catalog(q):
    keyboard = [
        [InlineKeyboardButton(f"{p['name']} — ${p['price_per_gram']}/g", callback_data=f"product:{p['id']}")]
        for p in PRODUCTS
    ]
    await q.message.reply_text("Каталог:", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_product(q, product_id):
    p = PRODUCT_BY_ID[product_id]

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1g", callback_data=f"add:{product_id}:1"),
            InlineKeyboardButton("2g", callback_data=f"add:{product_id}:2"),
            InlineKeyboardButton("5g", callback_data=f"add:{product_id}:5"),
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="open_shop")]
    ])

    await q.message.reply_photo(p["photo_url"], caption=f"{p['name']}\n{p['description']}", reply_markup=kb)


async def show_cart(q, user_id):
    rows = get_cart(user_id)

    if not rows:
        await q.message.reply_text("Корзина пуста")
        return

    text = "🧺 Корзина:\n"
    total = 0

    for r in rows:
        p = PRODUCT_BY_ID[r["product_id"]]
        subtotal = r["grams"] * p["price_per_gram"]
        total += subtotal
        text += f"{p['name']} {r['grams']}g = ${subtotal}\n"

    text += f"\nИтого: ${total}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Оформить", callback_data="checkout")]
    ])

    await q.message.reply_text(text, reply_markup=kb)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    user_id = q.from_user.id

    if data == "open_shop":
        await show_catalog(q)

    elif data.startswith("product:"):
        pid = int(data.split(":")[1])
        await show_product(q, pid)

    elif data.startswith("add:"):
        _, pid, grams = data.split(":")
        add_to_cart(user_id, int(pid), int(grams))
        await q.message.reply_text("Добавлено в корзину")

    elif data == "cart":
        await show_cart(q, user_id)

    elif data == "checkout":
        res = create_order(user_id, q.from_user.username or "")
        if not res:
            await q.message.reply_text("Корзина пуста")
            return

        oid, total = res

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Я оплатил", callback_data=f"paid:{oid}")]
        ])

        await q.message.reply_text(f"Заказ #{oid}\nСумма: ${total}", reply_markup=kb)

    elif data.startswith("paid:"):
        oid = int(data.split(":")[1])
        await q.message.reply_text("Ожидайте подтверждения администратора")

    elif data == "orders":
        if user_id not in ADMIN_IDS:
            return

        rows = get_orders()
        for o in rows:
            await q.message.reply_text(f"#{o['id']} ${o['total_amount']} {o['status']}")


if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")

    init_db()

    request = HTTPXRequest(proxy=None)

    app = Application.builder().token(token).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))

    print("Bot is running...")
    app.run_polling()
