import os
from typing import Tuple
from pathlib import Path


def _is_youtube(url: str) -> bool:
    u = url.lower()
    return ("youtube.com/watch" in u) or ("youtu.be/" in u)


def _download_thumbnail(info: dict, task_dir: Path) -> None:
    """Download YouTube thumbnail image (T041)."""
    try:
        import urllib.request

        thumbnail_url = info.get("thumbnail")
        if not thumbnail_url:
            thumbnails = info.get("thumbnails", [])
            if thumbnails:
                thumbnail_url = thumbnails[-1].get("url")  # Highest quality

        if thumbnail_url:
            thumbnail_path = task_dir / "thumbnail.jpg"
            urllib.request.urlretrieve(thumbnail_url, thumbnail_path)
    except Exception as e:
        print(f"Thumbnail download failed (non-fatal): {e}")


def download_source(task_id: str, source_url: str, artifacts_dir: str) -> Tuple[Path, str]:
    task_dir = Path(artifacts_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    if _is_youtube(source_url):
        try:
            import yt_dlp  # type: ignore

            outtmpl = str(task_dir / "audio.%(ext)s")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "quiet": False,  # Show progress for debugging
                "no_warnings": False,
                "nocheckcertificate": True,
                # Use cookies from browser to bypass bot detection
                # Priority: YTDLP_COOKIES_BROWSER env var > chrome > safari > firefox
                "cookiesfrombrowser": (
                    os.getenv("YTDLP_COOKIES_BROWSER", "chrome"),
                    None,  # keyring
                    None,  # profile
                    None,  # container
                ),
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source_url, download=True)
                base = ydl.prepare_filename(info)
                audio_path = Path(base).with_suffix(".mp3")

                # Download thumbnail (T041)
                _download_thumbnail(info, task_dir)

                if audio_path.exists():
                    return audio_path, "audio/mpeg"
        except Exception as e:
            print(f"yt-dlp download failed: {e}")
            # Re-raise to show error in task status instead of returning stub
            raise RuntimeError(f"YouTube download failed: {e}")

    downloaded = task_dir / "download.txt"
    downloaded.write_text(f"source_url={source_url}\n")
    return downloaded, "text/plain"