# main_app.py
import io
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP, ForeignKey, func
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
    id = Column(String if DB_TYPE == "sqlite" else "BIGINT", primary_key=True, default=lambda: str(uuid.uuid4()))
    uuid = Column(String, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(Text, unique=True)
    hashed_password = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    role = Column(String, default='user', nullable=False)
    mfa_secret = Column(String, default=lambda: pyotp.random_base32())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    audit_logs = relationship("AuditLog", back_populates="user")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String if DB_TYPE == "sqlite" else "BIGINT", primary_key=True, default=lambda: str(uuid.uuid4()))
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

    class Config:
        orm_mode = True


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
        is_active=False
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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = await get_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not approved")
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


def cache_profile(user_id: int, profile: dict):
    r.set(f"profile:{user_id}", profile)


def get_cached_profile(user_id: int):
    return r.get(f"profile:{user_id}")


def cache_feed(key: str, user_ids: list):
    r.set(key, ",".join(map(str, user_ids)))


def get_feed(key: str):
    data = r.get(key)
    return data.split(",") if data else []


# -------------------------
# MINIO
# -------------------------
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)


def ensure_bucket():
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)


def upload_full_image(image_id: str, file_path: str):
    ensure_bucket()
    minio_client.fput_object(MINIO_BUCKET, f"{image_id}.jpg", file_path)
    return f"{image_id}.jpg"


def generate_signed_url(image_id: str):
    return minio_client.presigned_get_object(MINIO_BUCKET, f"{image_id}.jpg")


# -------------------------
# IMAGE PROCESSING
# -------------------------
def process_image(upload_file: bytes):
    image_id = str(uuid.uuid4())
    temp_path = f"{image_id}.jpg"
    with open(temp_path, "wb") as f:
        f.write(upload_file)
    img = Image.open(temp_path).convert("RGB")
    tiny_path = os.path.join(RAM_TINY, f"{image_id}.webp")
    medium_path = os.path.join(RAM_MEDIUM, f"{image_id}.webp")
    tiny_img = img.copy()
    tiny_img.thumbnail((200, 200))
    tiny_img.save(tiny_path, "WEBP", quality=40)
    medium_img = img.copy()
    medium_img.thumbnail((800, 800))
    medium_img.save(medium_path, "WEBP", quality=70)
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
async def login(user: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not db_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not approved")
    if db_user.mfa_secret:
        if not user.mfa_code or not pyotp.TOTP(db_user.mfa_secret).verify(user.mfa_code, valid_window=1):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
    access_token = create_access_token({"sub": db_user.id, "role": db_user.role})
    refresh_token = create_refresh_token({"sub": db_user.id})
    await log_action(db, db_user, "login")
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@app.get("/mfa/qrcode")
async def generate_mfa_qr(current_user: User = Depends(get_current_user)):
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not initialized")
    uri = pyotp.totp.TOTP(current_user.mfa_secret).provisioning_uri(
        name=current_user.email, issuer_name="SecureApp"
    )
    buf = io.BytesIO()
    qrcode.make(uri).save(buf, format='PNG')
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/refresh/", response_model=Token)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = await get_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    access_token = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})
    await log_action(db, user, "refresh_token")
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


# -------------------------
# IMAGE ENDPOINTS
# -------------------------
@images_router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    data = await file.read()
    result = process_image(data)
    return {"image_id": result["image_id"], "tiny_url": result["tiny"], "medium_url": result["medium"]}


# -------------------------
# PROFILE FEED ENDPOINT
# -------------------------
@profiles_router.get("/feed/{gender}/{city}")
async def feed(gender: str, city: str, db=Depends(get_db)):
    key = f"feed:{gender}:{city}"
    cached = get_feed(key)
    if cached:
        return {"users": cached}
    # Example query, adjust table columns as needed
    rows = await db.execute(select(User).filter(User.role == gender).limit(200))
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


# # main_app.py
# import io
# import os
# import uuid
# from datetime import datetime, timedelta
# from typing import Optional
# from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, UploadFile, File
# from fastapi.responses import StreamingResponse
# from fastapi.security import OAuth2PasswordBearer
# from pydantic import BaseModel, EmailStr
# from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP, ForeignKey
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import declarative_base, sessionmaker, relationship
# from sqlalchemy.sql import func
# from sqlalchemy.future import select
# from passlib.context import CryptContext
# from jose import JWTError, jwt
# import pyotp
# import qrcode
# from PIL import Image
# import asyncpg
# import redis
# from minio import Minio
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded

# # -------------------------
# # CONFIG
# # -------------------------
# ENV = os.getenv("ENV", "dev")
# DATABASE_URL = os.getenv("DATABASE_URL") if ENV == "prod" else "sqlite+aiosqlite:///./dev.db"

# POSTGRES_URL = os.getenv(
#     "POSTGRES_URL", "postgresql://postgres:1234@localhost:5432/matrimony_db"
# )
# REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
# REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# MINIO_ENDPOINT = "localhost:9000"
# MINIO_ACCESS_KEY = "minioadmin"
# MINIO_SECRET_KEY = "minioadmin"
# MINIO_BUCKET = "profile-images"

# RAM_TINY = "./images/tiny"
# RAM_MEDIUM = "./images/medium"
# os.makedirs(RAM_TINY, exist_ok=True)
# os.makedirs(RAM_MEDIUM, exist_ok=True)

# SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_dev_key")
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 15
# REFRESH_TOKEN_EXPIRE_DAYS = 7

# # -------------------------
# # DATABASE (SQLAlchemy async for users)
# # -------------------------
# engine = create_async_engine(DATABASE_URL, echo=False)
# async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
# Base = declarative_base()

# async def get_db():
#     async with async_session() as session:
#         yield session

# # -------------------------
# # PASSWORD HASHING
# # -------------------------
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)
# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)

