from fastapi import APIRouter, Depends
from services.models.database import get_db
from services.models.redis_caching.redis_cache import get_feed, cache_feed


router = APIRouter()

@router.get("/feed/{gender}/{city}")
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
