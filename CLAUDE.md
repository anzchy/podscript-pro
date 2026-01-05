# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Podscript is a podcast/audio-video transcription application. Users submit URLs (including YouTube links), and the system downloads, preprocesses, transcribes, and outputs SRT/Markdown files.

**Python requirement:** 3.10 - 3.12 (3.9 has SSL compatibility issues with yt-dlp)

**Dual ASR Engines:**
- **Whisper (offline)** — OpenAI open-source model, runs locally, no API keys needed
- **Tingwu (online)** — Alibaba Cloud service, requires credentials, supports speaker diarization

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install openai-whisper  # For Whisper offline transcription

# Run tests (80% coverage required)
PYTHONPATH=./src pytest --disable-warnings --maxfail=1

# Run tests with coverage report
PYTHONPATH=./src pytest --cov=src/podscript_api --cov=src/podscript_pipeline --cov=src/podscript_shared --cov-report=term-missing

# Run single test file
PYTHONPATH=./src pytest tests/test_api.py -v

# Start API server (default port 8001)
PYTHONPATH=./src uvicorn podscript_api.main:app --port 8001

# Development mode with auto-reload
PYTHONPATH=./src uvicorn podscript_api.main:app --port 8001 --reload

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
│   ├── routers/           # API route modules
│   │   ├── auth.py        # Authentication endpoints (register/login/logout)
│   │   ├── credits.py     # Credits balance and transactions
│   │   └── payment.py     # Z-Pay payment integration
│   ├── middleware/        # Middleware components
│   │   └── auth.py        # JWT validation (get_current_user, get_current_user_optional)
│   └── static/            # Frontend UI (HTML/JS/CSS)
│       ├── login.html     # Login/register page
│       └── login.js       # Auth form handling
├── podscript_pipeline/    # Processing pipeline
│   ├── pipeline.py        # Orchestrates: download → preprocess → transcribe → format
│   ├── download.py        # URL download, YouTube via yt-dlp
│   ├── preprocess.py      # Audio preprocessing
│   ├── asr.py             # ASR dispatch layer (routes to Whisper or Tingwu)
│   ├── whisper_adapter.py # OpenAI Whisper offline transcription
│   ├── tingwu_adapter.py  # Alibaba Cloud Tingwu integration (job polling)
│   ├── storage.py         # Unified cloud storage interface
│   ├── cos_adapter.py     # Tencent Cloud COS adapter
│   └── formatters.py      # SRT/Markdown generation
└── podscript_shared/      # Shared utilities
    ├── models.py          # Pydantic models (TaskStatus, TaskDetail, AppConfig, etc.)
    ├── config.py          # Environment config loader (.env support)
    ├── supabase.py        # Supabase client (anon + service role)
    └── logging.py         # Structured payment logger
```

**Two-Step Workflow:**
1. **Step 1 - Download:** `POST /tasks` → downloads audio → status becomes `downloaded`
2. **Step 2 - Transcribe:** `POST /tasks/{id}/transcribe?provider=whisper` → transcribes → status becomes `completed`
3. Results stored in `artifacts/{task_id}/` (result.srt, result.md, result.json)
4. Frontend polls `GET /tasks/{id}` for status, downloads from `/artifacts/{id}/result.*`

## Key Patterns

- **Task state stored in-memory** (`TASKS` dict in main.py) — not persistent across restarts
- **Background processing** via FastAPI's `BackgroundTasks`
- **ASR provider selection** at transcribe time via `provider` query param (`whisper` or `tingwu`)
- **Dual cloud storage** — OSS (Alibaba) or COS (Tencent) for Tingwu audio uploads
- **Tingwu SDK**: Uses `aliyun-python-sdk-core` with CommonRequest (API version 2023-09-30)
- **Whisper models**: tiny, base, small, medium, large, turbo (cached in `~/.cache/whisper/`)
- **YouTube handling** requires:
  - `yt-dlp`, `ffmpeg`, and `deno` installed (`brew install ffmpeg deno` on macOS)
  - Browser cookies for authentication (defaults to Chrome, set `YTDLP_COOKIES_BROWSER=safari` for Safari)
- **Auth pattern**: Cookie-based JWT auth with httponly, samesite=lax
- **Supabase clients**: `get_supabase_client()` for user ops, `get_supabase_admin_client()` for webhooks (bypasses RLS)
- **Payment webhook**: MD5 signature verification, idempotent processing, structured JSON logging

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

Optional for Supabase Auth + Z-Pay Payment:
```
# Supabase (user auth and data storage)
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

# Z-Pay (payment gateway)
ZPAY_PID=merchant_id
ZPAY_KEY=secret_key
ZPAY_NOTIFY_URL=https://your-domain.com/api/payment/webhook
ZPAY_RETURN_URL=https://your-domain.com/static/payment-success.html
```

Other optional:
- `ARTIFACTS_DIR` — output directory (default: `artifacts`)
- `ALIBABA_CLOUD_SECURITY_TOKEN` — for STS temporary credentials

## API Endpoints

**Task Workflow:**
- `POST /tasks` — Create download task from URL (Step 1)
- `POST /tasks/upload` — Create task from uploaded file (Step 1, skips download)
- `POST /tasks/{id}/transcribe?provider=whisper` — Start transcription (Step 2)
- `POST /tasks/transcribe-url` — Direct URL transcription (skips cloud upload)

**Task Status:**
- `GET /tasks/{id}` — Get task status/progress/logs
- `GET /tasks/{id}/results` — Get result URLs (srt_url, markdown_url)
- `GET /tasks/{id}/transcript` — Get structured transcript with segments
- `GET /tasks/{id}/logs` — Get task execution logs

**ASR Management:**
- `GET /asr/providers` — Get available ASR providers and their status
- `GET /asr/whisper/models` — Get Whisper models and download status
- `POST /asr/whisper/download` — Download a Whisper model

**Authentication (optional, requires Supabase):**
- `POST /api/auth/register` — Register new user (grants 10 bonus credits)
- `POST /api/auth/login` — Login, sets httponly cookie
- `POST /api/auth/logout` — Logout, clears cookie
- `GET /api/auth/me` — Get current user info and credits

**Credits (requires auth):**
- `GET /api/credits/balance` — Get credit balance
- `GET /api/credits/transactions` — Get transaction history

**Payment (requires auth + Z-Pay):**
- `POST /api/payment/create` — Create payment order
- `POST /api/payment/webhook` — Z-Pay async callback

**Static Files:**
- `GET /artifacts/{id}/*` — Serve output files (SRT, Markdown, audio)
- `GET /` — Web UI
- `GET /login` — Login page

## Testing Notes

- Coverage configured in `pyproject.toml` with 80% threshold
- `tingwu_adapter.py` excluded from coverage (requires real cloud credentials)
- Tests use `httpx.AsyncClient` with FastAPI's `TestClient`

## Active Technologies
- Python 3.10-3.12 + FastAPI, Pydantic, yt-dlp, openai-whisper
- JSON 文件 (`artifacts/history.json`) + 任务目录 (`artifacts/{task_id}/`)
- Supabase Python SDK + PyJWT (auth), gotrue (error handling)
- Supabase PostgreSQL: users_credits, credit_transactions, payment_orders tables

## Recent Changes
- 003-add-supabase-and-payment: Added user auth (register/login/logout), credits system, Z-Pay payment integration
- 002-add-transcribe-history: Added transcription history tracking with persistent storage
