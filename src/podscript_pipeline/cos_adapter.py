"""
Tencent Cloud COS adapter for audio file storage.
Used as alternative to Alibaba Cloud OSS for Tingwu transcription.
"""
import logging
import mimetypes
import re
from pathlib import Path

from podscript_shared.models import AppConfig

logger = logging.getLogger(__name__)


def upload_to_cos(cfg: AppConfig, local_file: Path) -> str:
    """
    Upload local audio file to Tencent Cloud COS and return signed URL.

    Args:
        cfg: Application config with Tencent Cloud credentials
        local_file: Path to the local audio file

    Returns:
        Signed URL valid for 3 hours (required by Tingwu API)
    """
    from qcloud_cos import CosConfig, CosS3Client

    logger.info(f"upload_to_cos: Starting upload for {local_file}")
    logger.debug(f"upload_to_cos: file_size={local_file.stat().st_size} bytes")

    secret_id = (cfg.tencent_secret_id or "").strip()
    secret_key = (cfg.tencent_secret_key or "").strip()
    region = (cfg.storage_region or "ap-shanghai").strip()
    bucket = (cfg.storage_bucket or "").strip()

    if not secret_id or not secret_key:
        raise ValueError("Tencent Cloud credentials not configured (TENCENT_SECRET_ID, TENCENT_SECRET_KEY)")
    if not bucket:
        raise ValueError("Storage bucket not configured (STORAGE_BUCKET)")

    logger.info(f"upload_to_cos: region={region}, bucket={bucket}")

    cos_config = CosConfig(
        Region=region,
        SecretId=secret_id,
        SecretKey=secret_key,
        Token=None,
        Scheme='https',
    )
    client = CosS3Client(cos_config)

    # Sanitize filename for COS (preserve Chinese and other Unicode characters)
    sanitized = re.sub(r"\s+", "_", local_file.name)
    # Only remove characters that are problematic for object keys: / \ : * ? " < > | and control chars
    sanitized = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "-", sanitized)

    # Build object key with optional prefix
    prefix = (cfg.storage_prefix or "tingwu-audio").strip().strip("/")
    object_key = f"{prefix}/{sanitized}"
    logger.info(f"upload_to_cos: object_key={object_key}")

    content_type = mimetypes.guess_type(sanitized)[0] or "application/octet-stream"
    logger.debug(f"upload_to_cos: content_type={content_type}")

    # Upload file
    logger.info("upload_to_cos: Uploading file to COS...")
    response = client.upload_file(
        Bucket=bucket,
        Key=object_key,
        LocalFilePath=str(local_file),
        EnableMD5=False,
        ContentType=content_type,
    )
    logger.info(f"upload_to_cos: Upload response ETag={response.get('ETag', 'N/A')}")

    # Generate signed URL valid for 3 hours (10800 seconds)
    # Tingwu requires at least 3 hours validity for async processing
    url = client.get_presigned_url(
        Method='GET',
        Bucket=bucket,
        Key=object_key,
        Expired=10800,  # 3 hours
    )
    logger.info(f"upload_to_cos: Generated signed URL (length={len(url)})")

    return url
