# app/core/db.py
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# SQLAlchemy setup
engine = create_async_engine(settings.POSTGRES_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

# asyncpg pool for onboarding service
pg_pool = None


async def init_db():
    """Initialize SQLAlchemy database and create tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_pg_pool():
    """Initialize asyncpg connection pool for onboarding service"""
    global pg_pool
    pg_pool = await asyncpg.create_pool(
        settings.ONBOARDING_POSTGRES_URL,
        min_size=5,
        max_size=20
    )


async def get_db() -> AsyncSession:
    """Dependency to get SQLAlchemy async session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class AsyncPGConnection:
    """Context manager for asyncpg connections"""
    def __init__(self):
        if pg_pool is None:
            raise RuntimeError("PostgreSQL pool not initialized")
        self.pool = pg_pool
    
    async def __aenter__(self):
        self.connection = await self.pool.acquire()
        return self.connection
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.pool.release(self.connection)


def get_pg_connection():
    """Get asyncpg connection context manager"""
    return AsyncPGConnection()