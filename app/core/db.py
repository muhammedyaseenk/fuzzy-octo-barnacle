# app/core/db.py
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# SQLAlchemy setup with optimized connection pooling
engine = create_async_engine(
    settings.POSTGRES_URL,
    echo=False,
    pool_size=50,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=30,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {"jit": "off"},
        "command_timeout": 60,
        "prepared_statement_cache_size": 500
    }
)
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
        min_size=10,
        max_size=50,
        max_inactive_connection_lifetime=300,
        command_timeout=60
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