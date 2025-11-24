from minio import Minio
from app.config.config import Config

minio_client = Minio(
    Config.MINIO_ENDPOINT,
    access_key=Config.MINIO_ACCESS_KEY,
    secret_key=Config.MINIO_SECRET_KEY,
    secure=False
)

def ensure_bucket():
    if not minio_client.bucket_exists(Config.MINIO_BUCKET):
        minio_client.make_bucket(Config.MINIO_BUCKET)

def upload_full_image(image_id: str, file_path: str):
    ensure_bucket()
    minio_client.fput_object(
        Config.MINIO_BUCKET,
        f"{image_id}.jpg",
        file_path
    )
    return f"{image_id}.jpg"

def generate_signed_url(image_id: str):
    return minio_client.presigned_get_object(
        Config.MINIO_BUCKET,
        f"{image_id}.jpg"
    )
