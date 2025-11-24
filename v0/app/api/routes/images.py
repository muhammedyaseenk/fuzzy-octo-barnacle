from fastapi import APIRouter, UploadFile, File
from image_uploader_routes import process_image

router = APIRouter()

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    data = await file.read()

    result = process_image(data)

    return {
        "image_id": result["image_id"],
        "tiny_url": result["tiny"],
        "medium_url": result["medium"]
    }
