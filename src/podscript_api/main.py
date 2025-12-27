import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Response, UploadFile, File, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from podscript_shared.config import load_config
from podscript_shared.models import (
    TaskCreateRequest,
    TaskDetail,
    TaskLog,
    TaskResults,
    TaskStatus,
    TaskSummary,
)
from podscript_pipeline import run_pipeline, run_pipeline_from_file, run_download_only, run_transcribe_only
from podscript_pipeline.asr import get_available_providers, ASR_PROVIDER_WHISPER, ASR_PROVIDER_TINGWU

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Podscript MVP API", version="0.1.0")
cfg = load_config()
logger.info("Podscript API initialized")

TASKS: Dict[str, TaskDetail] = {}


def add_task_log(task_id: str, message: str, level: str = "info"):
    """Add a log entry to a task."""
    if task_id in TASKS:
        log_entry = TaskLog(
            time=datetime.now().strftime("%H:%M:%S"),
            level=level,
            message=message
        )
        TASKS[task_id].logs.append(log_entry)


static_dir = Path(cfg.artifacts_dir)
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(static_dir)), name="artifacts")
ui_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(ui_dir)), name="static")


@app.get("/")
async def root():
    return FileResponse(ui_dir / "index.html")


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


# ============== ASR Provider APIs ==============

@app.get("/asr/providers")
async def get_asr_providers():
    """Get available ASR providers and their models."""
    return get_available_providers()


class ModelDownloadRequest(BaseModel):
    model_name: str


@app.post("/asr/whisper/download")
async def download_whisper_model(req: ModelDownloadRequest, bg: BackgroundTasks):
    """Download a Whisper model."""
    try:
        from podscript_pipeline.whisper_adapter import download_model, WHISPER_MODELS, is_model_downloaded

        if req.model_name not in WHISPER_MODELS:
            raise HTTPException(status_code=400, detail=f"Unknown model: {req.model_name}")

        if is_model_downloaded(req.model_name):
            return {"status": "already_downloaded", "model": req.model_name}

        # Download in background
        def _download():
            try:
                download_model(req.model_name)
                logger.info(f"Whisper model {req.model_name} downloaded successfully")
            except Exception as e:
                logger.error(f"Failed to download model {req.model_name}: {e}")

        bg.add_task(_download)
        return {"status": "downloading", "model": req.model_name}
    except ImportError:
        raise HTTPException(status_code=500, detail="Whisper not installed. Run: pip install openai-whisper")


@app.get("/asr/whisper/models")
async def get_whisper_models():
    """Get available Whisper models and their download status."""
    try:
        from podscript_pipeline.whisper_adapter import WHISPER_MODELS, get_downloaded_models

        downloaded = get_downloaded_models()
        models = {}
        for name, info in WHISPER_MODELS.items():
            models[name] = {
                **info,
                "downloaded": name in downloaded,
            }
        return models
    except ImportError:
        raise HTTPException(status_code=500, detail="Whisper not installed. Run: pip install openai-whisper")


# ============== Task APIs ==============

@app.post("/tasks", response_model=TaskSummary)
async def create_task(req: TaskCreateRequest, bg: BackgroundTasks):
    """Create a download task (step 1). Use POST /tasks/{id}/transcribe for step 2."""
    task_id = uuid.uuid4().hex[:12]
    logger.info(f"[{task_id}] Creating download task for URL: {req.source_url}")
    TASKS[task_id] = TaskDetail(id=task_id, status=TaskStatus.queued, progress=0.0)

    def _download():
        try:
            logger.info(f"[{task_id}] Starting download...")
            add_task_log(task_id, "开始下载...")
            TASKS[task_id].status = TaskStatus.downloading
            TASKS[task_id].progress = 0.1
            audio_path, mime_type = run_download_only(task_id, str(req.source_url), cfg.artifacts_dir)
            logger.info(f"[{task_id}] Download complete: {audio_path} (mime: {mime_type})")
            add_task_log(task_id, f"下载完成: {Path(audio_path).name}")
            TASKS[task_id].status = TaskStatus.downloaded
            TASKS[task_id].progress = 0.5
            TASKS[task_id].audio_path = audio_path
        except Exception as e:
            logger.error(f"[{task_id}] Download failed: {e}", exc_info=True)
            add_task_log(task_id, f"下载失败: {str(e)}", "error")
            TASKS[task_id].status = TaskStatus.failed
            TASKS[task_id].error = {"message": str(e)}

    bg.add_task(_download)
    return TaskSummary(id=task_id, status=TaskStatus.queued, progress=0.0)


