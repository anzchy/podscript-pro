import os
from pathlib import Path

from .models import AppConfig


def load_config() -> AppConfig:
    try:
        from dotenv import load_dotenv

        # Try to load .env from project root (parent of src)
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
        else:
            # Fallback to current directory
            load_dotenv()
    except Exception:
        pass
    artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")
    Path(artifacts_dir).mkdir(parents=True, exist_ok=True)
    storage_provider = os.getenv("STORAGE_PROVIDER")
    storage_bucket = os.getenv("STORAGE_BUCKET") or os.getenv("OSS_BUCKET")
    storage_public_host = os.getenv("STORAGE_PUBLIC_HOST") or os.getenv("OSS_PUBLIC_HOST")
    storage_region = os.getenv("STORAGE_REGION") or os.getenv("OSS_REGION")
    storage_endpoint = os.getenv("STORAGE_ENDPOINT")
    return AppConfig(
        access_key_id=(os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID") or "").strip() or None,
        access_key_secret=(os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or "").strip() or None,
        security_token=(os.getenv("ALIBABA_CLOUD_SECURITY_TOKEN") or "").strip() or None,
        storage_provider=storage_provider,
        storage_bucket=storage_bucket,
        storage_public_host=storage_public_host,
        storage_region=storage_region,
        storage_endpoint=storage_endpoint,
        qwen_api_key=os.getenv("QWEN_API_KEY"),
        tingwu_app_key=(os.getenv("TINGWU_APP_KEY") or "").strip() or None,
        artifacts_dir=artifacts_dir,
    )