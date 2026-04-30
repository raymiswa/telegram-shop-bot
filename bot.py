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
ADMIN_IDS = [111111111, 222222222]  # Укажите реальные Telegram user_id администраторов
PICKUP_ADDRESS = "📍 Адрес получения: ул. Примерная, 10. Напишите менеджеру по прибытии."

PRODUCTS: List[Dict] = [
    {
        "id": 1,
        "name": "Blue Dream",
        "price_per_gram": 15.0,
        "description": "Мягкий вкус, сбалансированный эффект, отлично для вечера.",
        "photo_url": "https://images.unsplash.com/photo-1536811145294-1408f4f8c734",
    },
    {
        "id": 2,
        "name": "OG Kush",
        "price_per_gram": 18.0,
        "description": "Классический плотный сорт с ярким ароматом.",
        "photo_url": "https://images.unsplash.com/photo-1603909223429-69bb7101f420",
    },
    {
        "id": 3,
        "name": "Lemon Haze",
        "price_per_gram": 17.5,
        "description": "Цитрусовый профиль и бодрящий характер.",
        "photo_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b",
    },
    {
        "id": 4,
        "name": "Pineapple Express",
        "price_per_gram": 19.0,
        "description": "Тропический аромат и приятное послевкусие.",
        "photo_url": "https://images.unsplash.com/photo-1528821128474-27f963b062bf",
    },
    {
        "id": 5,
        "name": "White Widow",
        "price_per_gram": 16.0,
        "description": "Легендарный сорт с насыщенным букетом.",
        "photo_url": "https://images.unsplash.com/photo-1542831371-d531d36971e6",
    },
    {
        "id": 6,
        "name": "Gorilla Glue",
        "price_per_gram": 20.0,
        "description": "Интенсивный аромат и плотные соцветия.",
        "photo_url": "https://images.unsplash.com/photo-1473448912268-2022ce9509d8",
    },
    {
        "id": 7,
        "name": "Amnesia",
        "price_per_gram": 14.5,
        "description": "Легкий цветочный профиль и ровный вкус.",
        "photo_url": "https://images.unsplash.com/photo-1464983953574-0892a716854b",
    },
    {
        "id": 8,
        "name": "Northern Lights",
        "price_per_gram": 21.0,
        "description": "Премиум-линейка с мягкой текстурой аромата.",
        "photo_url": "https://images.unsplash.com/photo-1501004318641-b39e6451bec6",
    },
    {
        "id": 9,
        "name": "Sour Diesel",
        "price_per_gram": 18.5,
        "description": "Яркий резкий аромат для ценителей.",
        "photo_url": "https://images.unsplash.com/photo-1492496913980-501348b61469",
    },
    {
        "id": 10,
        "name": "AK-47",
        "price_per_gram": 17.0,
        "description": "Сбалансированный сорт, стабильное качество.",
        "photo_url": "https://images.unsplash.com/photo-1503023345310-bd7c1de61c7d",
    },
]

PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            grams INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            items_json TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    con.commit()
    con.close()


def add_to_cart(user_id: int, product_id: int, grams: int):
    con = db()
    con.execute(
        "INSERT INTO cart(user_id, product_id, grams, created_at) VALUES(?, ?, ?, ?)",
        (user_id, product_id, grams, int(time.time())),
    )
    con.commit()
    con.close()