class TranscribeRequest(BaseModel):
    provider: str = ASR_PROVIDER_WHISPER
    model_name: Optional[str] = None
    language: Optional[str] = None


@app.post("/tasks/{task_id}/transcribe", response_model=TaskSummary)
async def transcribe_task(
    task_id: str,
    bg: BackgroundTasks,
    provider: str = Query(default=ASR_PROVIDER_WHISPER, description="ASR provider: 'whisper' or 'tingwu'"),
    model_name: Optional[str] = Query(default=None, description="Model name (for Whisper)"),
    language: Optional[str] = Query(default=None, description="Language code (e.g., 'zh', 'en')"),
    prompt: Optional[str] = Query(default=None, description="Custom prompt: Whisper uses it for vocabulary hints; Tingwu for LLM post-processing"),
):
    """Start transcription for a downloaded task (step 2).

    The prompt parameter works differently for each provider:
    - Whisper: initial_prompt for vocabulary/style hints (max ~900 chars)
      Example: "术语：Kubernetes, Docker" or "这是一个播客对话"
    - Tingwu: custom prompt for LLM post-processing
      Example: "生成详细摘要" or "提取关键信息"
    """
    task = TASKS.get(task_id)
    if not task:
        logger.warning(f"[{task_id}] Transcribe request for non-existent task")
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.downloaded:
        logger.warning(f"[{task_id}] Transcribe request with wrong status: {task.status}")
        raise HTTPException(status_code=400, detail=f"Task must be in 'downloaded' status, current: {task.status}")
    if not task.audio_path:
        logger.warning(f"[{task_id}] Transcribe request but no audio_path")
        raise HTTPException(status_code=400, detail="No audio file found for this task")

    provider_name = "Whisper 离线" if provider == ASR_PROVIDER_WHISPER else "通义听悟"
    logger.info(f"[{task_id}] Starting transcription with {provider_name}: {task.audio_path}")
    add_task_log(task_id, f"开始转写任务 (使用 {provider_name})...")
    if prompt:
        logger.info(f"[{task_id}] Custom prompt: {prompt[:50]}...")
        add_task_log(task_id, f"使用自定义 Prompt: {prompt[:30]}...")

    def _transcribe():
        def log_callback(msg: str):
            add_task_log(task_id, msg)

        try:
            TASKS[task_id].status = TaskStatus.transcribing
            TASKS[task_id].progress = 0.55

            results = run_transcribe_only(
                task_id=task_id,
                audio_path=task.audio_path,
                artifacts_dir=cfg.artifacts_dir,
                provider=provider,
                model_name=model_name,
                language=language,
                prompt=prompt,
                log_callback=log_callback,
            )

            add_task_log(task_id, f"转写完成，共 {results.get('meta', {}).get('segments', 0)} 个语音片段")
            TASKS[task_id].status = TaskStatus.completed
            TASKS[task_id].progress = 1.0
            srt_url = f"/artifacts/{task_id}/result.srt"
            md_url = f"/artifacts/{task_id}/result.md"
            TASKS[task_id].results = TaskResults(
                srt_url=srt_url, markdown_url=md_url, meta=results.get("meta", {})
            )
            add_task_log(task_id, "结果已保存，转写任务完成！")
        except Exception as e:
            logger.error(f"[{task_id}] Transcription failed: {e}", exc_info=True)
            add_task_log(task_id, f"转写失败: {str(e)}", "error")
            TASKS[task_id].status = TaskStatus.failed
            TASKS[task_id].error = {"message": str(e)}

    bg.add_task(_transcribe)
    return TaskSummary(id=task_id, status=TaskStatus.transcribing, progress=0.6)


