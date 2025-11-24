import os

# ON POWERSHELL RUN THIS TO ACTIVATE MINI-iO
# setx MINIO_ROOT_USER "adminuser"
# setx MINIO_ROOT_PASSWORD "StrongPass123!"
# .\minio.exe server D:\auram_sharahiya\sample_image_database --console-address ":9001"
#  or  
# (aurum_env) PS D:\auram_sharahiya> $env:MINIO_ROOT_USER="adminuser"
# >> $env:MINIO_ROOT_PASSWORD="StrongPass123!"
# >>
# (aurum_env) PS D:\auram_sharahiya> .\minio.exe server D:\auram_sharahiya\sample_image_database --console-address ":9001"
# >>
# MinIO Object Storage Server

# MinIO in Production

# Run as a service / container: Don’t run minio.exe manually; use either:

# Docker:

# docker run -p 9000:9000 -p 9001:9001 \
#   -e MINIO_ROOT_USER=adminuser \
#   -e MINIO_ROOT_PASSWORD=StrongPass123! \
#   -v /data/minio:/data \
#   minio/minio server /data --console-address ":9001"


# Systemd service (Linux) if not using Docker.

# Use strong credentials:

# MINIO_ROOT_USER → a secure username

# MINIO_ROOT_PASSWORD → a strong password (at least 12–16 characters)

# TLS / HTTPS:

# In production, always enable HTTPS. MinIO supports certificates:

# export MINIO_CERT_FILE=/path/to/public.crt
# export MINIO_KEY_FILE=/path/to/private.key

class Config:

    # -------------------------------
    # CROSS ORGINS
    # -------------------------------

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")


    # -------------------------------
    # DATABASE (PostgreSQL)
    # -------------------------------
    POSTGRES_URL = os.getenv(
        "POSTGRES_URL", "postgresql://postgres:1234@localhost:5432/matrimony_db"
    )

    # -------------------------------
    # REDIS
    # -------------------------------
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    # -------------------------------
    # MINIO CONFIGURATION
    # -------------------------------
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
    MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "adminuser")
    MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "StrongPass123!")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "profile-images")

    # -------------------------------
    # LOCAL STORAGE (for thumbnails)
    # -------------------------------
    RAM_TINY = os.getenv("RAM_TINY", "D:/auram_sharahiya/sample_image_database/tiny")
    RAM_MEDIUM = os.getenv("RAM_MEDIUM", "D:/auram_sharahiya/sample_image_database/medium")

# Ensure directories exist
os.makedirs(Config.RAM_TINY, exist_ok=True)
os.makedirs(Config.RAM_MEDIUM, exist_ok=True)




# import os

# class Config:
#     POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:1234@localhost:5432/matrimony_db")
#     REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
#     REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

#     MINIO_ENDPOINT = "localhost:9000"
#     MINIO_ACCESS_KEY = "minioadmin"
#     MINIO_SECRET_KEY = "minioadmin"
#     MINIO_BUCKET = "profile-images"

#     RAM_TINY = "R:/matrimony/thumbnails/"
#     RAM_MEDIUM = "R:/matrimony/medium_cache/"
