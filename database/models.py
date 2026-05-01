from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean,
    Numeric, DateTime, ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False, default="")
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)
    orders = relationship("Order", back_populates="user")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    emoji = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    photo_url = Column(String, nullable=True)
    is_available = Column(Boolean, default=True)
    stock_quantity = Column(Integer, default=0)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")


class PickupPoint(Base):
    __tablename__ = "pickup_points"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)
    working_hours = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    orders = relationship("Order", back_populates="pickup_point")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="new")
    total_price = Column(Numeric(10, 2), nullable=False)
    total_price_usdt = Column(Numeric(10, 2), nullable=True)
    delivery_type = Column(String, default="pickup")
    pickup_point_id = Column(Integer, ForeignKey("pickup_points.id"), nullable=True)
    pickup_code = Column(String, nullable=True)
    phone = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    payment_method = Column(String, nullable=False)
    payment_status = Column(String, default="pending")
    payment_address = Column(String, nullable=True)
    payment_txid = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="orders")
    pickup_point = relationship("PickupPoint", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    confirmations = relationship("PaymentConfirmation", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    product_name = Column(String, nullable=False)
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    role = Column(String, default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmations = relationship("PaymentConfirmation", back_populates="admin")


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)


class PaymentWallet(Base):
    __tablename__ = "payment_wallets"
    id = Column(Integer, primary_key=True)
    currency = Column(String, default="usdt_trc20")
    address = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)


class PaymentConfirmation(Base):
    __tablename__ = "payment_confirmations"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    txid = Column(String, nullable=True)
    confirmed_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    order = relationship("Order", back_populates="confirmations")
    admin = relationship("Admin", back_populates="confirmations")
