"""
ASR (Automatic Speech Recognition) module.
Supports multiple transcription backends:
- Alibaba Cloud Tingwu (通义听悟)
- OpenAI Whisper (offline)
"""
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from podscript_shared.config import load_config

logger = logging.getLogger(__name__)

# ASR Provider constants
ASR_PROVIDER_TINGWU = "tingwu"
ASR_PROVIDER_WHISPER = "whisper"

# Lazy import to handle missing SDKs
upload_to_oss = None
submit_transcribe_job = None
poll_transcribe_result = None


def _import_tingwu_adapters():
    global upload_to_oss, submit_transcribe_job, poll_transcribe_result
    try:
        from podscript_pipeline.tingwu_adapter import (
            upload_to_oss as _upload_to_oss,
            submit_transcribe_job as _submit_transcribe_job,
            poll_transcribe_result as _poll_transcribe_result
        )
        upload_to_oss = _upload_to_oss
        submit_transcribe_job = _submit_transcribe_job
        poll_transcribe_result = _poll_transcribe_result
        return True
    except ImportError as e:
        logger.warning(f"Failed to import tingwu_adapter: {e}")
        return False


def _import_whisper_adapter():
    try:
        from podscript_pipeline import whisper_adapter
        return whisper_adapter
    except ImportError as e:
        logger.warning(f"Failed to import whisper_adapter: {e}")
        return None


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    """Get available ASR providers and their status."""
    cfg = load_config()

    # Check Tingwu availability
    tingwu_available = bool(
        os.getenv("TINGWU_ENABLED") == "1"
        and cfg.access_key_id
        and cfg.access_key_secret
        and cfg.tingwu_app_key
        and cfg.storage_provider == "oss"
        and cfg.storage_bucket
        and cfg.storage_region
    )

    # Check Whisper availability
    whisper_adapter = _import_whisper_adapter()
    whisper_available = whisper_adapter is not None

    providers = {
        ASR_PROVIDER_TINGWU: {
            "name": "阿里云通义听悟",
            "available": tingwu_available,
            "description": "在线转写服务，需要阿里云账号配置",
            "models": ["default"],
        },
        ASR_PROVIDER_WHISPER: {
            "name": "Whisper 离线",
            "available": whisper_available,
            "description": "OpenAI开源模型，本地离线运行",
            "models": list(whisper_adapter.WHISPER_MODELS.keys()) if whisper_available else [],
        },
    }
    return providers


def transcribe(
    task_id: str,
    input_path: Path,
    provider: str = ASR_PROVIDER_WHISPER,
    model_name: Optional[str] = None,
    language: Optional[str] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Transcribe audio using specified provider.

    Args:
        task_id: Unique task identifier for logging
        input_path: Path to the audio file
        provider: ASR provider ('tingwu' or 'whisper')
        model_name: Model name (for Whisper: tiny, base, small, medium, large, turbo)
        language: Language code (e.g., 'zh', 'en') or None for auto-detect
        log_callback: Optional callback for progress logging

    Returns:
        Dict with transcription results
    """
    def log(msg: str):
        logger.info(f"[{task_id}] {msg}")
        if log_callback:
            log_callback(msg)

    log(f"transcribe() called with provider={provider}, model={model_name}, path={input_path}")

    if provider == ASR_PROVIDER_WHISPER:
        return _transcribe_with_whisper(task_id, input_path, model_name, language, log_callback)
    elif provider == ASR_PROVIDER_TINGWU:
        return _transcribe_with_tingwu(task_id, input_path, log_callback)
    else:
        log(f"Unknown provider: {provider}, falling back to Whisper")
        return _transcribe_with_whisper(task_id, input_path, model_name, language, log_callback)


def _transcribe_with_whisper(
    task_id: str,
    input_path: Path,
    model_name: Optional[str],
    language: Optional[str],
    log_callback: Optional[Callable[[str], None]],
) -> Dict[str, Any]:
    """Transcribe using OpenAI Whisper."""
    def log(msg: str):
        logger.info(f"[{task_id}] {msg}")
        if log_callback:
            log_callback(msg)

    whisper_adapter = _import_whisper_adapter()
    if whisper_adapter is None:
        raise ImportError("Whisper adapter not available. Please install: pip install openai-whisper")

    # Use default model if not specified
    if not model_name:
        model_name = whisper_adapter.DEFAULT_MODEL
        log(f"Using default Whisper model: {model_name}")

    try:
        result = whisper_adapter.transcribe_audio(
            audio_path=input_path,
            model_name=model_name,
            language=language,
            log_callback=log_callback,
        )
        return result
    except Exception as e:
        logger.error(f"[{task_id}] Whisper transcription error: {e}", exc_info=True)
        raise


def _transcribe_with_tingwu(
    task_id: str,
    input_path: Path,
    log_callback: Optional[Callable[[str], None]],
) -> Dict[str, Any]:
    """Transcribe using Alibaba Cloud Tingwu."""
    def log(msg: str):
        logger.info(f"[{task_id}] {msg}")
        if log_callback:
            log_callback(msg)

    cfg = load_config()

    # Verify Tingwu configuration
    use_tingwu = (
        os.getenv("TINGWU_ENABLED") == "1"
        and cfg.access_key_id
        and cfg.access_key_secret
        and cfg.tingwu_app_key
        and cfg.storage_provider == "oss"
        and cfg.storage_bucket
        and cfg.storage_region
    )

    if not use_tingwu:
        raise RuntimeError("Tingwu service is not properly configured. Check environment variables.")

    if not _import_tingwu_adapters():
        raise ImportError("Failed to import Tingwu adapter. Check SDK installation.")

    try:
        log("Uploading audio to OSS...")
        audio_url = upload_to_oss(cfg, input_path)
        log(f"Audio uploaded successfully")

        log("Submitting transcribe job to Tingwu...")
        job_id = submit_transcribe_job(cfg, audio_url)
        log(f"Job submitted: {job_id}")

        log("Polling for transcription result...")
        result = poll_transcribe_result(cfg, job_id)
        log(f"Transcription complete: {len(result.get('segments', []))} segments")

        return result
    except Exception as e:
        logger.error(f"[{task_id}] Tingwu transcription error: {e}", exc_info=True)
        raise


# For backward compatibility
def transcribe_legacy(task_id: str, input_path: Path) -> Dict[str, Any]:
    """Legacy transcribe function for backward compatibility."""
    return transcribe(task_id, input_path)
