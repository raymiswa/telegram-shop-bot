from datetime import datetime
from typing import Optional
from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database.models import (
    User, Category, Product, Order, OrderItem,
    Admin, Setting, PickupPoint, PaymentWallet, PaymentConfirmation
)


# ── Users ──────────────────────────────────────────────────────────────────────

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif username and user.username != username:
        user.username = username
        await session.commit()
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


async def set_user_phone(session: AsyncSession, telegram_id: int, phone: str):
    await session.execute(update(User).where(User.telegram_id == telegram_id).values(phone=phone))
    await session.commit()


async def block_user(session: AsyncSession, telegram_id: int, blocked: bool):
    await session.execute(update(User).where(User.telegram_id == telegram_id).values(is_blocked=blocked))
    await session.commit()


# ── Categories ─────────────────────────────────────────────────────────────────

async def get_active_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(
        select(Category).where(Category.is_active == True).order_by(Category.position, Category.id)
    )
    return result.scalars().all()


async def get_all_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(select(Category).order_by(Category.position, Category.id))
    return result.scalars().all()


async def get_category(session: AsyncSession, category_id: int) -> Optional[Category]:
    result = await session.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def create_category(session: AsyncSession, name: str, emoji: str = "📦", description: str = None) -> Category:
    cat = Category(name=name, emoji=emoji, description=description)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def update_category(session: AsyncSession, category_id: int, **kwargs):
    await session.execute(update(Category).where(Category.id == category_id).values(**kwargs))
    await session.commit()


async def delete_category(session: AsyncSession, category_id: int):
    cat = await session.get(Category, category_id)
    if cat:
        await session.delete(cat)
        await session.commit()


# ── Products ───────────────────────────────────────────────────────────────────

async def get_products_by_category(session: AsyncSession, category_id: int, offset: int = 0, limit: int = 5):
    result = await session.execute(
        select(Product)
        .where(Product.category_id == category_id, Product.is_available == True)
        .order_by(Product.position, Product.id)
        .offset(offset).limit(limit)
    )
    return result.scalars().all()


async def count_products_by_category(session: AsyncSession, category_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(Product)
        .where(Product.category_id == category_id, Product.is_available == True)
    )
    return result.scalar()


async def get_all_products(session: AsyncSession) -> list[Product]:
    result = await session.execute(select(Product).order_by(Product.category_id, Product.position))
    return result.scalars().all()


async def get_product(session: AsyncSession, product_id: int) -> Optional[Product]:
    result = await session.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(session: AsyncSession, **kwargs) -> Product:
    p = Product(**kwargs)
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


async def update_product(session: AsyncSession, product_id: int, **kwargs):
    await session.execute(update(Product).where(Product.id == product_id).values(**kwargs))
    await session.commit()


async def delete_product(session: AsyncSession, product_id: int):
    p = await session.get(Product, product_id)
    if p:
        await session.delete(p)
        await session.commit()


# ── Cart (stored in bot context) ───────────────────────────────────────────────
# Cart is stored as context.user_data["cart"] = {product_id: quantity}

# ── Orders ─────────────────────────────────────────────────────────────────────

async def create_order(session: AsyncSession, user_id: int, items: dict, total_price: float,
                       total_price_usdt: float = None, delivery_type: str = "pickup",
                       pickup_point_id: int = None, phone: str = None,
                       comment: str = None, payment_method: str = "cash",
                       payment_address: str = None) -> Order:
    from utils.payment_helpers import generate_pickup_code
    order = Order(
        user_id=user_id,
        total_price=total_price,
        total_price_usdt=total_price_usdt,
        delivery_type=delivery_type,
        pickup_point_id=pickup_point_id,
        pickup_code=generate_pickup_code(),
        phone=phone,
        comment=comment,
        payment_method=payment_method,
        payment_status="pending",
        payment_address=payment_address,
        status="awaiting_payment" if payment_method == "usdt" else "new",
    )
    session.add(order)
    await session.flush()
    for product_id, qty in items.items():
        product = await get_product(session, int(product_id))
        if product:
            item = OrderItem(
                order_id=order.id,
                product_id=int(product_id),
                quantity=qty,
                price=product.price,
                product_name=product.name,
            )
            session.add(item)
    await session.commit()
    await session.refresh(order)
    return order


