from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from database.database import AsyncSessionLocal
from database.crud import (
    get_all_pickup_points, get_pickup_point, create_pickup_point,
    toggle_pickup_point, delete_pickup_point, count_active_orders_for_pickup,
)
from keyboards.admin import pickup_points_list_keyboard, pickup_point_actions_keyboard
from utils.decorators import admin_required

ADD_NAME, ADD_ADDRESS, ADD_COORDS, ADD_HOURS = range(4)


@admin_required
async def show_pickup_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        points = await get_all_pickup_points(session)
    text = f"📍 *Точки выдачи* ({len(points)}):"
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=pickup_points_list_keyboard(points))
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=pickup_points_list_keyboard(points))


@admin_required
async def show_pickup_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    point_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        point = await get_pickup_point(session, point_id)
    if not point:
        await query.edit_message_text("❌ Точка не найдена.")
        return
    text = (
        f"📍 *{point.name}*\n\n"
        f"Адрес: {point.address}\n"
        f"Координаты: {point.latitude}, {point.longitude}\n"
        f"Часы работы: {point.working_hours}\n"
        f"Статус: {'✅ Активна' if point.is_active else '❌ Неактивна'}"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=pickup_point_actions_keyboard(point.id, point.is_active),
    )


@admin_required
async def add_pickup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📍 *Новая точка выдачи*\n\nВведите название точки:",
        parse_mode="Markdown",
    )
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_pp_name"] = update.message.text.strip()
    await update.message.reply_text("Введите адрес точки:")
    return ADD_ADDRESS


async def add_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_pp_address"] = update.message.text.strip()
    await update.message.reply_text(
        "Отправьте геолокацию или введите координаты в формате:\n"
        "`55.7558,37.6173`",
        parse_mode="Markdown",
    )
    return ADD_COORDS


async def add_coords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        context.user_data["new_pp_lat"] = update.message.location.latitude
        context.user_data["new_pp_lon"] = update.message.location.longitude
    else:
        try:
            parts = update.message.text.strip().replace(" ", "").split(",")
            lat = float(parts[0])
            lon = float(parts[1])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError
            context.user_data["new_pp_lat"] = lat
            context.user_data["new_pp_lon"] = lon
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Неверный формат. Введите координаты:\n`55.7558,37.6173`",
                parse_mode="Markdown",
            )
            return ADD_COORDS

    await update.message.reply_text("Введите часы работы (например: 10:00-22:00):")
    return ADD_HOURS


async def add_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hours = update.message.text.strip()
    name = context.user_data.pop("new_pp_name", "")
    address = context.user_data.pop("new_pp_address", "")
    lat = context.user_data.pop("new_pp_lat", 0.0)
    lon = context.user_data.pop("new_pp_lon", 0.0)

    async with AsyncSessionLocal() as session:
        point = await create_pickup_point(session, name, address, lat, lon, hours)

    await update.message.reply_text(
        f"✅ Точка выдачи *{point.name}* добавлена!",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


@admin_required
async def toggle_pickup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    point_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        point = await toggle_pickup_point(session, point_id)
    if point:
        status = "активирована" if point.is_active else "деактивирована"
        await query.edit_message_text(
            f"✅ Точка {status}.",
            reply_markup=pickup_point_actions_keyboard(point.id, point.is_active),
        )


@admin_required
async def delete_pickup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    point_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        active_count = await count_active_orders_for_pickup(session, point_id)
        if active_count > 0:
            await query.answer(f"❌ Есть {active_count} активных заказов!", show_alert=True)
            return
        await delete_pickup_point(session, point_id)
    await query.edit_message_text("🗑 Точка выдачи удалена.")


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


def register(app):
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_pickup_start, pattern="^admin_add_pickup$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_address)],
            ADD_COORDS: [
                MessageHandler(filters.LOCATION, add_coords),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_coords),
            ],
            ADD_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_hours)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
        per_chat=True,
        per_user=True,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📍 Точки выдачи$"), show_pickup_points))
    app.add_handler(CallbackQueryHandler(show_pickup_points, pattern="^admin_pickup_points$"))
    app.add_handler(CallbackQueryHandler(show_pickup_detail, pattern=r"^admin_pickup:\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_pickup, pattern=r"^admin_toggle_pickup:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_pickup, pattern=r"^admin_delete_pickup:\d+$"))
