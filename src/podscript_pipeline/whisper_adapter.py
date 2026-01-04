"""
OpenAI Whisper adapter for offline audio transcription.
Docs: https://github.com/openai/whisper
"""
import logging
import os
import sys
import io
import re
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class TqdmProgressCapture:
    """Capture tqdm progress output and send to callback."""

    def __init__(self, callback: Optional[Callable[[str], None]] = None, throttle_percent: int = 5):
        self.callback = callback
        self.throttle_percent = throttle_percent  # Only report every N percent
        self.last_reported_percent = -1
        self.buffer = ""
        self._original_stderr = None
        self._pipe_read = None
        self._pipe_write = None
        self._reader_thread = None
        self._stop_event = threading.Event()

    def __enter__(self):
        if not self.callback:
            return self

        # Create a pipe to capture stderr
        self._pipe_read, self._pipe_write = os.pipe()
        self._original_stderr = os.dup(sys.stderr.fileno())

        # Redirect stderr to our pipe
        os.dup2(self._pipe_write, sys.stderr.fileno())

        # Start a thread to read from the pipe
        self._stop_event.clear()
        self._reader_thread = threading.Thread(target=self._read_progress, daemon=True)
        self._reader_thread.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.callback or self._original_stderr is None:
            return

        # Restore stderr
        os.dup2(self._original_stderr, sys.stderr.fileno())
        os.close(self._original_stderr)

        # Stop the reader thread
        self._stop_event.set()
        os.close(self._pipe_write)

        if self._reader_thread:
            self._reader_thread.join(timeout=1.0)

        os.close(self._pipe_read)

    def _read_progress(self):
        """Read progress from pipe and parse tqdm output."""
        try:
            while not self._stop_event.is_set():
                # Read available data
                data = os.read(self._pipe_read, 4096)
                if not data:
                    break

                text = data.decode('utf-8', errors='ignore')
                self._parse_progress(text)
        except OSError:
            pass  # Pipe closed

    def _parse_progress(self, text: str):
        """Parse tqdm progress bar output."""
        # tqdm format: "10%|██        | 51300/521970 [00:17<02:46, 2825.41frames/s]"
        # Match percentage and frame info
        pattern = r'(\d+)%\|[^|]*\|\s*(\d+)/(\d+)\s*\[([^\]]+)\]'
        matches = re.findall(pattern, text)

        for match in matches:
            percent, current, total, time_info = match
            percent_int = int(percent)

            # Throttle: only report if percent changed by threshold or at 100%
            if percent_int - self.last_reported_percent >= self.throttle_percent or percent_int == 100:
                self.last_reported_percent = percent_int
                # Format: "转写进度: 10% (51300/521970) [00:17<02:46]"
                progress_msg = f"转写进度: {percent}% ({current}/{total}) [{time_info}]"
                if self.callback:
                    self.callback(progress_msg)

# Available Whisper models with their properties
WHISPER_MODELS = {
    "tiny": {"params": "39M", "vram": "~1GB", "speed": "~10x", "multilingual": True},
    "tiny.en": {"params": "39M", "vram": "~1GB", "speed": "~10x", "multilingual": False},
    "base": {"params": "74M", "vram": "~1GB", "speed": "~7x", "multilingual": True},
    "base.en": {"params": "74M", "vram": "~1GB", "speed": "~7x", "multilingual": False},
    "small": {"params": "244M", "vram": "~2GB", "speed": "~4x", "multilingual": True},
    "small.en": {"params": "244M", "vram": "~2GB", "speed": "~4x", "multilingual": False},
    "medium": {"params": "769M", "vram": "~5GB", "speed": "~2x", "multilingual": True},
    "medium.en": {"params": "769M", "vram": "~5GB", "speed": "~2x", "multilingual": False},
    "large": {"params": "1550M", "vram": "~10GB", "speed": "1x", "multilingual": True},
    "turbo": {"params": "809M", "vram": "~6GB", "speed": "~8x", "multilingual": True},
}

# Default model to use
DEFAULT_MODEL = "base"

# Cache for loaded models
_model_cache: Dict[str, Any] = {}


def get_available_models() -> Dict[str, Dict[str, Any]]:
    """Return information about available Whisper models."""
    return WHISPER_MODELS.copy()


def get_model_download_path(model_name: str) -> Path:
    """Get the path where Whisper models are downloaded."""
    # Whisper downloads models to ~/.cache/whisper by default
    cache_dir = Path.home() / ".cache" / "whisper"
    return cache_dir


def is_model_downloaded(model_name: str) -> bool:
    """Check if a Whisper model is already downloaded."""
    cache_dir = get_model_download_path(model_name)
    # Whisper model files are named like "tiny.pt", "base.pt", etc.
    model_file = cache_dir / f"{model_name}.pt"
    return model_file.exists()


