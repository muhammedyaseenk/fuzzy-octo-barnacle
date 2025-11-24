import os
import uuid
from fastapi import APIRouter, UploadFile, File
from minio import Minio
from PIL import Image
from app.config.config import Config

images_router = APIRouter()

# MinIO client
minio_client = Minio(
    Config.MINIO_ENDPOINT,
    access_key=Config.MINIO_ROOT_USER,
    secret_key=Config.MINIO_ROOT_PASSWORD,
    secure=False
)

def ensure_bucket():
    if not minio_client.bucket_exists(Config.MINIO_BUCKET):
        minio_client.make_bucket(Config.MINIO_BUCKET)

def upload_full_image(image_id: str, file_path: str):
    ensure_bucket()
    minio_client.fput_object(Config.MINIO_BUCKET, f"{image_id}.jpg", file_path)
    return f"{image_id}.jpg"

def process_image(upload_file: bytes):
    image_id = str(uuid.uuid4())
    temp_path = f"{image_id}.jpg"

    # Save raw upload temporarily
    with open(temp_path, "wb") as f:
        f.write(upload_file)

    img = Image.open(temp_path)
    img = img.convert("RGB")

    # Tiny thumbnail
    tiny_img = img.copy()
    tiny_img.thumbnail((200, 200))
    tiny_path = os.path.join(Config.RAM_TINY, f"{image_id}.webp")
    tiny_img.save(tiny_path, "WEBP", quality=40)

    # Medium thumbnail
    medium_img = img.copy()
    medium_img.thumbnail((800, 800))
    medium_path = os.path.join(Config.RAM_MEDIUM, f"{image_id}.webp")
    medium_img.save(medium_path, "WEBP", quality=70)

    # Upload full image
    upload_full_image(image_id, temp_path)

    # Remove temp raw file
    os.remove(temp_path)

    return {
        "image_id": image_id,
        "tiny": tiny_path,
        "medium": medium_path
    }

# Image upload route
@images_router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    data = await file.read()
    result = process_image(data)
    return {
        "image_id": result["image_id"],
        "tiny_url": result["tiny"],
        "medium_url": result["medium"]
    }
