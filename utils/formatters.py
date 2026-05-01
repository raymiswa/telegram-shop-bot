from datetime import datetime

STATUS_LABELS = {
    "new": "🆕 Новый",
    "awaiting_payment": "⏳ Ожидает оплаты",
    "paid": "✅ Оплачен",
    "ready": "📦 Готов к выдаче",
    "completed": "✔️ Завершён",
    "cancelled": "❌ Отменён",
}

PAYMENT_STATUS_LABELS = {
    "pending": "⏳ Ожидает",
    "paid": "✅ Оплачен",
    "refunded": "↩️ Возврат",
}


def fmt_price(amount) -> str:
    return f"{float(amount):.0f}₽"


def fmt_usdt(amount) -> str:
    return f"{float(amount):.2f} USDT"


def fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def fmt_status(status: str) -> str:
    return STATUS_LABELS.get(status, status)
