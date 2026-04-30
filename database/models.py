from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Integer, Numeric, String, Text, Float
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(64))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)
    orders = relationship("Order", back_populates="user")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    emoji = Column(String(8), default="📦")
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    position = Column(Integer, default=0)
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    photo_url = Column(String(512))
    stock_quantity = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    position = Column(Integer, default=0)
    category = relationship("Category", back_populates="products")


class PickupPoint(Base):
    __tablename__ = "pickup_points"
    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    working_hours = Column(String(256))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    orders = relationship("Order", back_populates="pickup_point")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), default="new")
    total_price = Column(Numeric(10, 2), nullable=False)
    total_price_usdt = Column(Numeric(10, 2))
    delivery_type = Column(String(16), default="pickup")
    pickup_point_id = Column(Integer, ForeignKey("pickup_points.id"))
    pickup_code = Column(String(16))
    phone = Column(String(20))
    comment = Column(Text)
    payment_method = Column(String(16))
    payment_status = Column(String(16), default="pending")
    payment_address = Column(String(64))
    payment_txid = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="orders")
    pickup_point = relationship("PickupPoint", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    payment_confirmations = relationship("PaymentConfirmation", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    product_name = Column(String(256), nullable=False)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(64))
    role = Column(String(32), default="admin")


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)


class PaymentWallet(Base):
    __tablename__ = "payment_wallets"
    id = Column(Integer, primary_key=True)
    currency = Column(String(32), default="usdt_trc20")
    address = Column(String(64), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)


class PaymentConfirmation(Base):
    __tablename__ = "payment_confirmations"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    txid = Column(String(128))
    confirmed_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    order = relationship("Order", back_populates="payment_confirmations")
    admin = relationship("Admin")