async def get_order(session: AsyncSession, order_id: int) -> Optional[Order]:
    result = await session.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.user),
                 selectinload(Order.pickup_point))
    )
    return result.scalar_one_or_none()


async def get_user_orders(session: AsyncSession, user_id: int, status_filter: str = None,
                          offset: int = 0, limit: int = 10) -> list[Order]:
    q = select(Order).where(Order.user_id == user_id)
    if status_filter:
        q = q.where(Order.status == status_filter)
    q = q.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(q)
    return result.scalars().all()


async def count_user_orders(session: AsyncSession, user_id: int, status_filter: str = None) -> int:
    q = select(func.count()).select_from(Order).where(Order.user_id == user_id)
    if status_filter:
        q = q.where(Order.status == status_filter)
    result = await session.execute(q)
    return result.scalar()


async def get_all_orders(session: AsyncSession, status_filter: str = None,
                         offset: int = 0, limit: int = 10) -> list[Order]:
    q = select(Order).options(selectinload(Order.user))
    if status_filter:
        q = q.where(Order.status == status_filter)
    q = q.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(q)
    return result.scalars().all()


async def count_all_orders(session: AsyncSession, status_filter: str = None) -> int:
    q = select(func.count()).select_from(Order)
    if status_filter:
        q = q.where(Order.status == status_filter)
    result = await session.execute(q)
    return result.scalar()


async def get_awaiting_payment_orders(session: AsyncSession) -> list[Order]:
    result = await session.execute(
        select(Order)
        .where(Order.status == "awaiting_payment")
        .options(selectinload(Order.user), selectinload(Order.items))
        .order_by(Order.created_at)
    )
    return result.scalars().all()


async def update_order_status(session: AsyncSession, order_id: int, status: str, **kwargs):
    values = {"status": status, "updated_at": datetime.utcnow(), **kwargs}
    await session.execute(update(Order).where(Order.id == order_id).values(**values))
    await session.commit()


