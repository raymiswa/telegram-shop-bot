import random
import string
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from database.models import (
    User, Category, Product, Order, OrderItem,
    Admin, PaymentWallet, PaymentConfirmation, PickupPoint, Setting,
)
import config


def generate_pickup_code() -> str:
    letter = random.choice(string.ascii_uppercase)
    number = "".join(random.choices(string.digits, k=4))
    return f"#{letter}{number}"


# ─── Users ───────────────────────────────────────────────────────────────────

async def get_or_create_user(session, telegram_id: int, username: str | None, first_name: str) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name or "")
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        if user.username != username or user.first_name != (first_name or ""):
            user.username = username
            user.first_name = first_name or ""
            await session.commit()
    return user


async def get_all_users(session) -> list[User]:
    result = await session.execute(select(User).order_by(desc(User.created_at)))
    return result.scalars().all()


async def get_user_by_telegram_id(session, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


# ─── Categories ──────────────────────────────────────────────────────────────

async def get_active_categories(session) -> list[Category]:
    result = await session.execute(
        select(Category).where(Category.is_active == True).order_by(Category.position, Category.id)
    )
    return result.scalars().all()


async def get_all_categories(session) -> list[Category]:
    result = await session.execute(select(Category).order_by(Category.position, Category.id))
    return result.scalars().all()


async def get_category(session, category_id: int) -> Category | None:
    result = await session.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def create_category(session, name: str, emoji: str | None, description: str | None) -> Category:
    cat = Category(name=name, emoji=emoji, description=description)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def toggle_category(session, category_id: int) -> Category | None:
    cat = await get_category(session, category_id)
    if cat:
        cat.is_active = not cat.is_active
        await session.commit()
    return cat


async def delete_category(session, category_id: int):
    cat = await get_category(session, category_id)
    if cat:
        await session.delete(cat)
        await session.commit()


# ─── Products ─────────────────────────────────────────────────────────────────

async def get_products_by_category(session, category_id: int, page: int = 1, per_page: int = 5):
    offset = (page - 1) * per_page
    count_result = await session.execute(
        select(func.count(Product.id)).where(
            Product.category_id == category_id, Product.is_available == True
        )
    )
    total = count_result.scalar() or 0
    result = await session.execute(
        select(Product)
        .where(Product.category_id == category_id, Product.is_available == True)
        .order_by(Product.position, Product.id)
        .offset(offset)
        .limit(per_page)
    )
    products = result.scalars().all()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return products, total, total_pages


async def get_product(session, product_id: int) -> Product | None:
    result = await session.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_all_products(session) -> list[Product]:
    result = await session.execute(
        select(Product).options(selectinload(Product.category)).order_by(Product.id)
    )
    return result.scalars().all()


async def create_product(
    session, category_id: int, name: str, description: str | None,
    price: float, photo_url: str | None, stock_quantity: int
) -> Product:
    prod = Product(
        category_id=category_id, name=name, description=description,
        price=price, photo_url=photo_url, stock_quantity=stock_quantity,
    )
    session.add(prod)
    await session.commit()
    await session.refresh(prod)
    return prod


async def update_product(session, product_id: int, **kwargs) -> Product | None:
    prod = await get_product(session, product_id)
    if prod:
        for key, value in kwargs.items():
            setattr(prod, key, value)
        prod.updated_at = datetime.utcnow()
        await session.commit()
    return prod


async def toggle_product(session, product_id: int) -> Product | None:
    prod = await get_product(session, product_id)
    if prod:
        prod.is_available = not prod.is_available
        prod.updated_at = datetime.utcnow()
        await session.commit()
    return prod


async def delete_product(session, product_id: int):
    prod = await get_product(session, product_id)
    if prod:
        await session.delete(prod)
        await session.commit()


# ─── Pickup Points ────────────────────────────────────────────────────────────

async def get_active_pickup_points(session) -> list[PickupPoint]:
    result = await session.execute(
        select(PickupPoint).where(PickupPoint.is_active == True).order_by(PickupPoint.id)
    )
    return result.scalars().all()


async def get_all_pickup_points(session) -> list[PickupPoint]:
    result = await session.execute(select(PickupPoint).order_by(PickupPoint.id))
    return result.scalars().all()


async def get_pickup_point(session, point_id: int) -> PickupPoint | None:
    result = await session.execute(select(PickupPoint).where(PickupPoint.id == point_id))
    return result.scalar_one_or_none()


async def create_pickup_point(
    session, name: str, address: str, latitude: float, longitude: float, working_hours: str
) -> PickupPoint:
    point = PickupPoint(
        name=name, address=address, latitude=latitude,
        longitude=longitude, working_hours=working_hours,
    )
    session.add(point)
    await session.commit()
    await session.refresh(point)
    return point


async def toggle_pickup_point(session, point_id: int) -> PickupPoint | None:
    point = await get_pickup_point(session, point_id)
    if point:
        point.is_active = not point.is_active
        await session.commit()
    return point


async def delete_pickup_point(session, point_id: int):
    point = await get_pickup_point(session, point_id)
    if point:
        await session.delete(point)
        await session.commit()


async def count_active_orders_for_pickup(session, point_id: int) -> int:
    result = await session.execute(
        select(func.count(Order.id)).where(
            Order.pickup_point_id == point_id,
            Order.status.in_(["new", "awaiting_payment", "paid", "ready"]),
        )
    )
    return result.scalar() or 0


# ─── Wallets ──────────────────────────────────────────────────────────────────

async def get_active_wallets(session) -> list[PaymentWallet]:
    result = await session.execute(
        select(PaymentWallet).where(PaymentWallet.is_active == True).order_by(PaymentWallet.id)
    )
    return result.scalars().all()


async def get_all_wallets(session) -> list[PaymentWallet]:
    result = await session.execute(select(PaymentWallet).order_by(PaymentWallet.id))
    return result.scalars().all()


async def get_wallet(session, wallet_id: int) -> PaymentWallet | None:
    result = await session.execute(select(PaymentWallet).where(PaymentWallet.id == wallet_id))
    return result.scalar_one_or_none()


async def create_wallet(session, address: str) -> PaymentWallet:
    wallet = PaymentWallet(currency="usdt_trc20", address=address, is_active=True)
    session.add(wallet)
    await session.commit()
    await session.refresh(wallet)
    return wallet


async def toggle_wallet(session, wallet_id: int) -> PaymentWallet | None:
    wallet = await get_wallet(session, wallet_id)
    if wallet:
        wallet.is_active = not wallet.is_active
        await session.commit()
    return wallet


async def delete_wallet(session, wallet_id: int):
    wallet = await get_wallet(session, wallet_id)
    if wallet:
        await session.delete(wallet)
        await session.commit()


async def mark_wallet_used(session, wallet_id: int):
    wallet = await get_wallet(session, wallet_id)
    if wallet:
        wallet.last_used_at = datetime.utcnow()
        await session.commit()


# ─── Orders ───────────────────────────────────────────────────────────────────

async def create_order(
    session,
    user_id: int,
    cart: dict,
    phone: str,
    comment: str | None,
    payment_method: str,
    total_price: float,
    total_price_usdt: float | None,
    payment_address: str | None,
    pickup_point_id: int | None,
) -> Order:
    pickup_code = generate_pickup_code()
    order = Order(
        user_id=user_id,
        status="awaiting_payment" if payment_method == "usdt_trc20" else "new",
        total_price=total_price,
        total_price_usdt=total_price_usdt,
        delivery_type="pickup",
        pickup_point_id=pickup_point_id,
        pickup_code=pickup_code,
        phone=phone,
        comment=comment,
        payment_method=payment_method,
        payment_status="pending",
        payment_address=payment_address,
    )
    session.add(order)
    await session.flush()

    for product_id_str, item in cart.items():
        oi = OrderItem(
            order_id=order.id,
            product_id=int(product_id_str),
            quantity=item["qty"],
            price=item["price"],
            product_name=item["name"],
        )
        session.add(oi)

    await session.commit()
    await session.refresh(order)
    return order


async def get_order(session, order_id: int) -> Order | None:
    result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.user),
            selectinload(Order.pickup_point),
        )
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_user_orders(session, user_id: int) -> list[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(desc(Order.created_at))
    )
    return result.scalars().all()


