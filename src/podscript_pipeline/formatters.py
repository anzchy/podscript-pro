from pathlib import Path
from typing import Dict, Any, Tuple


def to_srt(transcript: Dict[str, Any]) -> str:
    lines = []
    for i, seg in enumerate(transcript.get("segments", []), start=1):
        start = _format_ts(seg["start"])  # type: ignore[index]
        end = _format_ts(seg["end"])  # type: ignore[index]
        text = seg["text"]  # type: ignore[index]
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def to_markdown(transcript: Dict[str, Any]) -> str:
    text = transcript.get("text", "")
    return f"# 转写结果\n\n{text}\n"


def persist_results(task_dir: Path, srt_text: str, md_text: str) -> Tuple[Path, Path]:
    srt_path = task_dir / "result.srt"
    md_path = task_dir / "result.md"
    srt_path.write_text(srt_text)
    md_path.write_text(md_text)
    return srt_path, md_path


def _format_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"