# # -------------------------
# # USER MODELS
# # -------------------------
# class User(Base):
#     __tablename__ = "users"
#     id = Column(String if "sqlite" in DATABASE_URL else "BIGINT", primary_key=True, default=lambda: str(uuid.uuid4()))
#     uuid = Column(String, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
#     email = Column(String, unique=True, nullable=False)
#     phone = Column(Text, unique=True)
#     hashed_password = Column(Text, nullable=False)
#     is_active = Column(Boolean, default=False, nullable=False)
#     role = Column(String, default='user', nullable=False)
#     mfa_secret = Column(String, default=lambda: pyotp.random_base32())
#     created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
#     updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
#     audit_logs = relationship("AuditLog", back_populates="user")

# class AuditLog(Base):
#     __tablename__ = "audit_logs"
#     id = Column(String if "sqlite" in DATABASE_URL else "BIGINT", primary_key=True, default=lambda: str(uuid.uuid4()))
#     user_id = Column(String, ForeignKey("users.id"))
#     action = Column(String)
#     timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
#     performed_by = Column(String)
#     user = relationship("User", back_populates="audit_logs")

# # -------------------------
# # USER SCHEMAS
# # -------------------------
# class UserBase(BaseModel):
#     email: Optional[EmailStr]
#     phone: Optional[str]
#     role: Optional[str] = "user"
#     is_active: Optional[bool] = True

# class UserCreate(UserBase):
#     password: str

# class UserRead(UserBase):
#     id: str
#     uuid: str
#     created_at: datetime
#     updated_at: datetime
#     class Config:
#         orm_mode = True

# class UserLogin(BaseModel):
#     email: EmailStr
#     password: str
#     mfa_code: Optional[str] = None

# class Token(BaseModel):
#     access_token: str
#     token_type: str
#     refresh_token: Optional[str] = None

# class RefreshTokenRequest(BaseModel):
#     refresh_token: str

# # -------------------------
# # CRUD & HELPERS
# # -------------------------
# async def create_user(db: AsyncSession, user: UserCreate) -> User:
#     db_user = User(email=user.email, phone=user.phone, hashed_password=hash_password(user.password), role=user.role, is_active=False)
#     db.add(db_user)
#     await db.commit()
#     await db.refresh(db_user)
#     return db_user

