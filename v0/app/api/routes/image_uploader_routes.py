import uuid
import os
import pyvips
from config.config import Config
from utilities.minio_client import upload_full_image

def process_image(upload_file):
    image_id = str(uuid.uuid4())
    temp_path = f"/tmp/{image_id}.jpg"
    with open(temp_path, "wb") as f:
        f.write(upload_file)

    img = pyvips.Image.new_from_file(temp_path)

    tiny_path = os.path.join(Config.RAM_TINY, f"{image_id}.webp")
    tiny = img.thumbnail_image(200)
    tiny.write_to_file(tiny_path, Q=40)

    medium_path = os.path.join(Config.RAM_MEDIUM, f"{image_id}.webp")
    med = img.thumbnail_image(800)
    med.write_to_file(medium_path, Q=70)

    upload_full_image(image_id, temp_path)

    return {
        "image_id": image_id,
        "tiny": tiny_path,
        "medium": medium_path
    }
