from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from database.database import AsyncSessionLocal
from database.crud import get_statistics
from utils.decorators import admin_required
from utils.formatters import fmt_price, fmt_usdt


@admin_required
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        stats = await get_statistics(session)

    top = "\n".join(
        f"  {i + 1}. {name} — {qty} шт."
        for i, (name, qty) in enumerate(stats["top_products"])
    ) or "  Нет данных"

    text = (
        f"📊 *Статистика магазина*\n\n"
        f"📦 Всего заказов: {stats['total_orders']}\n"
        f"📅 За последние 7 дней: {stats['week_orders']}\n\n"
        f"💰 Выручка (₽): {fmt_price(stats['revenue_rub'])}\n"
        f"💎 Выручка (USDT): {fmt_usdt(stats['revenue_usdt'])}\n"
        f"🧾 Средний чек: {fmt_price(stats['avg_order'])}\n\n"
        f"🏆 Топ-5 товаров:\n{top}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def register(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📊 Статистика$"), show_stats))