# async def get_user(db: AsyncSession, user_id: str) -> Optional[User]:
#     result = await db.execute(select(User).filter(User.id == user_id))
#     return result.scalars().first()

# async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
#     result = await db.execute(select(User).filter(User.email == email))
#     return result.scalars().first()

# async def log_action(db: AsyncSession, user: User, action: str, performed_by: Optional[str] = None):
#     log = AuditLog(user_id=user.id, action=action, performed_by=performed_by)
#     db.add(log)
#     await db.commit()

# # -------------------------
# # JWT & AUTH
# # -------------------------
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# def create_access_token(data: dict, expires_delta: timedelta | None = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# def create_refresh_token(data: dict):
#     expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
#     to_encode = data.copy()
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("sub")
#         if user_id is None:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
#     except JWTError:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
#     user = await get_user(db, user_id)
#     if not user or not user.is_active:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not approved")
#     return user

# def require_roles(*roles):
#     async def role_checker(current_user: User = Depends(get_current_user)):
#         if current_user.role not in roles:
#             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
#         return current_user
#     return role_checker

# # -------------------------
# # REDIS
# # -------------------------
# r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
# def cache_profile(user_id: int, profile: dict):
#     r.set(f"profile:{user_id}", profile)
# def get_cached_profile(user_id: int):
#     return r.get(f"profile:{user_id}")
# def cache_feed(key: str, user_ids: list):
#     r.set(key, ",".join(map(str, user_ids)))
# def get_feed(key: str):
#     data = r.get(key)
#     return data.split(",") if data else []

# # -------------------------
# # MINIO
# # -------------------------
# minio_client = Minio(
#     MINIO_ENDPOINT,
#     access_key=MINIO_ACCESS_KEY,
#     secret_key=MINIO_SECRET_KEY,
#     secure=False
# )
# def ensure_bucket():
#     if not minio_client.bucket_exists(MINIO_BUCKET):
#         minio_client.make_bucket(MINIO_BUCKET)
# def upload_full_image(image_id: str, file_path: str):
#     ensure_bucket()
#     minio_client.fput_object(MINIO_BUCKET, f"{image_id}.jpg", file_path)
#     return f"{image_id}.jpg"
# def generate_signed_url(image_id: str):
#     return minio_client.presigned_get_object(MINIO_BUCKET, f"{image_id}.jpg")

# # -------------------------
# # IMAGE PROCESSING
# # -------------------------
# def process_image(upload_file: bytes):
#     image_id = str(uuid.uuid4())
#     temp_path = f"{image_id}.jpg"
#     with open(temp_path, "wb") as f:
#         f.write(upload_file)
#     img = Image.open(temp_path).convert("RGB")
#     tiny_path = os.path.join(RAM_TINY, f"{image_id}.webp")
#     medium_path = os.path.join(RAM_MEDIUM, f"{image_id}.webp")
#     img.copy().thumbnail((200, 200)); img.save(tiny_path, "WEBP", quality=40)
#     img.copy().thumbnail((800, 800)); img.save(medium_path, "WEBP", quality=70)
#     upload_full_image(image_id, temp_path)
#     os.remove(temp_path)
#     return {"image_id": image_id, "tiny": tiny_path, "medium": medium_path}

# # -------------------------
# # FASTAPI APP
# # -------------------------
# app = FastAPI(title="Unified Matrimony + Auth Backend")
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# # Routers
# images_router = APIRouter()
# profiles_router = APIRouter()

# # -------------------------
# # AUTH ENDPOINTS
# # -------------------------
# @app.post("/register/", response_model=UserRead)
# async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
#     if await get_user_by_email(db, user.email):
#         raise HTTPException(status_code=400, detail="Email already registered")
#     return await create_user(db, user)

# @app.post("/login/", response_model=Token)
# @limiter.limit("5/minute")
# async def login(user: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
#     db_user = await get_user_by_email(db, user.email)
#     if not db_user or not verify_password(user.password, db_user.hashed_password):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
#     if not db_user.is_active:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not approved")
#     if db_user.mfa_secret:
#         if not user.mfa_code or not pyotp.TOTP(db_user.mfa_secret).verify(user.mfa_code, valid_window=1):
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
#     access_token = create_access_token({"sub": db_user.id, "role": db_user.role})
#     refresh_token = create_refresh_token({"sub": db_user.id})
#     await log_action(db, db_user, "login")
#     return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