async def get_awaiting_payment_orders(session) -> list[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.user))
        .where(Order.status == "awaiting_payment")
        .order_by(Order.created_at)
    )
    return result.scalars().all()


async def get_all_orders(session, status: str | None = None) -> list[Order]:
    q = select(Order).options(selectinload(Order.user), selectinload(Order.items))
    if status:
        q = q.where(Order.status == status)
    q = q.order_by(desc(Order.created_at))
    result = await session.execute(q)
    return result.scalars().all()


async def cancel_order(session, order_id: int) -> Order | None:
    order = await get_order(session, order_id)
    if order:
        order.status = "cancelled"
        order.updated_at = datetime.utcnow()
        await session.commit()
    return order


async def update_order_status(session, order_id: int, status: str) -> Order | None:
    order = await get_order(session, order_id)
    if order:
        order.status = status
        order.updated_at = datetime.utcnow()
        await session.commit()
    return order


async def confirm_payment(session, order_id: int, admin_telegram_id: int, txid: str | None) -> Order | None:
    order = await get_order(session, order_id)
    if not order:
        return None

    order.status = "paid"
    order.payment_status = "paid"
    order.payment_txid = txid
    order.paid_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    admin_result = await session.execute(
        select(Admin).where(Admin.telegram_id == admin_telegram_id)
    )
    admin = admin_result.scalar_one_or_none()

    if not admin:
        admin = Admin(telegram_id=admin_telegram_id, role="admin")
        session.add(admin)
        await session.flush()

    confirm = PaymentConfirmation(
        order_id=order.id,
        admin_id=admin.id,
        txid=txid,
    )
    session.add(confirm)
    await session.commit()
    await session.refresh(order)
    return order


