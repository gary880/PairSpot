from __future__ import annotations

from io import BytesIO

import boto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


async def upload_file(file_data: bytes, key: str, content_type: str = "image/jpeg") -> str:
    """Upload file to S3-compatible storage and return the URL."""
    client = get_s3_client()
    client.upload_fileobj(
        BytesIO(file_data),
        settings.S3_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{key}"


async def delete_file(key: str) -> None:
    """Delete file from S3-compatible storage."""
    client = get_s3_client()
    client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
