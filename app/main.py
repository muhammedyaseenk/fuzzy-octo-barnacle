# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import init_db, init_pg_pool
from app.core.storage import ensure_bucket
from app.core.rate_limit import init_rate_limiter
from app.core.cache import init_redis

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
    # Startup
    await init_db()       # SQLAlchemy engine + tables
    await init_pg_pool()  # asyncpg pool for onboarding/raw
    await init_redis()    # Redis connection
    ensure_bucket()       # Minio bucket
    yield
    # Shutdown
    # Add cleanup code here if needed


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
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "aurum-matrimony-api"
    }
