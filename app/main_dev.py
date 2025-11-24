# app/main_dev.py - Development version with graceful service handling
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.rate_limit import init_rate_limiter

from app.domains.identity import api as identity_api
from app.domains.onboarding import api as onboarding_api
from app.domains.profiles import api as profiles_api
from app.domains.moderation import api as moderation_api
from app.domains.matching import api as matching_api
from app.domains.chat import api_http as chat_http_api, api_ws as chat_ws_api
from app.domains.calls import api_ws as calls_ws_api
from app.domains.media import api as media_api
from app.domains.notifications import api as notifications_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - with error handling for development
    print("🚀 Starting Aurum Matrimony API...")
    
    try:
        from app.core.db import init_db, init_pg_pool
        await init_db()
        await init_pg_pool()
        print("✅ Database connected")
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("   Continue without database for API testing")
    
    try:
        from app.core.cache import init_redis
        await init_redis()
        print("✅ Redis connected")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("   Continue without Redis caching")
    
    try:
        from app.core.storage import ensure_bucket
        ensure_bucket()
        print("✅ MinIO storage ready")
    except Exception as e:
        print(f"⚠️  MinIO connection failed: {e}")
        print("   Continue without file storage")
    
    print("🎉 API server started successfully!")
    yield
    
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="Aurum Matrimony Platform",
    version="1.0.0",
    description="Premium matrimony platform with Kerala-first focus",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize rate limiter
init_rate_limiter(app)

# Mount routers
app.include_router(identity_api.router, prefix="/api/v1")
app.include_router(onboarding_api.router, prefix="/api/v1")
app.include_router(profiles_api.router, prefix="/api/v1")
app.include_router(moderation_api.router, prefix="/api/v1")
app.include_router(matching_api.router, prefix="/api/v1")
app.include_router(media_api.router, prefix="/api/v1")
app.include_router(notifications_api.router, prefix="/api/v1")
app.include_router(chat_http_api.router, prefix="/api/v1")
app.include_router(chat_ws_api.router)  # WebSocket, no prefix
app.include_router(calls_ws_api.router) # WebSocket, no prefix


@app.get("/")
async def root():
    return {
        "message": "Aurum Matrimony API", 
        "status": "ok",
        "version": "1.0.0",
        "note": "Some features may be limited without database/redis/minio"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "aurum-matrimony-api"
    }


@app.get("/setup-guide")
async def setup_guide():
    return {
        "message": "Aurum Matrimony Setup Guide",
        "steps": [
            "1. Install PostgreSQL and create 'aurum_db' database",
            "2. Install Redis server",
            "3. Install MinIO server",
            "4. Update .env file with correct connection strings",
            "5. Run: python init_db.py",
            "6. Run: uvicorn app.main:app --reload"
        ],
        "current_config": {
            "postgres_url": settings.POSTGRES_URL,
            "redis_host": f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            "minio_endpoint": settings.MINIO_ENDPOINT
        }
    }