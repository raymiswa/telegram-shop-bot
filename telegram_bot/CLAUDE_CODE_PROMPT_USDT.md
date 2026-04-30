# Промпт для Claude Code: Telegram Shop с USDT TRC20

Привет! Мне нужен **современный Telegram-магазин** с оплатой через USDT TRC20 и системой самовывоза.

## Что делать

Разработай полноценный интернет-магазин в Telegram используя:
- **Python 3.11+**
- **python-telegram-bot 21.0+**
- **SQLAlchemy 2.0** с **aiosqlite** (асинхронная SQLite)
- **qrcode** для генерации QR-кодов оплаты
- Модульная архитектура: handlers, database, keyboards, utils

## База данных

Создай SQLAlchemy модели для **11 таблиц**:

1. **users** (telegram_id, username, phone, created_at, is_blocked)
2. **categories** (name, emoji, description, is_active, position)
3. **products** (category_id FK, name, description, price, photo_url, stock_quantity, is_available, position)
4. **orders** (user_id FK, status, total_price, total_price_usdt, delivery_type, pickup_point_id FK, pickup_code, phone, comment, payment_method, payment_status, payment_address, payment_txid, created_at, paid_at, updated_at)
5. **order_items** (order_id FK, product_id FK, quantity, price, product_name)
6. **admins** (telegram_id, username, role)
7. **settings** (key, value, description)
8. **pickup_points** (name, address, latitude, longitude, working_hours, is_active, created_at)
9. **payment_wallets** (currency='usdt_trc20', address, is_active, created_at, last_used_at)
10. **payment_confirmations** (order_id FK, admin_id FK, txid, confirmed_at, notes)

**Статусы заказов:**
- `new` - Новый
- `awaiting_payment` - Ожидает оплаты (после выбора USDT)
- `paid` - Оплачен
- `ready` - Готов к выдаче
- `completed` - Выдан
- `cancelled` - Отменён

**delivery_type:** `pickup` (самовывоз) или `delivery` (доставка)

Используй **async/await** везде. Настрой подключение через `DATABASE_URL` из `.env`.

## Пользовательский функционал

### Главное меню:
- 🛒 Каталог товаров
- 🧺 Моя корзина (показывать количество)
- 📦 Мои заказы
- ℹ️ О магазине

### Каталог:
1. Категории
2. Товары (пагинация по 5)
3. Карточка товара: фото, описание, цена, остаток, кнопки [➖][кол-во][➕][🛒]

### Корзина:
- Список товаров с ценами
- Кнопки удаления
- Итоговая сумма
- [🗑 Очистить] [✅ Оформить]

### Оформление заказа (ConversationHandler):

**Шаг 1:** Выбор способа получения
- [📍 Самовывоз] [🚚 Доставка]

**Шаг 2:** Телефон (валидация: +7...)

**Шаг 3:** Комментарий (опционально, /skip)

**Шаг 4:** Выбор оплаты
- [💎 USDT TRC20] [💵 Наличные]

**Шаг 5а: Если выбран USDT TRC20:**

1. Конвертировать сумму в USDT (курс из settings: key='usdt_rate')
2. Взять адрес кошелька из `payment_wallets` (is_active=True)
3. Сгенерировать QR-код с адресом
4. Показать:
   ```
   💎 ОПЛАТА USDT TRC20
   
   Адрес кошелька:
   TXxxxxxxxxxxxxxxxxxxxxxxxxxx
   
   [QR-код картинкой]
   
   Сумма к оплате: 15.50 USDT
   
   ⏱ Осталось времени: 29:45
   
   Инструкция:
   1. Откройте ваш USDT кошелёк (TronLink, Trust Wallet и т.д.)
   2. Отправьте ТОЧНУЮ сумму на указанный адрес
   3. Используйте сеть TRC20 (Tron)
   4. После оплаты нажмите "Я оплатил"
   
   [✅ Я оплатил]  [❌ Отменить заказ]
   ```

5. Сохранить заказ со статусом `awaiting_payment`
6. Запустить таймер 30 минут (context.job_queue)
7. Если время истекло → статус `cancelled`, уведомить клиента

**Кнопка "✅ Я оплатил":**
- Отправить уведомление ВСЕМ админам:
  ```
  💰 ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ ОПЛАТЫ
  
  Заказ #123
  Клиент: @username (ID: 123456)
  Телефон: +7 999 123-45-67
  Сумма: 15.50 USDT
  Кошелёк: TXxxx...xxx
  Время создания: 2026-04-30 15:30
  
  [🔍 Проверить в Tronscan]
  [✅ Подтвердить оплату]
  [❌ Отклонить]
  ```

