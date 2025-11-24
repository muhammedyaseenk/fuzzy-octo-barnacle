# main_app.py
import io
import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import (
    FastAPI,
    APIRouter,
    HTTPException,
    Depends,
    status,
    Request,
    UploadFile,
    File,
)
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Text,
    TIMESTAMP,
    ForeignKey,
    func,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.future import select
from passlib.context import CryptContext
from jose import JWTError, jwt
import pyotp
import qrcode
from PIL import Image
import asyncpg
import redis
from minio import Minio
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import asyncio
from app.config.config import Config

# -------------------------
# CONFIG
# -------------------------
ENV = os.getenv("ENV", "dev")
POSTGRES_URL = os.getenv(
    "POSTGRES_URL", "postgresql://postgres:1234@localhost:5432/matrimony_db"
)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "profile-images")

RAM_TINY = "./images/tiny"
RAM_MEDIUM = "./images/medium"
os.makedirs(RAM_TINY, exist_ok=True)
os.makedirs(RAM_MEDIUM, exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_dev_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# -------------------------
# DATABASE INIT (Postgres or SQLite fallback)
# -------------------------
DB_TYPE = None
DATABASE_URL = None
engine = None
async_session = None
Base = declarative_base()


async def init_database():
    global DB_TYPE, DATABASE_URL, engine, async_session

    try:
        conn = await asyncpg.connect(POSTGRES_URL)
        await conn.close()
        DATABASE_URL = POSTGRES_URL
        DB_TYPE = "postgres"
        print("PostgreSQL connection OK")
    except Exception as e:
        print("PostgreSQL connection failed, falling back to SQLite:", e)
        DATABASE_URL = "sqlite+aiosqlite:///./dev_fallback.db"
        DB_TYPE = "sqlite"

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session


# -------------------------
# PASSWORD HASHING
# -------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# -------------------------
# MODELS
# -------------------------
class User(Base):
    __tablename__ = "users"

    # Always use String UUID for id; works on Postgres + SQLite
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uuid = Column(String, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(Text, unique=True)
    hashed_password = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    role = Column(String, default="user", nullable=False)
    mfa_secret = Column(String, default=lambda: pyotp.random_base32())
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    audit_logs = relationship("AuditLog", back_populates="user")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    action = Column(String)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    performed_by = Column(String)

    user = relationship("User", back_populates="audit_logs")


# -------------------------
# SCHEMAS
# -------------------------
class UserBase(BaseModel):
    email: Optional[EmailStr]
    phone: Optional[str]
    role: Optional[str] = "user"
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: str
    uuid: str
    created_at: datetime
    updated_at: datetime

    # Pydantic v2 replacement for orm_mode = True
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# -------------------------
# CRUD & HELPERS
# -------------------------
async def create_user(db: AsyncSession, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        phone=user.phone,
        hashed_password=hash_password(user.password),
        role=user.role,
        # Registered users start as inactive (awaiting approval)
        is_active=False,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def log_action(db: AsyncSession, user: User, action: str, performed_by: Optional[str] = None):
    log = AuditLog(user_id=user.id, action=action, performed_by=performed_by)
    db.add(log)
    await db.commit()


# -------------------------
# JWT & AUTH
# -------------------------
# tokenUrl should match actual route: /login/
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = await get_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not approved",
        )
    return user


def require_roles(*roles):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return current_user

    return role_checker


# -------------------------
# REDIS
# -------------------------
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def cache_profile(user_id: str, profile: dict):
    # Store JSON string
    r.set(f"profile:{user_id}", json.dumps(profile))


def get_cached_profile(user_id: str):
    data = r.get(f"profile:{user_id}")
    return json.loads(data) if data else None


def cache_feed(key: str, user_ids: list[str]):
    r.set(key, ",".join(map(str, user_ids)))


def get_feed(key: str):
    data = r.get(key)
    return data.split(",") if data else []


# -------------------------
# MINIO
# -------------------------
minio_client = Minio(
    MINIO_ENDPOINT,
    # access_key=MINIO_ACCESS_KEY,
    # secret_key=MINIO_SECRET_KEY,
    access_key=Config.MINIO_ROOT_USER,
    secret_key=Config.MINIO_ROOT_PASSWORD,
    secure=False,
)



def ensure_bucket():
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
        print(f"MinIO bucket '{MINIO_BUCKET}' is ready")
    except Exception as e:
        print(f"MinIO connection failed: {e}")
        print("Continuing without MinIO - image uploads will fail")


def upload_full_image(image_id: str, file_path: str):
    try:
        ensure_bucket()
        minio_client.fput_object(MINIO_BUCKET, f"{image_id}.jpg", file_path)
        return f"{image_id}.jpg"
    except Exception as e:
        print(f"Failed to upload to MinIO: {e}")
        return None


def generate_signed_url(image_id: str):
    try:
        return minio_client.presigned_get_object(MINIO_BUCKET, f"{image_id}.jpg")
    except Exception as e:
        print(f"Failed to generate signed URL: {e}")
        return None


# -------------------------
# IMAGE PROCESSING
# -------------------------
def process_image(upload_file: bytes):
    image_id = str(uuid.uuid4())
    temp_path = f"{image_id}.jpg"

    # Save uploaded file to temp
    with open(temp_path, "wb") as f:
        f.write(upload_file)

    img = Image.open(temp_path).convert("RGB")

    # Tiny
    tiny_path = os.path.join(RAM_TINY, f"{image_id}.webp")
    tiny_img = img.copy()
    tiny_img.thumbnail((200, 200))
    tiny_img.save(tiny_path, "WEBP", quality=40)

    # Medium
    medium_path = os.path.join(RAM_MEDIUM, f"{image_id}.webp")
    medium_img = img.copy()
    medium_img.thumbnail((800, 800))
    medium_img.save(medium_path, "WEBP", quality=70)

    # Full in Minio
    upload_full_image(image_id, temp_path)
    os.remove(temp_path)

    return {"image_id": image_id, "tiny": tiny_path, "medium": medium_path}


# -------------------------
# FASTAPI APP
# -------------------------
app = FastAPI(title="Unified Matrimony Backend")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routers
images_router = APIRouter()
profiles_router = APIRouter()


# -------------------------
# AUTH ENDPOINTS
# -------------------------
@app.post("/register/", response_model=UserRead)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    if await get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return await create_user(db, user)


@app.post("/login/", response_model=Token)
@limiter.limit("5/minute")
async def login(
    user: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    db_user = await get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not approved",
        )
    if db_user.mfa_secret:
        if not user.mfa_code or not pyotp.TOTP(db_user.mfa_secret).verify(
            user.mfa_code,
            valid_window=1,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code",
            )

    access_token = create_access_token({"sub": db_user.id, "role": db_user.role})
    refresh_token = create_refresh_token({"sub": db_user.id})

    await log_action(db, db_user, "login")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


@app.get("/mfa/qrcode")
async def generate_mfa_qr(current_user: User = Depends(get_current_user)):
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not initialized")

    uri = pyotp.totp.TOTP(current_user.mfa_secret).provisioning_uri(
        name=current_user.email,
        issuer_name="SecureApp",
    )

    buf = io.BytesIO()
    qrcode.make(uri).save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/refresh/", response_model=Token)
async def refresh_token(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = await get_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    access_token = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    await log_action(db, user, "refresh_token")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


# -------------------------
# IMAGE ENDPOINTS
# -------------------------
@images_router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    data = await file.read()
    result = process_image(data)
    return {
        "image_id": result["image_id"],
        "tiny_url": result["tiny"],
        "medium_url": result["medium"],
    }


# -------------------------
# PROFILE FEED ENDPOINT
# -------------------------
@profiles_router.get("/feed/{gender}/{city}")
async def feed(
    gender: str,
    city: str,
    db: AsyncSession = Depends(get_db),
):
    key = f"feed:{gender}:{city}"
    cached = get_feed(key)
    if cached:
        return {"users": cached}

    # Example query, adjust table columns / filters as needed
    rows = await db.execute(
        select(User).filter(User.role == gender).limit(200)
    )
    user_ids = [str(r.id) for r in rows.scalars()]

    cache_feed(key, user_ids)
    return {"users": user_ids}


# -------------------------
# ROUTER INCLUSION
# -------------------------
app.include_router(images_router, prefix="/images")
app.include_router(profiles_router, prefix="/profiles")


# -------------------------
# STARTUP EVENT
# -------------------------
@app.on_event("startup")
async def startup():
    await init_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    ensure_bucket()


@app.get("/ping")
async def ping():
    return {"status": "ok"}



# from fastapi import FastAPI
# from app.utilities.images_router import images_router
# from app.utilities.images_router import ensure_bucket
# from app.utilities.profiles_router import profiles_router
# from app.config.config import Config
# import asyncpg
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi import FastAPI

# app = FastAPI(
#     title="Aurum Matchmaking API",
#     version="1.0.0",
#     docs_url="/docs",
#     redoc_url="/redoc",
# )

# settings = Config()

# # # CORS for Flutter web + mobile (adjust in prod)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.CORS_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # # HTTP routers





# # Include routers
# app.include_router(profiles_router, prefix="/profiles")
# app.include_router(images_router, prefix="/images")
# # app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
# # app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
# # app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
# # app.include_router(matches.router, prefix="/api/v1/matches", tags=["matches"])
# # app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])
# # app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])

# # Startup events
# @app.on_event("startup")
# async def startup_event():
#     ensure_bucket()
#     try:
#         conn = await asyncpg.connect(Config.POSTGRES_URL)
#         await conn.close()
#         print("PostgreSQL connection OK")
#     except Exception as e:
#         print("PostgreSQL connection failed:", e)






























# # # app/main.py
# # from fastapi import FastAPI
# # from fastapi.middleware.cors import CORSMiddleware

# # from app.core.config import settings
# # from app.api.v1 import auth, users, profile, matches, chats, notifications
# # from app.realtime import chat_ws, notifications_ws

# # app = FastAPI(
# #     title="Aurum Matchmaking API",
# #     version="1.0.0",
# #     docs_url="/docs",
# #     redoc_url="/redoc",
# # )

# # # CORS for Flutter web + mobile (adjust in prod)
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=settings.CORS_ORIGINS,
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # # HTTP routers
# # app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
# # app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
# # app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
# # app.include_router(matches.router, prefix="/api/v1/matches", tags=["matches"])
# # app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])
# # app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])

# # # WebSockets (no prefix)
# # app.include_router(chat_ws.router, tags=["realtime-chat"])
# # app.include_router(notifications_ws.router, tags=["realtime-notifications"])
