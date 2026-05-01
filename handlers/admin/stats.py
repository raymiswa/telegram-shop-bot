from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from database.database import AsyncSessionLocal
from database.crud import get_statistics
from utils.decorators import admin_required


@admin_required
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        stats = await get_statistics(session)

    top = "\n".join(
        f"  {i + 1}. {name} — {qty} шт."
        for i, (name, qty) in enumerate(stats["top_products"])
    ) or "  нет данных"

    text = (
        "📊 *Статистика магазина*\n\n"
        f"📦 Всего заказов: *{stats['total_orders']}*\n"
        f"📅 За неделю: *{stats['week_orders']}*\n\n"
        f"💰 Выручка: *{stats['revenue_rub']:.0f}₽*\n"
        f"💎 Выручка USDT: *{stats['revenue_usdt']:.2f}*\n"
        f"🧾 Средний чек: *{stats['avg_order']:.0f}₽*\n\n"
        f"👤 Новых сегодня: *{stats['new_users_today']}*\n\n"
        f"🏆 Топ-5 товаров:\n{top}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def register(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📊 Статистика$"), show_stats))