# @app.get("/mfa/qrcode")
# async def generate_mfa_qr(current_user: User = Depends(get_current_user)):
#     if not current_user.mfa_secret:
#         raise HTTPException(status_code=400, detail="MFA not initialized")
#     uri = pyotp.totp.TOTP(current_user.mfa_secret).provisioning_uri(name=current_user.email, issuer_name="SecureApp")
#     buf = io.BytesIO(); qrcode.make(uri).save(buf, format='PNG'); buf.seek(0)
#     return StreamingResponse(buf, media_type="image/png")

# @app.get("/me", response_model=UserRead)
# async def read_current_user(current_user: User = Depends(get_current_user)):
#     return current_user

# # -------------------------
# # IMAGE ENDPOINTS
# # -------------------------
# @images_router.post("/upload-image")
# async def upload_image(file: UploadFile = File(...)):
#     data = await file.read()
#     result = process_image(data)
#     return {"image_id": result["image_id"], "tiny_url": result["tiny"], "medium_url": result["medium"]}

# @profiles_router.get("/feed/{gender}/{city}")
# async def feed(gender: str, city: str, db=Depends(get_db)):
#     key = f"feed:{gender}:{city}"
#     cached = get_feed(key)
#     if cached:
#         return {"users": cached}
#     rows = await db.fetch("SELECT id FROM users WHERE role=$1 ORDER BY id DESC LIMIT 200", gender)  # Example
#     user_ids = [str(r['id']) for r in rows]
#     cache_feed(key, user_ids)
#     return {"users": user_ids}

# app.include_router(images_router, prefix="/images")
# app.include_router(profiles_router, prefix="/profiles")

# @app.on_event("startup")
# async def startup():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     ensure_bucket()


# # -------------------------------
# # DATABASE INIT (Postgres or SQLite fallback)
# # -------------------------------

# import asyncpg
# from sqlalchemy.ext.asyncio import AsyncEngine

# DB_TYPE = None
# engine: AsyncEngine = None
# async_session = None

# try:
#     # Try connecting to PostgreSQL
#     test_conn = asyncpg.connect(Config.POSTGRES_URL)
#     DB_TYPE = "postgres"
#     DATABASE_URL = Config.POSTGRES_URL
#     print("PostgreSQL connection OK")
# except Exception as e:
#     print("PostgreSQL connection failed, falling back to SQLite:", e)
#     DB_TYPE = "sqlite"
#     DATABASE_URL = "sqlite+aiosqlite:///./dev_fallback.db"

# # SQLAlchemy engine
# engine = create_async_engine(DATABASE_URL, echo=False)
# async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# async def get_db():
#     async with async_session() as session:
#         yield session

# import io
# import os
# import uuid
# from datetime import datetime, timedelta
# from typing import Optional

# from fastapi import FastAPI, HTTPException, Depends, status, Request
# from fastapi.responses import StreamingResponse
# from fastapi.security import OAuth2PasswordBearer
# from pydantic import BaseModel, EmailStr
# from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP, ForeignKey
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import declarative_base, sessionmaker, relationship
# from sqlalchemy.sql import func
# from sqlalchemy.future import select
# from passlib.context import CryptContext
# from jose import JWTError, jwt
# import pyotp
# import qrcode
# # pip install slowapi sqlalchemy[asyncio] jose passlib[bcrypt] pyotp qrcode[pil]
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded

# # -------------------------
# # Config
# # -------------------------
# ENV = os.getenv("ENV", "dev")
# DATABASE_URL = os.getenv("DATABASE_URL") if ENV == "prod" else "sqlite+aiosqlite:///./dev.db"

# SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_dev_key")
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 15
# REFRESH_TOKEN_EXPIRE_DAYS = 7

