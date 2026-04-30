from telegram import Update
from telegram.ext import (
    ContextTypes, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_all_pickup_points, get_pickup_point, create_pickup_point,
    update_pickup_point, delete_pickup_point, count_active_orders_for_pickup
)
from keyboards.admin import pickup_points_list_keyboard, pickup_point_actions_keyboard
from utils.decorators import admin_required

ADD_NAME, ADD_ADDRESS, ADD_COORDS, ADD_HOURS = range(4)


@admin_required
async def show_pickup_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        points = await get_all_pickup_points(session)

    if not points:
        text = "📍 Точек выдачи нет."
    else:
        lines = []
        for p in points:
            status = "✅" if p.is_active else "❌"
            lines.append(f"{status} {p.name}\n   📍 {p.address}\n   ⏰ {p.working_hours or '—'}")
        text = "📍 *ТОЧКИ ВЫДАЧИ*\n\n" + "\n\n".join(lines)

    kb = pickup_points_list_keyboard(points)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def pickup_point_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    point_id = int(query.data.replace("admin_pp_", ""))
    async with AsyncSessionLocal() as session:
        pp = await get_pickup_point(session, point_id)
        active_orders = await count_active_orders_for_pickup(session, point_id)

    if not pp:
        await query.edit_message_text("Точка не найдена.")
        return

    text = (
        f"📍 *{pp.name}*\n\n"
        f"Адрес: {pp.address}\n"
        f"Координаты: {pp.latitude}, {pp.longitude}\n"
        f"Время работы: {pp.working_hours or '—'}\n"
        f"Статус: {'✅ Активна' if pp.is_active else '❌ Неактивна'}\n"
        f"📦 Активных заказов: {active_orders}"
    )
    await query.edit_message_text(text, reply_markup=pickup_point_actions_keyboard(pp), parse_mode="Markdown")


async def toggle_pickup_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    point_id = int(query.data.replace("admin_pp_toggle_", ""))
    async with AsyncSessionLocal() as session:
        pp = await get_pickup_point(session, point_id)
        await update_pickup_point(session, point_id, is_active=not pp.is_active)
        pp = await get_pickup_point(session, point_id)
    await query.edit_message_reply_markup(reply_markup=pickup_point_actions_keyboard(pp))


async def delete_pp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    point_id = int(query.data.replace("admin_pp_delete_", ""))
    async with AsyncSessionLocal() as session:
        count = await count_active_orders_for_pickup(session, point_id)
        if count > 0:
            await query.answer(f"Нельзя удалить: {count} активных заказов!", show_alert=True)
            return
        await delete_pickup_point(session, point_id)
    await query.edit_message_text("🗑 Точка выдачи удалена.")


async def add_pp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите название точки выдачи:")
    return ADD_NAME


async def add_pp_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_pp"] = {"name": update.message.text.strip()}
    await update.message.reply_text("Введите адрес точки:")
    return ADD_ADDRESS


async def add_pp_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_pp"]["address"] = update.message.text.strip()
    await update.message.reply_text(
        "Отправьте геолокацию (Telegram Location) или введите координаты вручную (например: 55.7558,37.6173):"
    )
    return ADD_COORDS


async def add_pp_coords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
    else:
        try:
            parts = update.message.text.strip().split(",")
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
        except Exception:
            await update.message.reply_text("Неверный формат. Введите: 55.7558,37.6173 или отправьте геолокацию:")
            return ADD_COORDS

    context.user_data["new_pp"]["latitude"] = lat
    context.user_data["new_pp"]["longitude"] = lon
    await update.message.reply_text("Введите время работы (например: Пн-Вс: 10:00 - 22:00):")
    return ADD_HOURS


async def add_pp_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_pp"]["working_hours"] = update.message.text.strip()
    data = context.user_data.pop("new_pp", {})
    async with AsyncSessionLocal() as session:
        pp = await create_pickup_point(session, **data)
    await update.message.reply_text(f"✅ Точка '{pp.name}' добавлена!")
    return ConversationHandler.END


def register(app):
    from telegram.ext import MessageHandler as MH, filters as F
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_pp_start, pattern="^admin_add_pp$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pp_name)],
            ADD_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pp_address)],
            ADD_COORDS: [
                MessageHandler(filters.LOCATION, add_pp_coords),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_pp_coords),
            ],
            ADD_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pp_hours)],
        },
        fallbacks=[],
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📍 Точки выдачи$"), show_pickup_points))
    app.add_handler(CallbackQueryHandler(show_pickup_points, pattern="^admin_pickup_points$"))
    app.add_handler(CallbackQueryHandler(pickup_point_detail, pattern=r"^admin_pp_\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_pickup_point, pattern=r"^admin_pp_toggle_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_pp_handler, pattern=r"^admin_pp_delete_\d+$"))
