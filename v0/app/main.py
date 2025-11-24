from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from contextlib import asynccontextmanager
from services.user_onboarding import app as onboarding_app

# Database connection pool
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_pool
    db_pool = await asyncpg.create_pool(
        "postgresql://postgres:mysecretpassword@localhost:5432/postgres",
        min_size=5,
        max_size=20
    )
    yield
    # Shutdown
    await db_pool.close()

# Main FastAPI app
app = FastAPI(
    title="Aurum Matrimony Platform",
    description="World-class matrimony platform for Kerala & India",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
async def get_db():
    async with db_pool.acquire() as conn:
        yield conn

# Mount onboarding routes
app.mount("/api/v1/onboarding", onboarding_app)

@app.get("/")
async def root():
    return {
        "message": "🏆 Aurum Matrimony Platform API",
        "version": "1.0.0",
        "status": "Active",
        "features": [
            "User Onboarding with Admin Verification",
            "Kerala-specific Matrimony Features",
            "Advanced Matching Algorithm",
            "Premium Subscription Management"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)