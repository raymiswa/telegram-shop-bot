from datetime import datetime


def fmt_price(amount) -> str:
    return f"{float(amount):,.2f} ₽".replace(",", " ")


def fmt_usdt(amount) -> str:
    return f"{float(amount):.2f} USDT"


def fmt_dt(dt: datetime) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


STATUS_LABELS = {
    "new": "🆕 Новый",
    "awaiting_payment": "⏳ Ожидает оплаты",
    "paid": "✅ Оплачен",
    "ready": "📦 Готов к выдаче",
    "completed": "✔️ Выдан",
    "cancelled": "❌ Отменён",
}


def fmt_status(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def fmt_order_short(order) -> str:
    return (
        f"📦 Заказ #{order.id} | {fmt_price(order.total_price)} | "
        f"{fmt_status(order.status)}"
    )
