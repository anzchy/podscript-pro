from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, HttpUrl, Field


class TaskStatus(str, Enum):
    queued = "queued"
    downloading = "downloading"
    downloaded = "downloaded"  # Download complete, waiting for transcription
    transcribing = "transcribing"
    formatting = "formatting"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"


class TaskCreateRequest(BaseModel):
    source_url: HttpUrl
    platform: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class TaskSummary(BaseModel):
    id: str
    status: TaskStatus
    progress: Optional[float] = Field(default=None, description="0.0 - 1.0")
    error: Optional[Dict[str, Any]] = None


class TaskResults(BaseModel):
    srt_url: Optional[str] = None
    markdown_url: Optional[str] = None
    meta: Dict[str, Any] = {}


class TaskLog(BaseModel):
    time: str
    level: str  # info, warn, error
    message: str


class TranscriptSegment(BaseModel):
    """A single transcript segment for streaming display."""
    start: float
    end: float
    text: str
    speaker: str = ""


class TaskDetail(BaseModel):
    id: str
    status: TaskStatus
    progress: Optional[float] = None
    error: Optional[Dict[str, Any]] = None
    results: Optional[TaskResults] = None
    audio_path: Optional[str] = None  # Path to downloaded audio file
    logs: List[TaskLog] = []  # Task execution logs
    partial_segments: List[TranscriptSegment] = []  # Streaming transcript segments


class AppConfig(BaseModel):
    # Alibaba Cloud credentials (for OSS and Tingwu)
    access_key_id: Optional[str] = None
    access_key_secret: Optional[str] = None
    security_token: Optional[str] = None

    # Tencent Cloud credentials (for COS)
    tencent_secret_id: Optional[str] = None
    tencent_secret_key: Optional[str] = None

    # Storage config (provider: 'oss' or 'cos')
    storage_provider: Optional[str] = None  # 'oss' = Alibaba OSS, 'cos' = Tencent COS
    storage_bucket: Optional[str] = None
    storage_prefix: Optional[str] = None  # Folder path prefix, e.g., 'audio/tingwu'
    storage_public_host: Optional[str] = None
    storage_region: Optional[str] = None
    storage_endpoint: Optional[str] = None

    # API keys
    qwen_api_key: Optional[str] = None
    tingwu_app_key: Optional[str] = None  # Tingwu AppKey from console
    artifacts_dir: str = "artifacts"