**Шаг 5б: Если наличные:**
- Сохранить заказ со статусом `new`, payment_status='pending'
- Показать подтверждение
- Уведомить админов

**Шаг 6: После подтверждения оплаты админом**

Клиент получает:
```
✅ ОПЛАТА ПОДТВЕРЖДЕНА!

📦 Ваш заказ #123 успешно оплачен

📍 ТОЧКА ВЫДАЧИ:
ТЦ "Центральный"
2 этаж, вход Б

🕐 Время работы: 
Пн-Вс: 10:00 - 22:00

📦 КОД ДЛЯ ПОЛУЧЕНИЯ:
#A1234

Инструкция:
Покажите этот код оператору в точке выдачи

[🗺 Показать на карте]
```

+ Отправить Telegram Location: `await context.bot.send_location(chat_id, latitude, longitude)`

### Мои заказы:
- Список с пагинацией
- Фильтры: Все / Ожидают оплаты / Оплачены / Готовы / Выданы
- Детали: состав, статус, адрес/точка выдачи, код (если есть)
- Кнопка "Отменить" для новых

## Админ-панель

### Главное меню:
- 📋 Заказы
- 💰 **Платежи (ожидают подтверждения)**
- 📦 Товары
- 📁 Категории
- 📍 **Точки выдачи**
- 💎 **Кошельки USDT**
- 👥 Пользователи
- 📊 Статистика
- 💬 Рассылка

### 💰 Платежи (ожидают подтверждения):

Список заказов со статусом `awaiting_payment`:
```
💰 ОЖИДАЮТ ПОДТВЕРЖДЕНИЯ

Заказ #123 - 15.50 USDT - @username
Заказ #124 - 8.20 USDT - @user2
...

[⬅️ Админ-панель]
```

**Клик на заказ → Детали:**
```
💰 ЗАКАЗ #123

👤 Клиент: @username (ID: 123456)
📱 Телефон: +7 999 123-45-67
💰 Сумма: 1500 ₽ (15.50 USDT)

📦 Состав:
- Товар 1 x2 = 800 ₽
- Товар 2 x1 = 700 ₽

💎 Адрес кошелька:
TXxxxxxxxxxxxxxxxxxxxxxxxxxx

⏱ Создан: 2026-04-30 15:30
⏱ Осталось: 18:25

[🔍 Проверить в Tronscan]
[✅ Подтвердить оплату]
[❌ Отклонить / Не оплачено]
```

**Кнопка "🔍 Проверить в Tronscan":**
- Открыть URL: `https://tronscan.org/#/address/{wallet_address}`
- Админ проверяет входящие транзакции вручную

**Кнопка "✅ Подтвердить оплату":**
1. Запросить TXID (опционально, /skip):
   ```
   Введите ID транзакции (TXID) или /skip
   ```
2. Обновить заказ:
   - status = 'paid'
   - payment_status = 'paid'
   - payment_txid = (введённый TXID)
   - paid_at = текущее время
3. Создать запись в `payment_confirmations`
4. Отправить клиенту сообщение с координатами (см. выше)
5. Уведомить админов: "✅ Оплата заказа #123 подтверждена админом @admin_username"

### 📍 Точки выдачи:

**Список:**
```
📍 ТОЧКИ ВЫДАЧИ

✅ ТЦ Центральный (активна)
   📍 Ленина 10 
   🕐 Пн-Вс 10:00-22:00
   📦 Активных заказов: 5

✅ ТЦ Гагаринский (активна)
   📍 Гагарина 50
   🕐 Пн-Пт 09:00-21:00
   📦 Активных заказов: 2

[➕ Добавить точку]
[⬅️ Админ-панель]
```

**Добавление точки (ConversationHandler):**
1. Ввести название: "ТЦ Центральный"
2. Ввести адрес: "г. Москва, ул. Ленина, д. 10, 2 этаж, вход Б"
3. Отправить геолокацию (Telegram Location) ИЛИ ввести координаты вручную: "55.7558,37.6173"
4. Ввести время работы: "Пн-Вс: 10:00 - 22:00"
5. Сохранить

**Редактирование:**
- Изменить название/адрес/координаты/время
- Вкл/Выкл точку

**Удаление:**
- Только если нет активных заказов (status != 'completed', 'cancelled')

### 💎 Кошельки USDT:

**Список:**
```
💎 КОШЕЛЬКИ USDT TRC20

✅ TXabc...xyz (активен)
   Последнее использование: 30.04.2026 15:30
   Транзакций: 15

❌ TXdef...123 (неактивен)
   Последнее использование: 28.04.2026
   Транзакций: 8

[➕ Добавить кошелёк]
[⬅️ Админ-панель]
```

