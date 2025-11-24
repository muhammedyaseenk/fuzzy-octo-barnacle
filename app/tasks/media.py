# app/tasks/media.py
from app.celery_app import celery_app


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def process_image_async(self, image_id: str, user_id: int):
    """Process uploaded image asynchronously"""
    try:
        from app.core.storage import process_image, save_processed_images
        print(f"Processing image {image_id} for user {user_id}")
        return {"status": "processed", "image_id": image_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def cleanup_old_images():
    """Cleanup old unused images"""
    print("Cleaning up old images")


@celery_app.task
def generate_image_thumbnails(image_id: str):
    """Generate additional thumbnail sizes"""
    print(f"Generating thumbnails for {image_id}")