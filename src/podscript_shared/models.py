from datetime import datetime
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


# ============== History Feature Models ==============

class SourceType(str, Enum):
    """Source type for transcription tasks."""
    YOUTUBE = "youtube"
    UPLOAD = "upload"
    URL = "url"


class MediaType(str, Enum):
    """Media type for transcription tasks."""
    VIDEO = "video"
    AUDIO = "audio"


class HistoryStatus(str, Enum):
    """Status enum for history records (separate from TaskStatus for clarity)."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class HistoryRecord(BaseModel):
    """A single history record in the history index."""
    task_id: str = Field(..., min_length=1, description="Unique task identifier")
    title: str = Field(..., max_length=200, description="Task title")
    source_url: Optional[str] = Field(default=None, description="Original URL")
    source_type: SourceType = Field(..., description="Source type")
    media_type: MediaType = Field(..., description="Media type")
    duration: int = Field(default=0, ge=0, description="Duration in seconds")
    file_size: int = Field(default=0, ge=0, description="File size in bytes")
    tags: List[str] = Field(default_factory=list, description="Keywords/tags")
    created_at: datetime = Field(..., description="Creation time")
    viewed: bool = Field(default=False, description="Whether record has been viewed")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL")
    status: HistoryStatus = Field(..., description="Record status")


class HistoryIndex(BaseModel):
    """The history index containing all history records."""
    version: str = Field(default="1.0", description="Schema version")
    updated_at: datetime = Field(..., description="Last update time")
    records: List[HistoryRecord] = Field(default_factory=list, description="History records")


class HistoryListResponse(BaseModel):
    """Response for GET /history endpoint."""
    total: int = Field(..., description="Total record count")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Records per page")
    records: List[HistoryRecord] = Field(..., description="History records")


class HistoryUpdateRequest(BaseModel):
    """Request body for PATCH /history/{task_id}."""
    viewed: Optional[bool] = Field(default=None, description="Mark as viewed")
    tags: Optional[List[str]] = Field(default=None, description="Update tags")