# # -------------------------
# # Database setup
# # -------------------------
# engine = create_async_engine(DATABASE_URL, echo=False)
# async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
# Base = declarative_base()

# async def get_db():
#     async with async_session() as session:
#         yield session

# # -------------------------
# # Password hashing
# # -------------------------
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)
# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)

# # -------------------------
# # Models
# # -------------------------
# class User(Base):
#     __tablename__ = "users"
#     id = Column(String if "sqlite" in DATABASE_URL else "BIGINT", primary_key=True, default=lambda: str(uuid.uuid4()))
#     uuid = Column(String, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
#     email = Column(String, unique=True, nullable=False)
#     phone = Column(Text, unique=True)
#     hashed_password = Column(Text, nullable=False)
#     is_active = Column(Boolean, default=False, nullable=False)
#     role = Column(String, default='user', nullable=False)
#     mfa_secret = Column(String, default=lambda: pyotp.random_base32())
#     created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
#     updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
#     audit_logs = relationship("AuditLog", back_populates="user")

# class AuditLog(Base):
#     __tablename__ = "audit_logs"
#     id = Column(String if "sqlite" in DATABASE_URL else "BIGINT", primary_key=True, default=lambda: str(uuid.uuid4()))
#     user_id = Column(String, ForeignKey("users.id"))
#     action = Column(String)
#     timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
#     performed_by = Column(String)  # UUID of admin
#     user = relationship("User", back_populates="audit_logs")

# # -------------------------
# # Schemas
# # -------------------------
# class UserBase(BaseModel):
#     email: Optional[EmailStr]
#     phone: Optional[str]
#     role: Optional[str] = "user"
#     is_active: Optional[bool] = True

# class UserCreate(UserBase):
#     password: str

# class UserRead(UserBase):
#     id: str
#     uuid: str
#     created_at: datetime
#     updated_at: datetime
#     class Config:
#         orm_mode = True

# class UserLogin(BaseModel):
#     email: EmailStr
#     password: str
#     mfa_code: Optional[str] = None

# class Token(BaseModel):
#     access_token: str
#     token_type: str
#     refresh_token: Optional[str] = None

# class RefreshTokenRequest(BaseModel):
#     refresh_token: str

# # -------------------------
# # CRUD & Helpers
# # -------------------------
# async def create_user(db: AsyncSession, user: UserCreate) -> User:
#     db_user = User(email=user.email, phone=user.phone, hashed_password=hash_password(user.password), role=user.role, is_active=False)
#     db.add(db_user)
#     await db.commit()
#     await db.refresh(db_user)
#     return db_user

# async def get_user(db: AsyncSession, user_id: str) -> Optional[User]:
#     result = await db.execute(select(User).filter(User.id == user_id))
#     return result.scalars().first()

# async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
#     result = await db.execute(select(User).filter(User.email == email))
#     return result.scalars().first()

# async def log_action(db: AsyncSession, user: User, action: str, performed_by: Optional[str] = None):
#     log = AuditLog(user_id=user.id, action=action, performed_by=performed_by)
#     db.add(log)
#     await db.commit()

# # -------------------------
# # JWT & Auth
# # -------------------------
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# def create_access_token(data: dict, expires_delta: timedelta | None = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# def create_refresh_token(data: dict):
#     expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
#     to_encode = data.copy()
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("sub")
#         if user_id is None:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
#     except JWTError:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
#     user = await get_user(db, user_id)
#     if not user or not user.is_active:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not approved")
#     return user

# def require_roles(*roles):
#     async def role_checker(current_user: User = Depends(get_current_user)):
#         if current_user.role not in roles:
#             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
#         return current_user
#     return role_checker

# # -------------------------
# # FastAPI App
# # -------------------------
# app = FastAPI(title="Secure JWT + MFA + QR + Audit")
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# @app.on_event("startup")
# async def startup():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

# # -------------------------
# # Endpoints
# # -------------------------

# @app.post("/register/", response_model=UserRead)
# async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
#     if await get_user_by_email(db, user.email):
#         raise HTTPException(status_code=400, detail="Email already registered")
#     return await create_user(db, user)

