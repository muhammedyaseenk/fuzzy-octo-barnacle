# app/core/config.py
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    ENV: str = "dev"
    
    # Database
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/aurum_db"
    ONBOARDING_POSTGRES_URL: str = "postgresql://postgres:password@localhost:5432/aurum_db"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET: str = "profile-images"
    MINIO_SECURE: bool = False
    
    # Auth / Security
    SECRET_KEY: str = "super_secret_prod_key_change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Images
    IMAGE_RAM_TINY: str = "./images/tiny"
    IMAGE_RAM_MEDIUM: str = "./images/medium"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:4200", 
        "http://localhost:8080",
        "http://localhost:5173",
        # Local API dev host (useful when frontend calls backend directly)
        "http://localhost:8000"
    ]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    
    # Session Management
    SESSION_EXPIRE_MINUTES: int = 60
    
    # WhatsApp
    WHATSAPP_PHONE_NUMBER_ID: str = "your_phone_number_id"
    WHATSAPP_ACCESS_TOKEN: str = "your_access_token"
    
    # OpenAI
    OPENAI_API_KEY: str = "your_openai_api_key"
    
    class Config:
        env_file = ".env"


settings = Settings()