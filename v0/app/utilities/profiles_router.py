from fastapi import APIRouter, Depends
from app.config.config import Config
import asyncpg
import redis

profiles_router = APIRouter()

# Redis setup
r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)

# Redis helpers
def cache_feed(key: str, user_ids: list):
    r.set(key, ",".join(map(str, user_ids)))

def get_feed(key: str):
    data = r.get(key)
    return data.split(",") if data else []

# Database dependency
async def get_db():
    conn = await asyncpg.connect(Config.POSTGRES_URL)
    try:
        yield conn
    finally:
        await conn.close()

# Profile feed route
@profiles_router.get("/feed/{gender}/{city}")
async def feed(gender: str, city: str, db=Depends(get_db)):
    key = f"feed:{gender}:{city}"
    cached = get_feed(key)
    if cached:
        return {"users": cached}

    rows = await db.fetch(
        "SELECT id FROM users WHERE gender=$1 AND city=$2 ORDER BY id DESC LIMIT 200",
        gender, city
    )
    user_ids = [str(r['id']) for r in rows]
    cache_feed(key, user_ids)
    return {"users": user_ids}
