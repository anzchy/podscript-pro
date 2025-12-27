"""
Unified storage interface for cloud object storage.
Supports Alibaba Cloud OSS and Tencent Cloud COS.
"""
import logging
from pathlib import Path

from podscript_shared.models import AppConfig

logger = logging.getLogger(__name__)

# Storage provider constants
STORAGE_PROVIDER_OSS = "oss"  # Alibaba Cloud OSS
STORAGE_PROVIDER_COS = "cos"  # Tencent Cloud COS


def upload_audio(cfg: AppConfig, local_file: Path) -> str:
    """
    Upload audio file to cloud storage and return signed URL.

    Automatically selects storage provider based on STORAGE_PROVIDER config:
    - 'oss': Alibaba Cloud OSS (default)
    - 'cos': Tencent Cloud COS

    Args:
        cfg: Application config with cloud credentials
        local_file: Path to the local audio file

    Returns:
        Signed URL for the uploaded file

    Raises:
        ValueError: If storage provider is not configured or invalid
    """
    provider = (cfg.storage_provider or STORAGE_PROVIDER_OSS).lower().strip()
    logger.info(f"upload_audio: Using storage provider '{provider}'")

    if provider == STORAGE_PROVIDER_COS:
        from podscript_pipeline.cos_adapter import upload_to_cos
        return upload_to_cos(cfg, local_file)
    elif provider == STORAGE_PROVIDER_OSS:
        from podscript_pipeline.tingwu_adapter import upload_to_oss
        return upload_to_oss(cfg, local_file)
    else:
        raise ValueError(
            f"Unknown storage provider: '{provider}'. "
            f"Supported: '{STORAGE_PROVIDER_OSS}' (Alibaba), '{STORAGE_PROVIDER_COS}' (Tencent)"
        )


def get_storage_provider_name(cfg: AppConfig) -> str:
    """Get human-readable name of the configured storage provider."""
    provider = (cfg.storage_provider or STORAGE_PROVIDER_OSS).lower().strip()
    names = {
        STORAGE_PROVIDER_OSS: "阿里云 OSS",
        STORAGE_PROVIDER_COS: "腾讯云 COS",
    }
    return names.get(provider, provider)