@app.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/tasks/{task_id}/results", response_model=TaskResults)
async def get_results(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.completed or not task.results:
        raise HTTPException(status_code=400, detail="Results not ready")
    return task.results


@app.get("/tasks/{task_id}/logs")
async def get_logs(task_id: str) -> List[TaskLog]:
    """Get task execution logs."""
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.logs


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    speaker: str = ""


class TranscriptResponse(BaseModel):
    segments: List[TranscriptSegment]
    media_url: str
    media_type: str
    duration: float = 0


@app.get("/tasks/{task_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(task_id: str):
    """Get structured transcript data for the result viewer."""
    import json

    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.completed or not task.results:
        raise HTTPException(status_code=400, detail="Transcript not ready")

    # Try to load transcript from JSON file first
    task_dir = Path(cfg.artifacts_dir) / task_id
    json_path = task_dir / "result.json"

    segments = []
    duration = 0

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            segments = [
                TranscriptSegment(
                    id=i,
                    start=seg.get("start", 0),
                    end=seg.get("end", 0),
                    text=seg.get("text", ""),
                    speaker=str(seg.get("speaker", ""))
                )
                for i, seg in enumerate(data.get("segments", []))
            ]
            duration = data.get("duration", 0)
    else:
        # Fallback: parse from markdown
        md_path = task_dir / "result.md"
        if md_path.exists():
            segments = _parse_markdown_transcript(md_path)

    # Determine media URL
    media_url = ""
    media_type = "audio"

    # Check for common audio/video files
    for ext in [".mp3", ".m4a", ".wav", ".mp4", ".webm"]:
        for file in task_dir.glob(f"*{ext}"):
            media_url = f"/artifacts/{task_id}/{file.name}"
            if ext in [".mp4", ".webm"]:
                media_type = "video"
            break
        if media_url:
            break

    # Calculate duration from segments if not set
    if not duration and segments:
        duration = max(s.end for s in segments)

    return TranscriptResponse(
        segments=segments,
        media_url=media_url,
        media_type=media_type,
        duration=duration
    )


def _parse_markdown_transcript(md_path: Path) -> List[TranscriptSegment]:
    """Parse transcript segments from markdown file."""
    import re

    segments = []
    text = md_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    current_speaker = ""
    current_time = 0.0
    current_text = ""
    segment_id = 0

    for line in lines:
        # Match speaker line: "发言人1  00:16" or just "00:16"
        match = re.match(r"^(发言人\d+)?\s*(\d{2}:\d{2})", line)
        if match:
            # Save previous segment
            if current_text.strip():
                segments.append(TranscriptSegment(
                    id=segment_id,
                    start=current_time,
                    end=current_time + 10,  # Estimated
                    text=current_text.strip(),
                    speaker=current_speaker
                ))
                segment_id += 1

            speaker_str = match.group(1)
            current_speaker = speaker_str.replace("发言人", "") if speaker_str else ""
            time_parts = match.group(2).split(":")
            current_time = int(time_parts[0]) * 60 + int(time_parts[1])
            current_text = ""
        elif line.strip() and not line.startswith("#"):
            current_text += (" " if current_text else "") + line.strip()

    # Add last segment
    if current_text.strip():
        segments.append(TranscriptSegment(
            id=segment_id,
            start=current_time,
            end=current_time + 10,
            text=current_text.strip(),
            speaker=current_speaker
        ))

    # Fix end times based on next segment start
    for i in range(len(segments) - 1):
        segments[i].end = segments[i + 1].start

    return segments


@app.post("/tasks/upload", response_model=TaskSummary)
async def upload_task(file: UploadFile = File(...), bg: BackgroundTasks = BackgroundTasks()):
    """Upload a local audio/video file (step 1). Use POST /tasks/{id}/transcribe for step 2."""
    task_id = uuid.uuid4().hex[:12]
    logger.info(f"[{task_id}] Uploading file: {file.filename}")
    TASKS[task_id] = TaskDetail(id=task_id, status=TaskStatus.queued, progress=0.0)
    task_dir = Path(cfg.artifacts_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    destination = task_dir / file.filename

    add_task_log(task_id, f"上传文件: {file.filename}")

    with destination.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)

    content_type = file.content_type or "application/octet-stream"

    # Mark as downloaded immediately since file is already uploaded
    TASKS[task_id].status = TaskStatus.downloaded
    TASKS[task_id].progress = 0.5
    TASKS[task_id].audio_path = str(destination)
    add_task_log(task_id, "文件上传完成")

    return TaskSummary(id=task_id, status=TaskStatus.downloaded, progress=0.5)
