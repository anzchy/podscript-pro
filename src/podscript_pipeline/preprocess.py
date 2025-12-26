from pathlib import Path
from typing import Tuple


def preprocess(task_id: str, input_path: Path, mime: str) -> Tuple[Path, str]:
    suffix = input_path.suffix.lower()
    is_media = suffix in {".mp4", ".mp3", ".wav", ".m4a", ".aac", ".flac"} or (
        mime.startswith("audio/") or mime.startswith("video/")
    )
    if is_media and input_path.exists():
        return input_path, mime
    processed = input_path.parent / "processed.txt"
    processed.write_text(f"processed_from={input_path.name}\n")
    return processed, mime