def get_downloaded_models() -> list:
    """Get list of models that are already downloaded."""
    cache_dir = get_model_download_path("")
    downloaded = []
    if cache_dir.exists():
        for model_name in WHISPER_MODELS.keys():
            model_file = cache_dir / f"{model_name}.pt"
            if model_file.exists():
                downloaded.append(model_name)
    return downloaded


def load_model(model_name: str = DEFAULT_MODEL, device: Optional[str] = None):
    """
    Load a Whisper model (downloads if not cached).

    Args:
        model_name: Name of the model (tiny, base, small, medium, large, turbo)
        device: Device to load model on (cuda, cpu, or None for auto-detect)

    Returns:
        Loaded Whisper model
    """
    import whisper

    if model_name not in WHISPER_MODELS:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(WHISPER_MODELS.keys())}")

    cache_key = f"{model_name}_{device}"
    if cache_key in _model_cache:
        logger.info(f"Using cached model: {model_name}")
        return _model_cache[cache_key]

    logger.info(f"Loading Whisper model: {model_name} (device={device or 'auto'})")
    model = whisper.load_model(model_name, device=device)
    _model_cache[cache_key] = model
    logger.info(f"Model {model_name} loaded successfully")

    return model


def transcribe_audio(
    audio_path: Path,
    model_name: str = DEFAULT_MODEL,
    language: Optional[str] = None,
    task: str = "transcribe",
    initial_prompt: Optional[str] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Transcribe audio file using Whisper.

    Args:
        audio_path: Path to the audio file
        model_name: Whisper model to use
        language: Language code (e.g., 'zh', 'en') or None for auto-detect
        task: 'transcribe' or 'translate' (translate to English)
        initial_prompt: Optional prompt to guide transcription style or vocabulary.
            Useful for:
            - Technical terms: "术语：Kubernetes, Docker, CI/CD"
            - Speaker marking: "对话有两位发言人"
            - Style guidance: "这是一个播客访谈节目"
            Max ~224 tokens (~900 characters).
        log_callback: Optional callback for progress logging

    Returns:
        Dict with transcription results:
        - text: Full transcription text
        - segments: List of segments with start, end, text
        - language: Detected or specified language
    """
    import whisper

    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    log(f"Loading Whisper model: {model_name}...")
    model = load_model(model_name)

    log(f"Starting transcription of {audio_path.name}...")

    # Transcribe with Whisper
    options = {
        "task": task,
        "verbose": True,  # Enable verbose mode to get progress bar
    }
    if language:
        options["language"] = language
    if initial_prompt:
        options["initial_prompt"] = initial_prompt
        log(f"Using initial prompt: {initial_prompt[:50]}...")

    # Capture progress from tqdm and send to callback
    with TqdmProgressCapture(callback=log_callback):
        result = model.transcribe(str(audio_path), **options)

    detected_lang = result.get("language", language or "unknown")
    log(f"Detected language: {detected_lang}")

    # Parse segments
    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": float(seg.get("start", 0)),
            "end": float(seg.get("end", 0)),
            "text": seg.get("text", "").strip(),
            "speaker": "",  # Whisper doesn't do speaker diarization
        })

    log(f"Transcription complete: {len(segments)} segments")

    return {
        "text": result.get("text", "").strip(),
        "segments": segments,
        "language": detected_lang,
    }


def download_model(model_name: str, log_callback: Optional[Callable[[str], None]] = None) -> bool:
    """
    Download a Whisper model (if not already downloaded).

    Args:
        model_name: Name of the model to download
        log_callback: Optional callback for progress logging

    Returns:
        True if successful
    """
    import whisper

    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    if model_name not in WHISPER_MODELS:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(WHISPER_MODELS.keys())}")

    if is_model_downloaded(model_name):
        log(f"Model {model_name} is already downloaded")
        return True

    log(f"Downloading Whisper model: {model_name}...")
    log(f"Model size: {WHISPER_MODELS[model_name]['params']}, VRAM: {WHISPER_MODELS[model_name]['vram']}")

    # Loading the model will trigger download if not cached
    whisper.load_model(model_name)

    log(f"Model {model_name} downloaded successfully")
    return True


if __name__ == "__main__":
    # Test the adapter
    logging.basicConfig(level=logging.INFO)

    print("Available models:", list(WHISPER_MODELS.keys()))
    print("Downloaded models:", get_downloaded_models())

    # Example transcription (uncomment to test)
    # result = transcribe_audio(Path("test.mp3"), model_name="base")
    # print(result)
