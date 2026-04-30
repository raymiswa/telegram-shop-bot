from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from database.models import Base
import config

engine = create_async_engine(config.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_defaults()


async def _seed_defaults():
    from database.crud import get_setting, upsert_setting, get_active_wallets
    async with AsyncSessionLocal() as session:
        if not await get_setting(session, "usdt_rate"):
            await upsert_setting(session, "usdt_rate", str(config.USDT_RATE), "Курс USDT к рублю")
        if config.USDT_WALLET_ADDRESS and not await get_active_wallets(session):
            from database.models import PaymentWallet
            w = PaymentWallet(address=config.USDT_WALLET_ADDRESS)
            session.add(w)
            await session.commit()


def get_session() -> AsyncSession:
    return AsyncSessionLocal()