def get_cart_rows(user_id: int):
    con = db()
    rows = con.execute("SELECT * FROM cart WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    con.close()
    return rows


def clear_cart(user_id: int):
    con = db()
    con.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
    con.commit()
    con.close()


def build_cart_view(user_id: int):
    rows = get_cart_rows(user_id)
    if not rows:
        return "🧺 Ваша корзина пока пуста.", 0.0

    lines = ["🧺 <b>Ваша корзина</b>"]
    total = 0.0
    grouped: Dict[int, int] = {}
    for row in rows:
        grouped[row["product_id"]] = grouped.get(row["product_id"], 0) + row["grams"]

    for product_id, grams in grouped.items():
        product = PRODUCT_BY_ID.get(product_id)
        if not product:
            continue
        subtotal = grams * product["price_per_gram"]
        total += subtotal
        lines.append(f"• {product['name']} — {grams}g × ${product['price_per_gram']:.2f} = ${subtotal:.2f}")

    lines.append(f"\n💵 <b>Итого:</b> ${total:.2f}")
    return "\n".join(lines), total


def create_order_from_cart(user_id: int, username: str):
    rows = get_cart_rows(user_id)
    if not rows:
        return None

    grouped: Dict[int, int] = {}
    for row in rows:
        grouped[row["product_id"]] = grouped.get(row["product_id"], 0) + row["grams"]

    items = []
    total = 0.0
    for product_id, grams in grouped.items():
        product = PRODUCT_BY_ID.get(product_id)
        if not product:
            continue
        subtotal = grams * product["price_per_gram"]
        total += subtotal
        items.append(
            {
                "product_id": product_id,
                "name": product["name"],
                "grams": grams,
                "price_per_gram": product["price_per_gram"],
                "subtotal": subtotal,
            }
        )

    if not items:
        return None

    con = db()
    cur = con.execute(
        """
        INSERT INTO orders(user_id, username, items_json, total_amount, status, created_at)
        VALUES(?, ?, ?, ?, 'pending', ?)
        """,
        (user_id, username, json.dumps(items, ensure_ascii=False), total, int(time.time())),
    )
    order_id = cur.lastrowid
    con.commit()
    con.close()
    clear_cart(user_id)
    return order_id, total


def update_order_status(order_id: int, status: str):
    con = db()
    con.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    con.commit()
    con.close()


def get_order(order_id: int):
    con = db()
    row = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    con.close()
    return row


def get_all_orders():
    con = db()
    rows = con.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    con.close()
    return rows


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛍 <b>Добро пожаловать в наш магазин!</b>\n\n"
        "Здесь вы можете выбрать товар, добавить в корзину и оформить заказ в пару кликов."
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛒 Открыть магазин", callback_data="open_shop")], [InlineKeyboardButton("🧺 Корзина", callback_data="view_cart")]]
    )
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def show_catalog_message(message):
    keyboard = [[InlineKeyboardButton(f"{p['name']} — ${p['price_per_gram']:.2f}/g", callback_data=f"product:{p['id']}")] for p in PRODUCTS]
    keyboard.append([InlineKeyboardButton("🧺 Корзина", callback_data="view_cart")])
    await message.reply_text("📚 <b>Каталог товаров</b>\nВыберите позицию:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def show_product(query, product_id: int):
    product = PRODUCT_BY_ID.get(product_id)
    if not product:
        await query.message.reply_text("Товар не найден.")
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("1g", callback_data=f"add:{product_id}:1"),
                InlineKeyboardButton("2g", callback_data=f"add:{product_id}:2"),
                InlineKeyboardButton("5g", callback_data=f"add:{product_id}:5"),
            ],
            [InlineKeyboardButton("⬅️ К каталогу", callback_data="open_shop")],
            [InlineKeyboardButton("🧺 Корзина", callback_data="view_cart")],
        ]
    )

    caption = (
        f"🌿 <b>{product['name']}</b>\n"
        f"💵 Цена: <b>${product['price_per_gram']:.2f}</b> за грамм\n\n"
        f"{product['description']}\n\n"
        "Выберите количество:"
    )
    await query.message.reply_photo(photo=product["photo_url"], caption=caption, parse_mode="HTML", reply_markup=keyboard)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    user_id = q.from_user.id

    if data == "open_shop":
        await show_catalog_message(q.message)
        return

    if data.startswith("product:"):
        product_id = int(data.split(":")[1])
        await show_product(q, product_id)
        return

    if data.startswith("add:"):
        _, product_id_raw, grams_raw = data.split(":")
        product_id = int(product_id_raw)
        grams = int(grams_raw)
        add_to_cart(user_id, product_id, grams)
        product = PRODUCT_BY_ID[product_id]
        await q.message.reply_text(f"✅ Добавлено в корзину: {product['name']} — {grams}g")
        return

    if data == "view_cart":
        cart_text, total = build_cart_view(user_id)
        keyboard = [[InlineKeyboardButton("🧾 Оформить заказ", callback_data="checkout")]] if total > 0 else []
        keyboard.append([InlineKeyboardButton("🛍 Продолжить покупки", callback_data="open_shop")])
        await q.message.reply_text(cart_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "checkout":
        result = create_order_from_cart(user_id, q.from_user.username or "")
        if not result:
            await q.message.reply_text("Корзина пуста, нечего оформлять.")
            return
        order_id, total = result
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid:{order_id}")]]
        )
        await q.message.reply_text(
            f"🧾 Заказ <b>#{order_id}</b> создан.\n"
            f"💵 Сумма к оплате: <b>${total:.2f}</b>\n\n"
            "После оплаты нажмите кнопку ниже.",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    if data.startswith("paid:"):
        order_id = int(data.split(":")[1])
        order = get_order(order_id)
        if not order or order["user_id"] != user_id:
            await q.message.reply_text("Заказ не найден.")
            return
        update_order_status(order_id, "waiting_admin")
        await q.message.reply_text("⏳ Платеж отмечен. Ожидайте подтверждения администратора.")
        return

    if data.startswith("admin_confirm:"):
        if user_id not in ADMIN_IDS:
            await q.message.reply_text("У вас нет доступа к этому действию.")
            return
        order_id = int(data.split(":")[1])
        order = get_order(order_id)
        if not order:
            await q.message.reply_text("Заказ не найден.")
            return
        update_order_status(order_id, "paid")
        await q.message.reply_text(f"✅ Заказ #{order_id} подтвержден и отмечен как paid.")
        try:
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=f"✅ Ваш заказ #{order_id} подтвержден!\n{PICKUP_ADDRESS}",
            )
        except Exception:
            await q.message.reply_text("⚠️ Не удалось отправить сообщение клиенту (возможно, бот заблокирован).")


async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Доступ только для администраторов.")
        return

    rows = get_all_orders()
    if not rows:
        await update.message.reply_text("Заказов пока нет.")
        return

    for order in rows:
        items = json.loads(order["items_json"])
        items_text = "\n".join([f"• {it['name']} — {it['grams']}g (${it['subtotal']:.2f})" for it in items])
        text = (
            f"🧾 <b>Заказ #{order['id']}</b>\n"
            f"👤 user_id: <code>{order['user_id']}</code>\n"
            f"📌 status: <b>{order['status']}</b>\n"
            f"💰 total: <b>${order['total_amount']:.2f}</b>\n"
            f"Состав:\n{items_text}"
        )

        keyboard = []
        if order["status"] == "waiting_admin":
            keyboard.append([InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm:{order['id']}")])

        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)


if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Укажите BOT_TOKEN в .env")

    init_db()

    request = HTTPXRequest(proxy=None)
    app = Application.builder().token(token).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", orders))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot is running...")
    app.run_polling()
