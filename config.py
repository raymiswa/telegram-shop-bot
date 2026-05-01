import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///shop.db")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
USDT_WALLET_ADDRESS = os.getenv("USDT_WALLET_ADDRESS", "")
USDT_RATE = float(os.getenv("USDT_RATE", "90.5"))
PAYMENT_TIMEOUT_MINUTES = int(os.getenv("PAYMENT_TIMEOUT_MINUTES", "30"))
PRODUCTS_PER_PAGE = 5
