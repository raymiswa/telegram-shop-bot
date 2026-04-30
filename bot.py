import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

PRODUCTS = [
    {"id": 1, "name": "Gold", "price": 60},
    {"id": 2, "name": "Silver", "price": 1},
    {"id": 3, "name": "Platinum", "price": 30},
]

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
    ]
    await update.message.reply_text("Добро пожаловать", reply_markup=InlineKeyboardMarkup(kb))

# ===== CALLBACK =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    print("CLICK:", data)  # 👈 ДЛЯ ДЕБАГА

    # ===== МАГАЗИН =====
    if data == "shop":
        kb = []
        for p in PRODUCTS:
            kb.append([InlineKeyboardButton(f"{p['name']} — ${p['price']}", callback_data=f"p_{p['id']}")])

        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Каталог:",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ===== ТОВАР =====
    elif data.startswith("p_"):
        pid = int(data.split("_")[1])
        product = next(p for p in PRODUCTS if p["id"] == pid)

        kb = [
            [InlineKeyboardButton("Купить", callback_data=f"buy_{pid}")]
        ]

        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"{product['name']}\nЦена: ${product['price']}",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ===== ПОКУПКА =====
    elif data.startswith("buy_"):
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Заказ создан ✅"
        )

# ===== RUN =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

print("Bot started...")
app.run_polling()
