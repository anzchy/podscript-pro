import logging
from pathlib import Path
from typing import Dict, Any, Tuple

from podscript_pipeline.download import download_source
from podscript_pipeline.preprocess import preprocess
from podscript_pipeline.asr import transcribe, get_available_providers, ASR_PROVIDER_WHISPER
from podscript_pipeline.formatters import to_srt, to_markdown, persist_results

logger = logging.getLogger(__name__)


def run_download_only(task_id: str, source_url: str, artifacts_dir: str) -> Tuple[str, str]:
    """
    Download audio from URL only (step 1).
    Returns: (audio_path, mime_type)
    """
    logger.info(f"[{task_id}] run_download_only: source_url={source_url}")
    task_dir = Path(artifacts_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    downloaded, mime = download_source(task_id, source_url, artifacts_dir)
    logger.info(f"[{task_id}] run_download_only: downloaded={downloaded}, mime={mime}")
    return str(downloaded), mime


def run_transcribe_only(
    task_id: str,
    audio_path: str,
    artifacts_dir: str,
    mime_type: str = "audio/mpeg",
    provider: str = ASR_PROVIDER_WHISPER,
    model_name: str = None,
    language: str = None,
    prompt: str = None,
    log_callback=None,
) -> Dict[str, Any]:
    """
    Transcribe audio file only (step 2).

    Args:
        task_id: Unique task identifier
        audio_path: Path to the audio file
        artifacts_dir: Directory to store results
        mime_type: MIME type of the audio
        provider: ASR provider ('whisper' or 'tingwu')
        model_name: Model name (for Whisper)
        language: Language code (e.g., 'zh', 'en') or None for auto-detect
        prompt: Custom prompt for transcription:
            - Whisper: initial_prompt for vocabulary/style (max ~900 chars)
            - Tingwu: custom prompt for LLM post-processing
        log_callback: Optional callback for progress logging

    Returns:
        result dict with srt_path, md_path, meta
    """
    def log(msg: str):
        logger.info(f"[{task_id}] {msg}")
        if log_callback:
            log_callback(msg)

    log(f"run_transcribe_only: audio_path={audio_path}, provider={provider}, model={model_name}")
    task_dir = Path(artifacts_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(audio_path)

    log("Preprocessing audio...")
    processed, _ = preprocess(task_id, input_path, mime_type)
    log(f"Preprocessed: {processed}")

    log(f"Starting ASR transcription with {provider}...")
    transcript = transcribe(
        task_id=task_id,
        input_path=processed,
        provider=provider,
        model_name=model_name,
        language=language,
        prompt=prompt,
        log_callback=log_callback,
    )
    log(f"ASR complete, segments={len(transcript.get('segments', []))}")

    log("Formatting results...")
    srt_text = to_srt(transcript)
    md_text = to_markdown(transcript)
    srt_path, md_path = persist_results(task_dir, srt_text, md_text)
    log(f"Results saved: srt={srt_path}, md={md_path}")

    return {"srt_path": str(srt_path), "md_path": str(md_path), "meta": {"segments": len(transcript.get("segments", []))}}


def run_pipeline(task_id: str, source_url: str, artifacts_dir: str) -> Dict[str, Any]:
    """Full pipeline: download + transcribe (legacy, for backward compatibility)."""
    task_dir = Path(artifacts_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    downloaded, mime = download_source(task_id, source_url, artifacts_dir)
    processed, _ = preprocess(task_id, downloaded, mime)
    transcript = transcribe(task_id, processed)

    srt_text = to_srt(transcript)
    md_text = to_markdown(transcript)
    srt_path, md_path = persist_results(task_dir, srt_text, md_text)

    return {"srt_path": str(srt_path), "md_path": str(md_path), "meta": {"segments": len(transcript.get("segments", []))}}


def run_pipeline_from_file(task_id: str, local_path: str, artifacts_dir: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
    """Full pipeline from local file (legacy, for backward compatibility)."""
    task_dir = Path(artifacts_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(local_path)
    processed, _ = preprocess(task_id, input_path, content_type)
    transcript = transcribe(task_id, processed)
    srt_text = to_srt(transcript)
    md_text = to_markdown(transcript)
    srt_path, md_path = persist_results(task_dir, srt_text, md_text)
    return {"srt_path": str(srt_path), "md_path": str(md_path), "meta": {"segments": len(transcript.get("segments", []))}}