# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import init_db, init_pg_pool, engine
from app.core.storage import ensure_bucket
from app.core.rate_limit import init_rate_limiter
from app.core.cache import init_redis
from app.core.socketio_server import sio
from app.core.resource_manager import resource_manager
from app.middleware.security import SecurityMiddleware
import asyncio

from app.domains.identity import api as identity_api
from app.domains.onboarding import api as onboarding_api
from app.domains.profiles import api as profiles_api
from app.domains.moderation import api as moderation_api
from app.domains.matching import api as matching_api
from app.domains.matching import api_optimized as matching_optimized_api
from app.domains.engagement import api as engagement_api
from app.domains.admin import api as admin_api
from app.domains.whatsapp import api as whatsapp_api
from app.domains.chat import api_http as chat_http_api, api_ws as chat_ws_api
from app.domains.calls import api_ws as calls_ws_api
from app.domains.media import api as media_api
from app.domains.notifications import api as notifications_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await init_pg_pool()
    await init_redis()
    ensure_bucket()
    
    # Start resource monitor
    monitor_task = asyncio.create_task(resource_manager.monitor_resources())
    
    yield
    
    # Shutdown
    monitor_task.cancel()
    await engine.dispose()
    from app.core.db import pg_pool
    if pg_pool:
        await pg_pool.close()


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

# Add security middleware
app.add_middleware(SecurityMiddleware)

# Mount routers
app.include_router(identity_api.router, prefix="/api/v1")
app.include_router(onboarding_api.router, prefix="/api/v1")
app.include_router(profiles_api.router, prefix="/api/v1")
app.include_router(moderation_api.router, prefix="/api/v1")
app.include_router(matching_api.router, prefix="/api/v1")
app.include_router(matching_optimized_api.router)
app.include_router(engagement_api.router, prefix="/api/v1")
app.include_router(admin_api.router, prefix="/api/v1")
app.include_router(whatsapp_api.router, prefix="/api/v1")
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
    stats = resource_manager.get_stats()
    return {
        "status": "healthy",
        "service": "aurum-matrimony-api",
        "resources": stats
    }

# Mount Socket.IO for WebSocket
from socketio import ASGIApp
socket_app = ASGIApp(sio, app)
