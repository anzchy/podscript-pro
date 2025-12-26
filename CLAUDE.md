# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Podscript is a podcast/audio-video transcription application. Users submit URLs (including YouTube links), and the system downloads, preprocesses, transcribes (via Alibaba Cloud Tingwu ASR), and outputs SRT/Markdown files.

**Python requirement:** 3.10 - 3.12 (3.9 has SSL compatibility issues with yt-dlp)

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run tests (80% coverage required)
PYTHONPATH=./src pytest --disable-warnings --maxfail=1

# Run tests with coverage report
PYTHONPATH=./src pytest --cov=src/podscript_api --cov=src/podscript_pipeline --cov=src/podscript_shared --cov-report=term-missing

# Run single test file
PYTHONPATH=./src pytest tests/test_api.py -v

# Start API server (default port 8001)
PYTHONPATH=./src uvicorn podscript_api.main:app --port 8001

# Linting/formatting (dev dependencies)
black .
isort .
flake8
mypy src/
```

## Architecture

Three modular packages under `src/`:

```
src/
├── podscript_api/         # FastAPI gateway
│   ├── main.py            # API endpoints, task management, static file serving
│   └── static/            # Frontend UI (HTML/JS/CSS)
├── podscript_pipeline/    # Processing pipeline
│   ├── pipeline.py        # Orchestrates: download → preprocess → transcribe → format
│   ├── download.py        # URL download, YouTube via yt-dlp
│   ├── preprocess.py      # Audio preprocessing
│   ├── asr.py             # ASR dispatch (Tingwu or stub)
│   ├── tingwu_adapter.py  # Alibaba Cloud Tingwu integration (OSS upload + job polling)
│   └── formatters.py      # SRT/Markdown generation
└── podscript_shared/      # Shared utilities
    ├── models.py          # Pydantic models (TaskStatus, TaskDetail, AppConfig, etc.)
    └── config.py          # Environment config loader (.env support)
```

**Data Flow:**
1. `POST /tasks` creates a background task
2. Pipeline: download_source → preprocess → transcribe → to_srt/to_markdown → persist_results
3. Results stored in `artifacts/{task_id}/` (result.srt, result.md)
4. Frontend polls `GET /tasks/{id}` for status, downloads from `/artifacts/{id}/result.*`

## Key Patterns

- **Task state stored in-memory** (`TASKS` dict in main.py) — not persistent across restarts
- **Background processing** via FastAPI's `BackgroundTasks`
- **Tingwu integration** requires `TINGWU_ENABLED=1` plus valid Alibaba Cloud credentials and OSS bucket
- **Tingwu SDK**: Uses `aliyun-python-sdk-core` with CommonRequest (API version 2023-09-30)
- **Fallback stub mode** when Tingwu disabled — returns placeholder transcript for local testing
- **YouTube handling** requires:
  - `yt-dlp`, `ffmpeg`, and `deno` installed (`brew install ffmpeg deno` on macOS)
  - Browser cookies for authentication (defaults to Chrome, set `YTDLP_COOKIES_BROWSER=safari` for Safari)

## Environment Variables (.env)

Required for Tingwu integration:
```
ALIBABA_CLOUD_ACCESS_KEY_ID=...
ALIBABA_CLOUD_ACCESS_KEY_SECRET=...
TINGWU_APP_KEY=...              # Required: AppKey from Tingwu console
STORAGE_PROVIDER=oss
STORAGE_BUCKET=...
STORAGE_REGION=cn-shanghai
TINGWU_ENABLED=1
```

Get `TINGWU_APP_KEY` from: https://tingwu.console.aliyun.com/

Optional:
- `ARTIFACTS_DIR` — output directory (default: `artifacts`)
- `ALIBABA_CLOUD_SECURITY_TOKEN` — for STS temporary credentials

## API Endpoints

- `POST /tasks` — Create transcription task from URL
- `POST /tasks/upload` — Create task from uploaded file
- `GET /tasks/{id}` — Get task status/progress
- `GET /tasks/{id}/results` — Get result URLs (srt_url, markdown_url)
- `GET /artifacts/{id}/*` — Static file serving for outputs
- `GET /` — Web UI

## Testing Notes

- Coverage configured in `pyproject.toml` with 80% threshold
- `tingwu_adapter.py` excluded from coverage (requires real cloud credentials)
- Tests use `httpx.AsyncClient` with FastAPI's `TestClient`
