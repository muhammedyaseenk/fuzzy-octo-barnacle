# app/core/storage.py
import os
import uuid
from minio import Minio
from minio.error import S3Error
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional
from app.core.config import settings

# MinIO client
minio_client = None


def init_minio():
    """Initialize MinIO client"""
    global minio_client
    minio_client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
        secure=settings.MINIO_SECURE
    )


def get_minio_client():
    """Get MinIO client"""
    if minio_client is None:
        init_minio()
    return minio_client


def ensure_bucket():
    """Ensure MinIO bucket exists"""
    client = get_minio_client()
    try:
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
            print(f"Created bucket: {settings.MINIO_BUCKET}")
        else:
            print(f"Bucket {settings.MINIO_BUCKET} already exists")
    except S3Error as e:
        print(f"Error creating bucket: {e}")


def process_image(image_data: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Process image to create tiny, medium, and original versions
    Returns: (tiny_webp, medium_webp, original_jpg)
    """
    # Open image
    image = Image.open(BytesIO(image_data))
    
    # Convert to RGB if necessary
    if image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')
    
    # Create tiny version (200x200)
    tiny_image = image.copy()
    tiny_image.thumbnail((200, 200), Image.Resampling.LANCZOS)
    tiny_buffer = BytesIO()
    tiny_image.save(tiny_buffer, format='WEBP', quality=85)
    tiny_webp = tiny_buffer.getvalue()
    
    # Create medium version (800x800)
    medium_image = image.copy()
    medium_image.thumbnail((800, 800), Image.Resampling.LANCZOS)
    medium_buffer = BytesIO()
    medium_image.save(medium_buffer, format='WEBP', quality=90)
    medium_webp = medium_buffer.getvalue()
    
    # Create original JPG
    original_buffer = BytesIO()
    image.save(original_buffer, format='JPEG', quality=95)
    original_jpg = original_buffer.getvalue()
    
    return tiny_webp, medium_webp, original_jpg


def upload_full_image(image_data: bytes, filename: Optional[str] = None) -> str:
    """Upload full image to MinIO and return image_id"""
    client = get_minio_client()
    
    if filename is None:
        filename = f"{uuid.uuid4()}.jpg"
    
    try:
        client.put_object(
            settings.MINIO_BUCKET,
            filename,
            BytesIO(image_data),
            length=len(image_data),
            content_type='image/jpeg'
        )
        return filename.split('.')[0]  # Return image_id without extension
    except S3Error as e:
        raise Exception(f"Failed to upload image: {e}")


def save_processed_images(image_id: str, tiny_webp: bytes, medium_webp: bytes):
    """Save processed images to local directories"""
    # Ensure directories exist
    os.makedirs(settings.IMAGE_RAM_TINY, exist_ok=True)
    os.makedirs(settings.IMAGE_RAM_MEDIUM, exist_ok=True)
    
    # Save tiny image
    tiny_path = os.path.join(settings.IMAGE_RAM_TINY, f"{image_id}.webp")
    with open(tiny_path, 'wb') as f:
        f.write(tiny_webp)
    
    # Save medium image
    medium_path = os.path.join(settings.IMAGE_RAM_MEDIUM, f"{image_id}.webp")
    with open(medium_path, 'wb') as f:
        f.write(medium_webp)
    
    return tiny_path, medium_path


def generate_signed_url(object_name: str, expires_in_seconds: int = 3600) -> str:
    """Generate signed URL for MinIO object"""
    client = get_minio_client()
    try:
        url = client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_name,
            expires=expires_in_seconds
        )
        return url
    except S3Error as e:
        raise Exception(f"Failed to generate signed URL: {e}")


def get_image_urls(image_id: str) -> dict:
    """Get URLs for all image versions"""
    return {
        "image_id": image_id,
        "tiny_url": f"/images/tiny/{image_id}.webp",
        "medium_url": f"/images/medium/{image_id}.webp",
        "full_url": generate_signed_url(f"{image_id}.jpg")
    }