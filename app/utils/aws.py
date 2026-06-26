"""
AWS / LocalStack client factory.

Uses boto3 with AWS_ENDPOINT_URL to target LocalStack in development
and real AWS in production — zero code changes required.
"""
import boto3
from botocore.config import Config

from app.core.config import settings


def get_s3_client():
    """
    Return a boto3 S3 client.

    - In development: points to LocalStack via AWS_ENDPOINT_URL
    - In production: uses standard AWS endpoints (set AWS_ENDPOINT_URL=None)
    """
    kwargs = {
        "region_name": settings.aws_default_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "config": Config(
            retries={"max_attempts": 3, "mode": "standard"},
            signature_version="s3v4",
        ),
    }
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url

    return boto3.client("s3", **kwargs)


async def upload_file_to_s3(
    file_content: bytes,
    object_key: str,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Upload a file to the configured S3 bucket.

    Returns the S3 object URL.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    client = get_s3_client()

    await loop.run_in_executor(
        None,
        lambda: client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
            Body=file_content,
            ContentType=content_type,
        ),
    )

    if settings.aws_endpoint_url:
        return f"{settings.aws_endpoint_url}/{settings.s3_bucket_name}/{object_key}"
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_default_region}.amazonaws.com/{object_key}"


def get_presigned_url(object_key: str, expires_in: int = 3600) -> str:
    """Generate a pre-signed URL for downloading a file."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": object_key},
        ExpiresIn=expires_in,
    )