# @app.get("/mfa/qrcode")
# async def generate_mfa_qr(current_user: User = Depends(get_current_user)):
#     if not current_user.mfa_secret:
#         raise HTTPException(status_code=400, detail="MFA not initialized")
#     uri = pyotp.totp.TOTP(current_user.mfa_secret).provisioning_uri(name=current_user.email, issuer_name="SecureApp")
#     img = qrcode.make(uri)
#     buf = io.BytesIO()
#     img.save(buf, format='PNG')
#     buf.seek(0)
#     return StreamingResponse(buf, media_type="image/png")

# @app.put("/users/me", response_model=UserRead)
# async def update_profile(user_data: UserBase, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
#     for field, value in user_data.dict(exclude_unset=True).items():
#         if field in ["role", "is_active"]:
#             continue  # prevent privilege escalation
#         setattr(current_user, field, value)
#     await db.commit()
#     await db.refresh(current_user)
#     return current_user

# @app.put("/admin/approve/{user_id}", response_model=UserRead)
# async def approve_user(user_id: str, current_user: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
#     user = await get_user(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     user.is_active = True
#     await log_action(db, user, "approved", performed_by=current_user.id)
#     await db.commit()
#     await db.refresh(user)
#     return user

# @app.post("/login/", response_model=Token)
# @limiter.limit("5/minute")
# async def login(user: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
#     db_user = await get_user_by_email(db, user.email)
#     if not db_user or not verify_password(user.password, db_user.hashed_password):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
#     if not db_user.is_active:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not approved")
#     if db_user.mfa_secret:
#         if not user.mfa_code or not pyotp.TOTP(db_user.mfa_secret).verify(user.mfa_code, valid_window=1):
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
#     access_token = create_access_token({"sub": db_user.id, "role": db_user.role})
#     refresh_token = create_refresh_token({"sub": db_user.id})
#     await log_action(db, db_user, "login")
#     return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

# @app.post("/refresh/", response_model=Token)
# async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
#     try:
#         payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("sub")
#     except JWTError:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
#     user = await get_user(db, user_id)
#     if not user or not user.is_active:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
#     access_token = create_access_token({"sub": user.id, "role": user.role})
#     refresh_token = create_refresh_token({"sub": user.id})
#     await log_action(db, user, "refresh_token")
#     return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

# @app.get("/me", response_model=UserRead)
# async def read_current_user(current_user: User = Depends(get_current_user)):
#     return current_user

# @app.get("/admin", response_model=UserRead)
# async def admin_endpoint(current_user: User = Depends(require_roles("admin"))):
#     return current_user



# # # backend_app.py

# import os
# import uuid
# from fastapi import FastAPI, APIRouter, UploadFile, File, Depends
# import asyncpg
# import redis
# from minio import Minio
# from PIL import Image

# # -------------------------------
# # 1. CONFIG
# # -------------------------------

# class Config:
#     POSTGRES_URL = os.getenv(
#         "POSTGRES_URL", "postgresql://postgres:1234@localhost:5432/matrimony_db"
#     )
#     REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
#     REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

#     MINIO_ENDPOINT = "localhost:9000"
#     MINIO_ACCESS_KEY = "minioadmin"
#     MINIO_SECRET_KEY = "minioadmin"
#     MINIO_BUCKET = "profile-images"

#     RAM_TINY = "D:/auram_sharahiya/sample_image_database"
#     RAM_MEDIUM = "D:/auram_sharahiya/sample_image_database"

# # Make RAM directories if not exist
# os.makedirs(Config.RAM_TINY, exist_ok=True)
# os.makedirs(Config.RAM_MEDIUM, exist_ok=True)

# # -------------------------------
# # 2. DATABASE
# # -------------------------------

# async def get_db():
#     conn = await asyncpg.connect(Config.POSTGRES_URL)
#     try:
#         yield conn
#     finally:
#         await conn.close()

# # -------------------------------
# # 3. REDIS
# # -------------------------------

# r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)

# def cache_profile(user_id: int, profile: dict):
#     r.set(f"profile:{user_id}", profile)

