import redis
from config.config import Config

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)

def cache_profile(user_id: int, profile: dict):
    r.set(f"profile:{user_id}", profile)

def get_cached_profile(user_id: int):
    return r.get(f"profile:{user_id}")

def cache_feed(key: str, user_ids: list):
    r.set(key, ",".join(map(str, user_ids)))

def get_feed(key: str):
    data = r.get(key)
    return data.split(",") if data else []
