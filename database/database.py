from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from database.models import Base, PaymentWallet
import config

engine = create_async_engine(config.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if config.USDT_WALLET_ADDRESS:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PaymentWallet).where(PaymentWallet.address == config.USDT_WALLET_ADDRESS)
            )
            if not result.scalar_one_or_none():
                wallet = PaymentWallet(
                    currency="usdt_trc20",
                    address=config.USDT_WALLET_ADDRESS,
                    is_active=True,
                )
                session.add(wallet)
                await session.commit()