**Добавление:**
1. Ввести адрес TRC20
2. Валидация: начинается с 'T', длина 34 символа
3. Сохранить с is_active=True

**Редактирование:**
- Вкл/Выкл кошелёк

### 📋 Управление заказами:

Фильтры:
- Все
- Новые (new)
- Ожидают оплаты (awaiting_payment)
- Оплачены (paid)
- Готовы к выдаче (ready)
- Выданы (completed)
- Отменённые (cancelled)

**Детали заказа:**
- Инфо о клиенте
- Состав
- Способ получения
- Статус оплаты (если USDT: адрес, TXID, ссылка на tronscan)
- **Действия:**
  - Изменить статус → ready / completed
  - Отменить

### 📊 Статистика:
- Всего заказов
- Общая выручка (₽ и USDT отдельно)
- Средний чек
- Топ-5 товаров
- График заказов за неделю

## Генерация QR-кода для оплаты

```python
import qrcode
from io import BytesIO

def generate_qr_code(wallet_address: str) -> BytesIO:
    """Генерация QR-кода с адресом кошелька"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(wallet_address)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# Использование:
qr_image = generate_qr_code(wallet_address)
await update.message.reply_photo(
    photo=qr_image,
    caption=f"💎 Адрес для оплаты:\n`{wallet_address}`\n\nСканируйте QR-код",
    parse_mode="Markdown"
)
```

## Генерация кода выдачи

```python
import random
import string

def generate_pickup_code() -> str:
    """Генерация уникального кода выдачи"""
    # Формат: #A1234
    letter = random.choice(string.ascii_uppercase)
    number = ''.join(random.choices(string.digits, k=4))
    return f"#{letter}{number}"
```

## Переменные окружения (.env)

```env
BOT_TOKEN=your_bot_token
DATABASE_URL=sqlite+aiosqlite:///shop.db
ADMIN_IDS=123456789,987654321

# Крипто
USDT_WALLET_ADDRESS=TXxxxxxxxxxxxxxxxxxxxxxxxxxx
USDT_RATE=90.5
PAYMENT_TIMEOUT_MINUTES=30

# Точка выдачи по умолчанию
DEFAULT_PICKUP_POINT_ID=1
```

## requirements.txt

```
python-telegram-bot==21.0
sqlalchemy==2.0.30
aiosqlite==0.20.0
python-dotenv==1.0.1
qrcode==7.4.2
Pillow==10.3.0
```

## Структура проекта

```
telegram-shop/
├── bot.py
├── config.py
├── requirements.txt
├── .env.example
├── database/
│   ├── models.py
│   ├── database.py
│   └── crud.py
├── handlers/
│   ├── user/
│   │   ├── start.py
│   │   ├── catalog.py
│   │   ├── cart.py
│   │   ├── orders.py          # Оформление заказа
│   │   └── payment.py         # Обработка USDT платежей
│   └── admin/
│       ├── panel.py
│       ├── orders.py
│       ├── payments.py        # Подтверждение оплат
│       ├── products.py
│       ├── pickup_points.py   # Управление точками выдачи
│       └── wallets.py         # Управление кошельками
├── keyboards/
│   ├── user.py
│   └── admin.py
└── utils/
    ├── decorators.py
    ├── validators.py
    ├── formatters.py
    ├── qr_generator.py        # Генерация QR-кодов
    └── payment_helpers.py     # Хелперы для платежей
```

## Важные детали

1. **Таймер оплаты:** Используй `context.job_queue.run_once()` для отмены заказа через 30 минут
2. **Уведомления:** Отправляй ВСЕМ админам из таблицы `admins`
3. **Валидация адреса TRC20:** `address.startswith('T') and len(address) == 34`
4. **Конвертация в USDT:** `total_usdt = total_rub / usdt_rate` (округление до 2 знаков)
5. **Координаты:** Храни как DECIMAL(10, 8) для latitude и DECIMAL(11, 8) для longitude
6. **Логирование:** Логируй все подтверждения оплаты в `payment_confirmations`

## Запуск

```python
# bot.py
import asyncio
from database.database import init_db
from handlers import register_all_handlers

async def main():
    await init_db()
    app = Application.builder().token(config.BOT_TOKEN).build()
    register_all_handlers(app)
    await app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
```

---

**Результат:** Production-ready магазин с USDT TRC20 оплатой, системой самовывоза с координатами и кодами выдачи, полной админ-панелью для управления платежами.

Начни с базы данных → CRUD → пользовательские хендлеры → платежи → админка.

Спасибо! 🚀
