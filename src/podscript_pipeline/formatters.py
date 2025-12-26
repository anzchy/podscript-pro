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
    """
    Convert transcript to Markdown format with speaker labels and timestamps.

    Output format (with speaker diarization - Tingwu):
    发言人1  00:16
    你觉得站在2025年的尾巴上，你有嗅到泡沫的味道没有？

    发言人2  00:22
    人类历史上每次技术革命都带来了泡沫...

    Output format (without speaker diarization - Whisper):
    00:00
    At the beginning of my day.

    00:05
    I literally just write today.
    """
    segments = transcript.get("segments", [])

    # If no segments, fall back to plain text
    if not segments:
        text = transcript.get("text", "")
        return f"# 转写结果\n\n{text}\n"

    # Check if any segment has speaker info
    has_speaker_info = any(seg.get("speaker", "") for seg in segments)

    lines = ["# 转写结果\n"]
    last_speaker = None

    for seg in segments:
        speaker = seg.get("speaker", "")
        start = seg.get("start", 0)
        text = seg.get("text", "").strip()

        if not text:
            continue

        # Format timestamp as MM:SS
        timestamp = _format_timestamp_short(start)

        if has_speaker_info:
            # With speaker diarization: group by speaker
            speaker_label = f"发言人{speaker}" if speaker else "发言人"

            if speaker != last_speaker or last_speaker is None:
                lines.append(f"\n{speaker_label}  {timestamp}")
                lines.append(text)
                last_speaker = speaker
            else:
                # Same speaker - append to previous paragraph
                lines.append(text)
        else:
            # Without speaker diarization: show each segment with timestamp
            lines.append(f"\n{timestamp}")
            lines.append(text)

    return "\n".join(lines) + "\n"


def _format_timestamp_short(seconds: float) -> str:
    """Format seconds to MM:SS format."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02}:{s:02}"


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