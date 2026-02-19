from __future__ import annotations

import io
import uuid

from PIL import Image

from app.core.storage import get_s3_client
from app.config import get_settings
from app.tasks import celery_app

settings = get_settings()


@celery_app.task(name="process_image")
def process_image(
    source_key: str,
    couple_id: str,
    post_id: str,
) -> dict:
    """
    Process uploaded image: generate thumbnails and medium-size versions.

    Args:
        source_key: S3 key of the original image
        couple_id: Couple UUID
        post_id: Post UUID

    Returns:
        Dict with URLs for original, medium, and thumbnail
    """
    client = get_s3_client()

    # Download original image
    response = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=source_key)
    image_data = response["Body"].read()

    with Image.open(io.BytesIO(image_data)) as img:
        # Strip EXIF data
        data = list(img.getdata())
        img_no_exif = Image.new(img.mode, img.size)
        img_no_exif.putdata(data)

        # Generate medium (800px wide)
        medium_img = img_no_exif.copy()
        if medium_img.width > 800:
            ratio = 800 / medium_img.width
            new_height = int(medium_img.height * ratio)
            medium_img = medium_img.resize((800, new_height), Image.Resampling.LANCZOS)

        # Generate thumbnail (300x300 crop)
        thumb_img = img_no_exif.copy()
        thumb_img.thumbnail((300, 300), Image.Resampling.LANCZOS)

        # Save and upload medium
        image_uuid = str(uuid.uuid4())
        medium_key = f"couples/{couple_id}/posts/{post_id}/medium_{image_uuid}.jpg"
        medium_buffer = io.BytesIO()
        medium_img.convert("RGB").save(medium_buffer, "JPEG", quality=85)
        medium_buffer.seek(0)
        client.upload_fileobj(
            medium_buffer,
            settings.S3_BUCKET_NAME,
            medium_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )

        # Save and upload thumbnail
        thumb_key = f"couples/{couple_id}/posts/{post_id}/thumb_{image_uuid}.jpg"
        thumb_buffer = io.BytesIO()
        thumb_img.convert("RGB").save(thumb_buffer, "JPEG", quality=80)
        thumb_buffer.seek(0)
        client.upload_fileobj(
            thumb_buffer,
            settings.S3_BUCKET_NAME,
            thumb_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )

    base_url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}"
    return {
        "original_url": f"{base_url}/{source_key}",
        "medium_url": f"{base_url}/{medium_key}",
        "thumbnail_url": f"{base_url}/{thumb_key}",
        "width": img_no_exif.width,
        "height": img_no_exif.height,
    }