# def get_cached_profile(user_id: int):
#     return r.get(f"profile:{user_id}")

# def cache_feed(key: str, user_ids: list):
#     r.set(key, ",".join(map(str, user_ids)))

# def get_feed(key: str):
#     data = r.get(key)
#     return data.split(",") if data else []

# # -------------------------------
# # 4. MINIO
# # -------------------------------

# minio_client = Minio(
#     Config.MINIO_ENDPOINT,
#     access_key=Config.MINIO_ACCESS_KEY,
#     secret_key=Config.MINIO_SECRET_KEY,
#     secure=False
# )

# def ensure_bucket():
#     if not minio_client.bucket_exists(Config.MINIO_BUCKET):
#         minio_client.make_bucket(Config.MINIO_BUCKET)

# def upload_full_image(image_id: str, file_path: str):
#     ensure_bucket()
#     minio_client.fput_object(Config.MINIO_BUCKET, f"{image_id}.jpg", file_path)
#     return f"{image_id}.jpg"

# def generate_signed_url(image_id: str):
#     return minio_client.presigned_get_object(Config.MINIO_BUCKET, f"{image_id}.jpg")

# # -------------------------------
# # 5. IMAGE PROCESSING (Pillow)
# # -------------------------------

# def process_image(upload_file: bytes):
#     image_id = str(uuid.uuid4())
#     temp_path = f"{image_id}.jpg"

#     # Save raw upload temporarily
#     with open(temp_path, "wb") as f:
#         f.write(upload_file)

#     img = Image.open(temp_path)
#     img = img.convert("RGB")  # Ensure consistent format

#     # Tiny thumbnail
#     tiny_img = img.copy()
#     tiny_img.thumbnail((200, 200))
#     tiny_path = os.path.join(Config.RAM_TINY, f"{image_id}.webp")
#     tiny_img.save(tiny_path, "WEBP", quality=40)

#     # Medium thumbnail
#     medium_img = img.copy()
#     medium_img.thumbnail((800, 800))
#     medium_path = os.path.join(Config.RAM_MEDIUM, f"{image_id}.webp")
#     medium_img.save(medium_path, "WEBP", quality=70)

#     # Upload full image to MinIO
#     upload_full_image(image_id, temp_path)

#     # Clean up temp raw file
#     os.remove(temp_path)

#     return {
#         "image_id": image_id,
#         "tiny": tiny_path,
#         "medium": medium_path
#     }

# # -------------------------------
# # 6. ROUTES
# # -------------------------------

# images_router = APIRouter()

# @images_router.post("/upload-image")
# async def upload_image(file: UploadFile = File(...)):
#     data = await file.read()
#     result = process_image(data)
#     return {
#         "image_id": result["image_id"],
#         "tiny_url": result["tiny"],
#         "medium_url": result["medium"]
#     }

# profiles_router = APIRouter()

# @profiles_router.get("/feed/{gender}/{city}")
# async def feed(gender: str, city: str, db=Depends(get_db)):
#     key = f"feed:{gender}:{city}"
#     cached = get_feed(key)
#     if cached:
#         return {"users": cached}

#     rows = await db.fetch(
#         "SELECT id FROM users WHERE gender=$1 AND city=$2 ORDER BY id DESC LIMIT 200",
#         gender, city
#     )
#     user_ids = [str(r['id']) for r in rows]
#     cache_feed(key, user_ids)
#     return {"users": user_ids}

# # -------------------------------
# # 7. FASTAPI APP
# # -------------------------------

# app = FastAPI(title="Matrimony Backend (Windows Pillow Version)")
# app.include_router(profiles_router, prefix="/profiles")
# app.include_router(images_router, prefix="/images")

# # -------------------------------
# # 8. STARTUP EVENTS
# # -------------------------------

# @app.on_event("startup")
# async def startup_event():
#     ensure_bucket()
#     try:
#         conn = await asyncpg.connect(Config.POSTGRES_URL)
#         await conn.close()
#         print("PostgreSQL connection OK")
#     except Exception as e:
#         print("PostgreSQL connection failed:", e)