# ─── Admins ───────────────────────────────────────────────────────────────────

async def get_all_admins(session) -> list[Admin]:
    result = await session.execute(select(Admin))
    return result.scalars().all()


async def get_admin_by_telegram_id(session, telegram_id: int) -> Admin | None:
    result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
    return result.scalar_one_or_none()


# ─── Statistics ───────────────────────────────────────────────────────────────

async def get_statistics(session) -> dict:
    total_orders_result = await session.execute(select(func.count(Order.id)))
    total_orders = total_orders_result.scalar() or 0

    revenue_rub_result = await session.execute(
        select(func.sum(Order.total_price)).where(Order.status.in_(["paid", "completed"]))
    )
    revenue_rub = float(revenue_rub_result.scalar() or 0)

    revenue_usdt_result = await session.execute(
        select(func.sum(Order.total_price_usdt)).where(
            Order.status.in_(["paid", "completed"]),
            Order.total_price_usdt.isnot(None),
        )
    )
    revenue_usdt = float(revenue_usdt_result.scalar() or 0)

    avg_order_result = await session.execute(
        select(func.avg(Order.total_price)).where(Order.status.in_(["paid", "completed"]))
    )
    avg_order = float(avg_order_result.scalar() or 0)

    week_ago = datetime.utcnow() - timedelta(days=7)
    week_orders_result = await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= week_ago)
    )
    week_orders = week_orders_result.scalar() or 0

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_today_result = await session.execute(
        select(func.count(User.id)).where(User.created_at >= today)
    )
    new_users_today = new_users_today_result.scalar() or 0

    top_products_result = await session.execute(
        select(OrderItem.product_name, func.sum(OrderItem.quantity).label("total_qty"))
        .group_by(OrderItem.product_name)
        .order_by(desc("total_qty"))
        .limit(5)
    )
    top_products = top_products_result.all()

    return {
        "total_orders": total_orders,
        "revenue_rub": revenue_rub,
        "revenue_usdt": revenue_usdt,
        "avg_order": avg_order,
        "week_orders": week_orders,
        "new_users_today": new_users_today,
        "top_products": top_products,
    }