async def confirm_payment(session: AsyncSession, order_id: int, admin_id: int, txid: str = None) -> Order:
    await session.execute(
        update(Order).where(Order.id == order_id).values(
            status="paid", payment_status="paid",
            payment_txid=txid, paid_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    )
    admin = await session.execute(select(Admin).where(Admin.telegram_id == admin_id))
    admin_obj = admin.scalar_one_or_none()
    conf = PaymentConfirmation(
        order_id=order_id,
        admin_id=admin_obj.id if admin_obj else None,
        txid=txid,
    )
    session.add(conf)
    await session.commit()
    return await get_order(session, order_id)


# ── Pickup Points ──────────────────────────────────────────────────────────────

async def get_active_pickup_points(session: AsyncSession) -> list[PickupPoint]:
    result = await session.execute(
        select(PickupPoint).where(PickupPoint.is_active == True).order_by(PickupPoint.id)
    )
    return result.scalars().all()


async def get_all_pickup_points(session: AsyncSession) -> list[PickupPoint]:
    result = await session.execute(select(PickupPoint).order_by(PickupPoint.id))
    return result.scalars().all()


async def get_pickup_point(session: AsyncSession, point_id: int) -> Optional[PickupPoint]:
    return await session.get(PickupPoint, point_id)


async def create_pickup_point(session: AsyncSession, **kwargs) -> PickupPoint:
    pp = PickupPoint(**kwargs)
    session.add(pp)
    await session.commit()
    await session.refresh(pp)
    return pp


async def update_pickup_point(session: AsyncSession, point_id: int, **kwargs):
    await session.execute(update(PickupPoint).where(PickupPoint.id == point_id).values(**kwargs))
    await session.commit()


async def delete_pickup_point(session: AsyncSession, point_id: int):
    pp = await session.get(PickupPoint, point_id)
    if pp:
        await session.delete(pp)
        await session.commit()


async def count_active_orders_for_pickup(session: AsyncSession, point_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(Order)
        .where(Order.pickup_point_id == point_id,
               Order.status.not_in(["completed", "cancelled"]))
    )
    return result.scalar()


# ── Wallets ────────────────────────────────────────────────────────────────────

async def get_active_wallets(session: AsyncSession) -> list[PaymentWallet]:
    result = await session.execute(
        select(PaymentWallet).where(PaymentWallet.is_active == True).order_by(PaymentWallet.id)
    )
    return result.scalars().all()


async def get_all_wallets(session: AsyncSession) -> list[PaymentWallet]:
    result = await session.execute(select(PaymentWallet).order_by(PaymentWallet.id))
    return result.scalars().all()


async def create_wallet(session: AsyncSession, address: str) -> PaymentWallet:
    w = PaymentWallet(address=address)
    session.add(w)
    await session.commit()
    await session.refresh(w)
    return w


async def update_wallet(session: AsyncSession, wallet_id: int, **kwargs):
    await session.execute(update(PaymentWallet).where(PaymentWallet.id == wallet_id).values(**kwargs))
    await session.commit()


async def mark_wallet_used(session: AsyncSession, wallet_id: int):
    await session.execute(
        update(PaymentWallet).where(PaymentWallet.id == wallet_id)
        .values(last_used_at=datetime.utcnow())
    )
    await session.commit()


async def count_wallet_transactions(session: AsyncSession, wallet_address: str) -> int:
    result = await session.execute(
        select(func.count()).select_from(Order)
        .where(Order.payment_address == wallet_address)
    )
    return result.scalar()


# ── Settings ───────────────────────────────────────────────────────────────────

async def get_setting(session: AsyncSession, key: str) -> Optional[str]:
    result = await session.execute(select(Setting).where(Setting.key == key))
    s = result.scalar_one_or_none()
    return s.value if s else None


async def upsert_setting(session: AsyncSession, key: str, value: str, description: str = None):
    result = await session.execute(select(Setting).where(Setting.key == key))
    s = result.scalar_one_or_none()
    if s:
        s.value = value
    else:
        s = Setting(key=key, value=value, description=description)
        session.add(s)
    await session.commit()


# ── Admins ─────────────────────────────────────────────────────────────────────

async def get_all_admins(session: AsyncSession) -> list[Admin]:
    result = await session.execute(select(Admin))
    return result.scalars().all()


async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
    return result.scalar_one_or_none() is not None


async def add_admin(session: AsyncSession, telegram_id: int, username: str = None, role: str = "admin") -> Admin:
    a = Admin(telegram_id=telegram_id, username=username, role=role)
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


# ── Statistics ─────────────────────────────────────────────────────────────────

async def get_statistics(session: AsyncSession) -> dict:
    total_orders = (await session.execute(select(func.count()).select_from(Order))).scalar()
    revenue_rub = (await session.execute(
        select(func.sum(Order.total_price)).where(Order.status.in_(["paid", "ready", "completed"]))
    )).scalar() or 0
    revenue_usdt = (await session.execute(
        select(func.sum(Order.total_price_usdt))
        .where(Order.status.in_(["paid", "ready", "completed"]), Order.payment_method == "usdt")
    )).scalar() or 0
    avg_order = (await session.execute(
        select(func.avg(Order.total_price)).where(Order.status.in_(["paid", "ready", "completed"]))
    )).scalar() or 0

    top_products = (await session.execute(
        select(OrderItem.product_name, func.sum(OrderItem.quantity).label("total_qty"))
        .group_by(OrderItem.product_name)
        .order_by(desc("total_qty"))
        .limit(5)
    )).all()

    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_orders = (await session.execute(
        select(func.count()).select_from(Order).where(Order.created_at >= week_ago)
    )).scalar()

    return {
        "total_orders": total_orders,
        "revenue_rub": float(revenue_rub),
        "revenue_usdt": float(revenue_usdt),
        "avg_order": float(avg_order),
        "top_products": top_products,
        "week_orders": week_orders,
    }
