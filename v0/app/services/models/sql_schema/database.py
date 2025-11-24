import asyncpg
from config.config import Config

async def get_db():
    conn = await asyncpg.connect(Config.POSTGRES_URL)
    try:
        yield conn
    finally:
        await conn.close()
