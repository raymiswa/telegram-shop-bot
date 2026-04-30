import json
import os
import sqlite3

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

load_dotenv()

DB_PATH = "shop.db"

PRODUCTS = [
    {"id": 1, "name": "Gold", "price": 60, "desc": "Золото 999", "img": "https://picsum.photos/300"},
    {"id": 2, "name": "Silver", "price": 1, "desc": "Серебро 999", "img": "https://picsum.photos/301"},
    {"id": 3, "name": "Platinum", "price": 30, "desc": "Платина", "img": "https://picsum.photos/302"},
]

PRODUCT_MAP = {p["id"]: p for p in PRODUCTS}


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            user_id INTEGER,
            product_id INTEGER,
            grams INTEGER
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            items TEXT,
            total REAL
        )
    """)
    con.commit()
    con.close()


def add_cart(user_id, product_id, grams):
    con = db()
    con.execute("INSERT INTO cart VALUES (?, ?, ?)", (user_id, product_id, grams))
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


def create_order(user_id):
    rows = get_cart(user_id)
    if not rows:
        return None

    total = 0
    items = []

    for r in rows:
        p = PRODUCT_MAP[r["product_id"]]
        subtotal = r["grams"] * p["price"]
        total += subtotal
        items.append(f"{p['name']} {r['grams']}g = ${subtotal}")

    con = db()
    cur = con.execute(
        "INSERT INTO orders(user_id, items, total) VALUES (?, ?, ?)",
        (user_id, json.dumps(items), total)
    )
    oid = cur.lastrowid
    con.commit()
    con.close()

    clear_cart(user_id)
    return oid, total


# ====== UI ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Открыть магазин", callback_data="shop")],
        [InlineKeyboardButton("🧺 Корзина", callback_data="cart")]
    ])

    await update.message.reply_text("Добро пожаловать!", reply_markup=kb)


async def show_shop(q):
    buttons = [
        [InlineKeyboardButton(f"{p['name']} — ${p['price']}/g", callback_data=f"p:{p['id']}")]
        for p in PRODUCTS
    ]

    await q.message.edit_text(
        "🛍 Каталог товаров:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_product(q, pid):
    p = PRODUCT_MAP[pid]

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1g", callback_data=f"add:{pid}:1"),
            InlineKeyboardButton("2g", callback_data=f"add:{pid}:2"),
            InlineKeyboardButton("5g", callback_data=f"add:{pid}:5"),
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="shop")]
    ])

    try:
        await q.message.delete()
    except:
        pass

    await q.message.reply_photo(
        p["img"],
        caption=f"{p['name']}\n{p['desc']}",
        reply_markup=kb
    )


async def show_cart(q, user_id):
    rows = get_cart(user_id)

    if not rows:
        await q.message.edit_text("Корзина пуста")
        return

    text = "🧺 Корзина:\n"
    total = 0

    for r in rows:
        p = PRODUCT_MAP[r["product_id"]]
        subtotal = r["grams"] * p["price"]
        total += subtotal
        text += f"{p['name']} {r['grams']}g = ${subtotal}\n"

    text += f"\nИтого: ${total}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Оформить", callback_data="checkout")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="shop")]
    ])

    await q.message.edit_text(text, reply_markup=kb)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    uid = q.from_user.id

    if data == "shop":
        await show_shop(q)

    elif data.startswith("p:"):
        await show_product(q, int(data.split(":")[1]))

    elif data.startswith("add:"):
        _, pid, grams = data.split(":")
        add_cart(uid, int(pid), int(grams))
        await q.message.reply_text("✅ Добавлено в корзину")

    elif data == "cart":
        await show_cart(q, uid)

    elif data == "checkout":
        res = create_order(uid)
        if not res:
            await q.message.edit_text("Корзина пуста")
            return

        oid, total = res

        await q.message.edit_text(f"Заказ #{oid}\nСумма: ${total}\n\nЖдите подтверждения")


# ====== RUN ======

if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")

    init_db()

    request = HTTPXRequest(proxy=None)

    app = Application.builder().token(token).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))

    print("Bot is running...")
    app.run_polling()
