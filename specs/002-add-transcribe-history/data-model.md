# Data Model: 002-Add-Transcribe-History

## Entity Relationship

```
┌─────────────────┐       ┌─────────────────┐
│   HistoryIndex  │       │  HistoryRecord  │
│  (history.json) │ 1───* │   (in records)  │
├─────────────────┤       ├─────────────────┤
│ version: str    │       │ task_id: str PK │
│ updated_at: dt  │       │ title: str      │
│ records: []     │──────>│ source_url: str │
└─────────────────┘       │ source_type: enum│
                          │ media_type: enum │
                          │ duration: int    │
                          │ file_size: int   │
                          │ tags: list[str]  │
                          │ created_at: dt   │
                          │ viewed: bool     │
                          │ thumbnail_url: str│
                          │ status: enum     │
                          └─────────────────┘
                                   │
                                   │ 1:1 (task_id)
                                   ▼
                          ┌─────────────────┐
                          │  TaskMetadata   │
                          │ (metadata.json) │
                          ├─────────────────┤
                          │ task_id: str PK │
                          │ title: str      │
                          │ source: Source  │
                          │ media: Media    │
                          │ transcription:  │
                          │   Transcription │
                          │ tags: list[str] │
                          │ created_at: dt  │
                          │ updated_at: dt  │
                          │ viewed: bool    │
                          │ status: enum    │
                          └─────────────────┘
```

---

## Entities

### 1. HistoryIndex

**File**: `artifacts/history.json`
**Purpose**: 历史记录索引，存储所有任务的摘要信息

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | string | Yes | Schema 版本号，当前 "1.0" |
| updated_at | datetime | Yes | 最后更新时间 (ISO 8601) |
| records | HistoryRecord[] | Yes | 历史记录数组 |

**Validation Rules**:
- `version` 必须是有效的语义化版本
- `updated_at` 每次修改时自动更新
- `records` 按 `created_at` 降序排列（最新在前）

---

### 2. HistoryRecord

**Location**: `history.json` 的 `records` 数组中
**Purpose**: 单条历史记录摘要

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| task_id | string | Yes | - | 唯一标识符 (UUID) |
| title | string | Yes | - | 任务标题 |
| source_url | string | No | null | 原始 URL |
| source_type | SourceType | Yes | - | 来源类型 |
| media_type | MediaType | Yes | - | 媒体类型 |
| duration | int | Yes | 0 | 时长（秒） |
| file_size | int | Yes | 0 | 文件大小（字节） |
| tags | string[] | No | [] | 关键词标签 |
| created_at | datetime | Yes | - | 创建时间 |
| viewed | bool | Yes | false | 是否已查看 |
| thumbnail_url | string | No | null | 缩略图路径 |
| status | TaskStatus | Yes | - | 任务状态 |

**Validation Rules**:
- `task_id` 必须唯一，格式为 12 位十六进制
- `title` 最大长度 200 字符
- `duration` 和 `file_size` 必须 >= 0
- `tags` 数组最多 10 个元素，每个标签最大 20 字符
- 查询时默认过滤 `status == "deleted"` 的记录

---

### 3. TaskMetadata

**File**: `artifacts/{task_id}/metadata.json`
**Purpose**: 单任务完整元数据

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | string | Yes | 唯一标识符 |
| title | string | Yes | 任务标题 |
| source | Source | Yes | 来源信息 |
| media | Media | Yes | 媒体信息 |
| transcription | Transcription | Yes | 转写信息 |
| tags | string[] | No | 关键词标签 |
| created_at | datetime | Yes | 创建时间 |
| updated_at | datetime | Yes | 更新时间 |
| viewed | bool | Yes | 是否已查看 |
| status | TaskStatus | Yes | 任务状态 |

---

## Value Objects

### Source

| Field | Type | Description |
|-------|------|-------------|
| url | string? | 原始 URL |
| type | SourceType | youtube / upload / url |
| original_filename | string? | 上传文件的原始文件名 |

### Media

| Field | Type | Description |
|-------|------|-------------|
| type | MediaType | video / audio |
| duration | int | 时长（秒） |
| file_size | int | 文件大小（字节） |
| format | string | 文件格式 (mp4/mp3/wav) |

### Transcription

| Field | Type | Description |
|-------|------|-------------|
| provider | string | 转写引擎 (whisper/tingwu) |
| model | string? | 模型名称 (whisper only) |
| language | string | 语言代码 (zh/en) |
| segments_count | int | 转写段落数 |

---

## Enums

### SourceType

```python
class SourceType(str, Enum):
    YOUTUBE = "youtube"   # YouTube 视频
    UPLOAD = "upload"     # 本地上传
    URL = "url"           # 直接 URL
```

### MediaType

```python
class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
```

### TaskStatus

```python
class TaskStatus(str, Enum):
    PENDING = "pending"         # 等待处理
    DOWNLOADING = "downloading" # 下载中
    DOWNLOADED = "downloaded"   # 下载完成
    PROCESSING = "processing"   # 转写中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    DELETED = "deleted"         # 软删除
```

---

## State Transitions

```
                    ┌──────────┐
                    │ PENDING  │
                    └────┬─────┘
                         │ download started
                         ▼
                  ┌─────────────┐
                  │ DOWNLOADING │
                  └──────┬──────┘
           success │     │ failure
                   ▼     ▼
           ┌────────────┐ ┌────────┐
           │ DOWNLOADED │ │ FAILED │
           └─────┬──────┘ └────────┘
                 │ transcribe started
                 ▼
           ┌────────────┐
           │ PROCESSING │
           └─────┬──────┘
    success │    │ failure
            ▼    ▼
    ┌───────────┐ ┌────────┐
    │ COMPLETED │ │ FAILED │
    └─────┬─────┘ └────────┘
          │ user deletes
          ▼
    ┌───────────┐
    │  DELETED  │
    └───────────┘
```

**Transition Rules**:
- 只有 `COMPLETED` 状态的记录会被写入 `history.json`
- `DELETED` 状态的记录在列表查询时被过滤
- 状态转换是单向的，不可回退（除非重新创建任务）

---

## Pydantic Models (Python)

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class SourceType(str, Enum):
    YOUTUBE = "youtube"
    UPLOAD = "upload"
    URL = "url"

class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"

class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"

class HistoryRecord(BaseModel):
    task_id: str = Field(..., min_length=12, max_length=12)
    title: str = Field(..., max_length=200)
    source_url: Optional[str] = None
    source_type: SourceType
    media_type: MediaType
    duration: int = Field(ge=0)
    file_size: int = Field(ge=0)
    tags: list[str] = Field(default_factory=list, max_length=10)
    created_at: datetime
    viewed: bool = False
    thumbnail_url: Optional[str] = None
    status: TaskStatus

class HistoryIndex(BaseModel):
    version: str = "1.0"
    updated_at: datetime
    records: list[HistoryRecord] = Field(default_factory=list)
```

---

## File Storage Layout

```
artifacts/
├── history.json                    # HistoryIndex
├── abc123def456/
│   ├── metadata.json               # TaskMetadata
│   ├── result.srt                  # SRT 字幕
│   ├── result.md                   # Markdown 文稿
│   ├── result.json                 # 结构化转写数据
│   ├── audio.mp3                   # 处理后音频
│   └── thumbnail.jpg               # 视频缩略图 (optional)
└── xyz789ghi012/
    └── ...
```
