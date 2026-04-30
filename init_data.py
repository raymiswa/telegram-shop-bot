"""
Скрипт для добавления тестовых данных в базу
Запусти один раз, потом удали
"""
import asyncio
from database.database import async_session
from database.models import Category, Product, PickupPoint, PaymentWallet
from config import ADMIN_IDS

async def init_default_data():
    """Добавить тестовые категории, товары и точку выдачи"""
    
    async with async_session() as session:
        # Проверяем есть ли уже данные
        from sqlalchemy import select
        result = await session.execute(select(Category))
        if result.scalar_one_or_none():
            print("❌ Данные уже есть в базе. Скрипт не нужен.")
            return
        
        print("📦 Добавляю категории...")
        
        # Категории
        cat_pizza = Category(
            name="Пицца",
            emoji="🍕",
            description="Вкусная пицца",
            is_active=True,
            position=1
        )
        cat_burgers = Category(
            name="Бургеры", 
            emoji="🍔",
            description="Сочные бургеры",
            is_active=True,
            position=2
        )
        cat_drinks = Category(
            name="Напитки",
            emoji="🥤", 
            description="Освежающие напитки",
            is_active=True,
            position=3
        )
        
        session.add_all([cat_pizza, cat_burgers, cat_drinks])
        await session.flush()
        
        print("✅ Категории добавлены")
        print("📦 Добавляю товары...")
        
        # Товары
        products = [
            Product(
                category_id=cat_pizza.id,
                name="Пицца Маргарита",
                description="Томаты, моцарелла, базилик",
                price=450,
                photo_url="https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500",
                is_available=True,
                stock_quantity=10,
                position=1
            ),
            Product(
                category_id=cat_pizza.id,
                name="Пицца Пепперони",
                description="Пепперони, сыр, томатный соус",
                price=520,
                photo_url="https://images.unsplash.com/photo-1628840042765-356cda07504e?w=500",
                is_available=True,
                stock_quantity=8,
                position=2
            ),
            Product(
                category_id=cat_burgers.id,
                name="Чизбургер",
                description="Говядина, сыр чеддер, соус",
                price=350,
                photo_url="https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500",
                is_available=True,
                stock_quantity=15,
                position=1
            ),
            Product(
                category_id=cat_drinks.id,
                name="Кока-Кола 0.5л",
                description="Освежающий напиток",
                price=100,
                photo_url="https://images.unsplash.com/photo-1554866585-cd94860890b7?w=500",
                is_available=True,
                stock_quantity=20,
                position=1
            ),
        ]
        
        session.add_all(products)
        
        print("✅ Товары добавлены")
        print("📍 Добавляю точку выдачи...")
        
        # Точка выдачи
        pickup = PickupPoint(
            name="ТЦ Центральный",
            address="г. Москва, ул. Ленина, д. 10, 2 этаж, вход Б",
            latitude=55.7558,
            longitude=37.6173,
            working_hours="Пн-Вс: 10:00-22:00",
            is_active=True
        )
        
        session.add(pickup)
        
        print("✅ Точка выдачи добавлена")
        print("💎 Добавляю USDT кошелёк...")
        
        # USDT кошелёк (тестовый)
        wallet = PaymentWallet(
            currency="usdt_trc20",
            address="TXabc123def456ghi789jkl012mno345pqr",  # ЗАМЕНИ НА СВОЙ!
            is_active=True
        )
        
        session.add(wallet)
        
        await session.commit()
        
        print("\n🎉 ВСЕ ДАННЫЕ ДОБАВЛЕНЫ!")
        print(f"📦 Категорий: 3")
        print(f"📦 Товаров: 4")
        print(f"📍 Точек выдачи: 1")
        print(f"💎 USDT кошельков: 1")
        print(f"\n👨‍💼 Админы: {ADMIN_IDS}")
        print("\n✅ Теперь можешь тестировать магазин!")

if __name__ == "__main__":
    from database.database import init_db
    
    print("🚀 Инициализация базы данных...")
    asyncio.run(init_db())
    
    print("📦 Добавление тестовых данных...")
    asyncio.run(init_default_data())
