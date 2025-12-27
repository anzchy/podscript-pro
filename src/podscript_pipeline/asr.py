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
upload_audio = None
submit_transcribe_job = None
poll_transcribe_result = None


def _import_tingwu_adapters():
    global upload_audio, submit_transcribe_job, poll_transcribe_result
    try:
        from podscript_pipeline.storage import upload_audio as _upload_audio
        from podscript_pipeline.tingwu_adapter import (
            submit_transcribe_job as _submit_transcribe_job,
            poll_transcribe_result as _poll_transcribe_result
        )
        upload_audio = _upload_audio
        submit_transcribe_job = _submit_transcribe_job
        poll_transcribe_result = _poll_transcribe_result
        return True
    except ImportError as e:
        logger.warning(f"Failed to import tingwu adapters: {e}")
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
    # Tingwu requires: credentials, app key, and storage (OSS or COS)
    storage_ok = (
        cfg.storage_provider in ("oss", "cos")
        and cfg.storage_bucket
        and cfg.storage_region
    )
    tingwu_available = bool(
        os.getenv("TINGWU_ENABLED") == "1"
        and cfg.access_key_id
        and cfg.access_key_secret
        and cfg.tingwu_app_key
        and storage_ok
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
    prompt: Optional[str] = None,
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
        prompt: Optional prompt to guide transcription:
            - Whisper: initial_prompt for vocabulary/style hints (~900 chars max)
            - Tingwu: custom prompt for LLM post-processing
        log_callback: Optional callback for progress logging

    Returns:
        Dict with transcription results
    """
    def log(msg: str):
        logger.info(f"[{task_id}] {msg}")
        if log_callback:
            log_callback(msg)

    log(f"transcribe() called with provider={provider}, model={model_name}, path={input_path}")
    if prompt:
        log(f"Using custom prompt: {prompt[:50]}...")

    if provider == ASR_PROVIDER_WHISPER:
        return _transcribe_with_whisper(task_id, input_path, model_name, language, prompt, log_callback)
    elif provider == ASR_PROVIDER_TINGWU:
        return _transcribe_with_tingwu(task_id, input_path, prompt, log_callback)
    else:
        log(f"Unknown provider: {provider}, falling back to Whisper")
        return _transcribe_with_whisper(task_id, input_path, model_name, language, prompt, log_callback)


def _transcribe_with_whisper(
    task_id: str,
    input_path: Path,
    model_name: Optional[str],
    language: Optional[str],
    prompt: Optional[str],
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
            initial_prompt=prompt,
            log_callback=log_callback,
        )
        return result
    except Exception as e:
        logger.error(f"[{task_id}] Whisper transcription error: {e}", exc_info=True)
        raise


def _transcribe_with_tingwu(
    task_id: str,
    input_path: Path,
    prompt: Optional[str],
    log_callback: Optional[Callable[[str], None]],
) -> Dict[str, Any]:
    """Transcribe using Alibaba Cloud Tingwu."""
    def log(msg: str):
        logger.info(f"[{task_id}] {msg}")
        if log_callback:
            log_callback(msg)

    cfg = load_config()

    # Verify Tingwu configuration
    # Supports both Alibaba OSS and Tencent COS for storage
    storage_ok = (
        cfg.storage_provider in ("oss", "cos")
        and cfg.storage_bucket
        and cfg.storage_region
    )
    use_tingwu = (
        os.getenv("TINGWU_ENABLED") == "1"
        and cfg.access_key_id
        and cfg.access_key_secret
        and cfg.tingwu_app_key
        and storage_ok
    )

    if not use_tingwu:
        raise RuntimeError("Tingwu service is not properly configured. Check environment variables.")

    if not _import_tingwu_adapters():
        raise ImportError("Failed to import Tingwu adapter. Check SDK installation.")

    # Get storage provider name for logging
    from podscript_pipeline.storage import get_storage_provider_name
    storage_name = get_storage_provider_name(cfg)

    try:
        log(f"Uploading audio to {storage_name}...")
        audio_url = upload_audio(cfg, input_path)
        log(f"Audio uploaded successfully")

        log("Submitting transcribe job to Tingwu...")
        job_id = submit_transcribe_job(cfg, audio_url, custom_prompt=prompt)
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
