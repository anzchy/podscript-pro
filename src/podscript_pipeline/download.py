import os
import socket
import logging
from typing import Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Timeout configurations
DOWNLOAD_SOCKET_TIMEOUT = 30  # seconds per network request
DOWNLOAD_RETRIES = 3
THUMBNAIL_TIMEOUT = 10  # seconds for thumbnail download


def _is_direct_audio_url(url: str) -> bool:
    """Check if URL points directly to an audio file."""
    u = url.lower()
    audio_extensions = ('.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma')
    return any(u.endswith(ext) or f'{ext}?' in u for ext in audio_extensions)


def _download_thumbnail(info: dict, task_dir: Path) -> None:
    """Download video thumbnail image with timeout."""
    try:
        import urllib.request

        thumbnail_url = info.get("thumbnail")
        if not thumbnail_url:
            thumbnails = info.get("thumbnails", [])
            if thumbnails:
                thumbnail_url = thumbnails[-1].get("url")  # Highest quality

        if thumbnail_url:
            # Set timeout for thumbnail download
            old_timeout = socket.getdefaulttimeout()
            try:
                socket.setdefaulttimeout(THUMBNAIL_TIMEOUT)
                thumbnail_path = task_dir / "thumbnail.jpg"
                urllib.request.urlretrieve(thumbnail_url, thumbnail_path)
                logger.info(f"Thumbnail downloaded: {thumbnail_path}")
            finally:
                socket.setdefaulttimeout(old_timeout)
    except Exception as e:
        logger.warning(f"Thumbnail download failed (non-fatal): {e}")


def _download_direct_audio(url: str, task_dir: Path) -> Tuple[Path, str]:
    """Download audio file directly from URL."""
    import httpx
    from urllib.parse import urlparse, unquote

    logger.info(f"Downloading direct audio URL: {url[:80]}...")

    # Extract filename from URL
    parsed = urlparse(url)
    filename = unquote(Path(parsed.path).name) or "audio.mp3"

    # Ensure valid extension
    if not any(filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']):
        filename = "audio.mp3"

    audio_path = task_dir / filename

    with httpx.Client(timeout=300, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        audio_path.write_bytes(response.content)

    # Determine MIME type
    mime_map = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        '.flac': 'audio/flac',
        '.ogg': 'audio/ogg',
    }
    ext = audio_path.suffix.lower()
    mime_type = mime_map.get(ext, 'audio/mpeg')

    logger.info(f"Direct audio downloaded: {audio_path} ({mime_type})")
    return audio_path, mime_type


def download_source(task_id: str, source_url: str, artifacts_dir: str) -> Tuple[Path, str]:
    """
    Download audio/video from URL using yt-dlp.

    Supports 1000+ sites including YouTube, Bilibili, Vimeo, Twitter, etc.
    Falls back to direct download for direct audio URLs.

    Args:
        task_id: Unique task identifier
        source_url: URL to download from
        artifacts_dir: Directory to store downloaded files

    Returns:
        Tuple of (audio_path, mime_type)

    Raises:
        RuntimeError: If download fails
    """
    task_dir = Path(artifacts_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    # Handle direct audio URLs
    if _is_direct_audio_url(source_url):
        try:
            return _download_direct_audio(source_url, task_dir)
        except Exception as e:
            logger.error(f"Direct audio download failed: {e}")
            raise RuntimeError(f"音频下载失败: {e}")

    # Use yt-dlp for video sites (supports 1000+ sites including Bilibili, YouTube, etc.)
    try:
        import yt_dlp  # type: ignore

        logger.info(f"[{task_id}] Starting yt-dlp download for: {source_url[:80]}...")

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
            "quiet": False,
            "no_warnings": False,
            "nocheckcertificate": True,

            # Timeout and retry configurations (P0-2 fix)
            "socket_timeout": DOWNLOAD_SOCKET_TIMEOUT,
            "retries": DOWNLOAD_RETRIES,
            "fragment_retries": DOWNLOAD_RETRIES,
            "extractor_retries": DOWNLOAD_RETRIES,
            "file_access_retries": DOWNLOAD_RETRIES,
            "http_chunk_size": 10485760,  # 10MB chunks

            # Use cookies from browser (optional, for sites requiring login)
            "cookiesfrombrowser": (
                os.getenv("YTDLP_COOKIES_BROWSER", "chrome"),
                None,  # keyring
                None,  # profile
                None,  # container
            ) if os.getenv("YTDLP_USE_COOKIES", "").lower() in ("1", "true") else None,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First try to extract info to check if URL is supported
            logger.info(f"[{task_id}] Extracting info from URL...")
            info = ydl.extract_info(source_url, download=True)

            if info is None:
                raise RuntimeError("无法解析此链接，请检查链接是否正确")

            base = ydl.prepare_filename(info)
            audio_path = Path(base).with_suffix(".mp3")

            # Download thumbnail (P0-3: with timeout)
            _download_thumbnail(info, task_dir)

            # Check if audio file exists
            if audio_path.exists():
                logger.info(f"[{task_id}] Download complete: {audio_path}")
                return audio_path, "audio/mpeg"

            # Sometimes the file has original extension
            for ext in [".m4a", ".webm", ".mp4", ".wav", ".ogg"]:
                alt_path = Path(base).with_suffix(ext)
                if alt_path.exists():
                    logger.info(f"[{task_id}] Found audio at: {alt_path}")
                    return alt_path, "audio/mpeg"

            # Check for any audio files in task_dir
            for audio_file in task_dir.glob("audio.*"):
                if audio_file.suffix.lower() in [".mp3", ".m4a", ".webm", ".wav", ".ogg", ".mp4"]:
                    logger.info(f"[{task_id}] Found audio file: {audio_file}")
                    return audio_file, "audio/mpeg"

            raise RuntimeError("下载完成但未找到音频文件")

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"[{task_id}] yt-dlp DownloadError: {error_msg}")

        # Provide user-friendly error messages
        if "Unsupported URL" in error_msg:
            raise RuntimeError(f"不支持的链接格式，请检查链接是否正确")
        elif "Video unavailable" in error_msg or "Private video" in error_msg:
            raise RuntimeError("视频不可用（可能是私密视频或已被删除）")
        elif "Sign in" in error_msg or "login" in error_msg.lower():
            raise RuntimeError("此视频需要登录才能观看")
        elif "Geographic restriction" in error_msg or "not available in your country" in error_msg:
            raise RuntimeError("此视频在当前地区不可用")
        elif "HTTP Error 403" in error_msg:
            raise RuntimeError("访问被拒绝（HTTP 403），可能需要登录或视频有访问限制")
        elif "HTTP Error 404" in error_msg:
            raise RuntimeError("视频不存在（HTTP 404），请检查链接是否正确")
        elif "Connection" in error_msg or "timed out" in error_msg.lower():
            raise RuntimeError("网络连接超时，请稍后重试")
        else:
            raise RuntimeError(f"下载失败: {error_msg[:200]}")

    except yt_dlp.utils.ExtractorError as e:
        logger.error(f"[{task_id}] yt-dlp ExtractorError: {e}")
        raise RuntimeError(f"无法解析此链接: {str(e)[:200]}")

    except Exception as e:
        logger.error(f"[{task_id}] Download failed: {e}", exc_info=True)
        raise RuntimeError(f"下载失败: {str(e)[:200]}")
