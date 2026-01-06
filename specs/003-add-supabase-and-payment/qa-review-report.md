# Podscript QA 审查报告

**审查日期**: 2026-01-06
**审查范围**: 下载模块、转写模块、API 接口、错误处理
**审查目的**: 识别可能导致进程卡死、功能异常、安全风险的问题

---

## 📊 问题汇总

| 优先级 | 问题数量 | 说明 |
|--------|----------|------|
| 🔴 P0 - 紧急 | 3 | 直接导致功能失败或进程卡死 |
| 🟠 P1 - 高 | 3 | 影响用户体验或存在安全风险 |
| 🟡 P2 - 中 | 3 | 资源泄漏或边界情况处理 |
| 🟢 P3 - 低 | 2 | 代码质量和可维护性 |

---

## 🔴 P0 - 紧急修复 (直接导致功能失败)

### P0-1: 非 YouTube 网站无法下载（如哔哩哔哩）

**严重程度**: 🔴 Critical
**影响范围**: 所有非 YouTube 链接
**用户表现**: 下载显示成功，但转写失败或输出空白

**问题位置**: `src/podscript_pipeline/download.py:6-76`

**问题代码**:
```python
def _is_youtube(url: str) -> bool:
    u = url.lower()
    return ("youtube.com/watch" in u) or ("youtu.be/" in u)

def download_source(task_id: str, source_url: str, artifacts_dir: str):
    if _is_youtube(source_url):
        # 只有 YouTube 会真正下载
        # ...yt-dlp 下载逻辑...
    else:
        # 非 YouTube 链接只创建一个文本文件！
        downloaded = task_dir / "download.txt"
        downloaded.write_text(f"source_url={source_url}\n")
        return downloaded, "text/plain"
```

**问题分析**:
1. `yt-dlp` 本身支持 1000+ 网站（包括 Bilibili、Vimeo、Twitter、抖音等）
2. 但代码中只对 YouTube 链接调用 yt-dlp
3. 其他网站的链接只会创建一个包含 URL 文本的 stub 文件
4. 后续转写模块尝试处理这个 stub 文件，导致失败

**修复方案**:
```python
def _is_supported_video_site(url: str) -> bool:
    """检查 URL 是否是 yt-dlp 支持的视频网站"""
    # 方案1: 尝试让 yt-dlp 提取信息，成功则支持
    # 方案2: 维护支持的网站白名单
    # 方案3: 对所有 URL 尝试 yt-dlp，失败则报错
    pass

def download_source(task_id: str, source_url: str, artifacts_dir: str):
    try:
        # 尝试用 yt-dlp 下载任何 URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_url, download=True)
            # ...
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"不支持的链接或下载失败: {e}")
```

**测试用例**:
- [ ] 哔哩哔哩视频链接 `https://www.bilibili.com/video/BV...`
- [ ] 抖音视频链接 `https://www.douyin.com/video/...`
- [ ] Twitter/X 视频链接
- [ ] 无效 URL 应返回明确错误

---

### P0-2: yt-dlp 下载没有超时设置

**严重程度**: 🔴 Critical
**影响范围**: 所有视频下载任务
**用户表现**: 下载任务一直显示"下载中"，永不完成

**问题位置**: `src/podscript_pipeline/download.py:38-61`

**问题代码**:
```python
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": outtmpl,
    "postprocessors": [...],
    "quiet": False,
    "no_warnings": False,
    "nocheckcertificate": True,
    "cookiesfrombrowser": (...),
    # ❌ 没有超时配置！
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(source_url, download=True)  # 可能无限等待
```

**问题分析**:
1. `extract_info()` 在网络不稳定或目标网站响应慢时会一直阻塞
2. 某些需要登录的视频可能在验证阶段卡住
3. FastAPI 的 BackgroundTasks 没有超时机制
4. 用户无法取消卡住的任务

**修复方案**:
```python
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": outtmpl,
    # ... 其他配置 ...

    # 添加超时和重试配置
    "socket_timeout": 30,           # 单次网络请求超时 30 秒
    "retries": 3,                   # 重试 3 次
    "fragment_retries": 3,          # 分片下载重试
    "extractor_retries": 3,         # 提取器重试
    "file_access_retries": 3,       # 文件访问重试
    "http_chunk_size": 10485760,    # 10MB 分块下载
}
```

**测试用例**:
- [ ] 下载超时应在合理时间内报错（建议 5 分钟）
- [ ] 网络中断后应自动重试
- [ ] 重试失败后应返回明确错误信息

---

### P0-3: 缩略图下载没有超时

**严重程度**: 🔴 High
**影响范围**: 所有 YouTube 下载任务
**用户表现**: 下载卡在缩略图获取阶段

**问题位置**: `src/podscript_pipeline/download.py:11-26`

**问题代码**:
```python
def _download_thumbnail(info: dict, task_dir: Path) -> None:
    try:
        import urllib.request
        # ...
        if thumbnail_url:
            thumbnail_path = task_dir / "thumbnail.jpg"
            urllib.request.urlretrieve(thumbnail_url, thumbnail_path)  # ❌ 无超时
    except Exception as e:
        print(f"Thumbnail download failed (non-fatal): {e}")
```

**修复方案**:
```python
def _download_thumbnail(info: dict, task_dir: Path, timeout: int = 10) -> None:
    try:
        import urllib.request
        import socket

        # 设置全局超时
        socket.setdefaulttimeout(timeout)

        thumbnail_url = info.get("thumbnail")
        if not thumbnail_url:
            thumbnails = info.get("thumbnails", [])
            if thumbnails:
                thumbnail_url = thumbnails[-1].get("url")

        if thumbnail_url:
            thumbnail_path = task_dir / "thumbnail.jpg"
            urllib.request.urlretrieve(thumbnail_url, thumbnail_path)
    except Exception as e:
        print(f"Thumbnail download failed (non-fatal): {e}")
    finally:
        socket.setdefaulttimeout(None)  # 恢复默认
```

---

## 🟠 P1 - 高优先级 (影响用户体验或安全)

### P1-1: URL 没有格式验证

**严重程度**: 🟠 High
**影响范围**: 所有任务创建请求
**用户表现**: 无效 URL 被接受，导致后续处理失败

**问题位置**: `src/podscript_api/main.py:351-388`

**问题代码**:
```python
@app.post("/tasks", response_model=TaskSummary)
async def create_task(req: TaskCreateRequest, bg: BackgroundTasks, ...):
    task_id = uuid.uuid4().hex[:12]
    # ❌ 没有验证 req.source_url 是否为有效 URL
    TASKS[task_id] = TaskDetail(id=task_id, status=TaskStatus.queued, progress=0.0)
    TASK_SOURCES[task_id] = str(req.source_url)
```

**修复方案**:
```python
from urllib.parse import urlparse
import re

def validate_url(url: str) -> tuple[bool, str]:
    """验证 URL 格式和协议"""
    try:
        result = urlparse(url)
        if result.scheme not in ('http', 'https'):
            return False, "URL 必须以 http:// 或 https:// 开头"
        if not result.netloc:
            return False, "无效的 URL 格式"
        return True, ""
    except Exception:
        return False, "URL 解析失败"

@app.post("/tasks", response_model=TaskSummary)
async def create_task(req: TaskCreateRequest, bg: BackgroundTasks, ...):
    # 验证 URL
    is_valid, error_msg = validate_url(str(req.source_url))
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # ... 继续处理
```

---

### P1-2: 文件上传没有大小限制

**严重程度**: 🟠 High
**影响范围**: 文件上传接口
**用户表现**: 无 (攻击者可耗尽磁盘空间)

**问题位置**: `src/podscript_api/main.py:731-768`

**问题代码**:
```python
@app.post("/tasks/upload", response_model=TaskSummary)
async def upload_task(file: UploadFile = File(...), ...):
    # ❌ 没有文件大小限制
    with destination.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
```

**修复方案**:
```python
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB

@app.post("/tasks/upload", response_model=TaskSummary)
async def upload_task(file: UploadFile = File(...), ...):
    # 检查 Content-Length header
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大，最大支持 {MAX_UPLOAD_SIZE // (1024*1024)}MB"
        )

    # 流式写入时检查大小
    total_size = 0
    with destination.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_UPLOAD_SIZE:
                destination.unlink()  # 删除部分文件
                raise HTTPException(status_code=413, detail="文件过大")
            out.write(chunk)
```

---

### P1-3: 后台任务无法取消

**严重程度**: 🟠 Medium
**影响范围**: 所有后台任务
**用户表现**: 卡住的任务无法中止，只能等待或重启服务

**问题位置**: `src/podscript_api/main.py:369-388, 490-567`

**问题分析**:
1. FastAPI 的 BackgroundTasks 不支持取消
2. 没有任务取消标志或机制
3. 用户只能等待任务超时或重启服务

**修复方案**:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, Future

# 任务执行器
TASK_EXECUTOR = ThreadPoolExecutor(max_workers=4)
TASK_FUTURES: Dict[str, Future] = {}

@app.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消正在执行的任务"""
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")

    task = TASKS[task_id]
    if task.status in [TaskStatus.completed, TaskStatus.failed]:
        raise HTTPException(status_code=400, detail="任务已完成，无法取消")

    # 尝试取消 Future
    future = TASK_FUTURES.get(task_id)
    if future and not future.done():
        future.cancel()

    task.status = TaskStatus.failed
    task.error = {"message": "任务已被用户取消"}
    add_task_log(task_id, "任务已取消", "warning")

    return {"message": "任务取消请求已发送"}
```

---

## 🟡 P2 - 中优先级 (资源泄漏和边界情况)

### P2-1: 任务内存无清理机制

**严重程度**: 🟡 Medium
**影响范围**: 服务器长期运行
**用户表现**: 服务器内存逐渐增加，可能导致 OOM

**问题位置**: `src/podscript_api/main.py:60-64`

**问题代码**:
```python
TASKS: Dict[str, TaskDetail] = {}
TASK_METADATA: Dict[str, Dict[str, Any]] = {}
TASK_SOURCES: Dict[str, str] = {}
# ❌ 没有清理机制，数据会无限增长
```

**修复方案**:
```python
from datetime import datetime, timedelta
import threading

TASK_TTL_HOURS = 24  # 任务保留 24 小时

def cleanup_old_tasks():
    """清理超过 TTL 的任务"""
    cutoff = datetime.now() - timedelta(hours=TASK_TTL_HOURS)
    to_delete = []

    for task_id, task in TASKS.items():
        # 检查任务创建时间（需要在 TaskDetail 中添加 created_at 字段）
        if hasattr(task, 'created_at') and task.created_at < cutoff:
            if task.status in [TaskStatus.completed, TaskStatus.failed]:
                to_delete.append(task_id)

    for task_id in to_delete:
        TASKS.pop(task_id, None)
        TASK_METADATA.pop(task_id, None)
        TASK_SOURCES.pop(task_id, None)

    if to_delete:
        logger.info(f"Cleaned up {len(to_delete)} old tasks")

# 定时清理（每小时）
def start_cleanup_scheduler():
    def run():
        while True:
            time.sleep(3600)
            cleanup_old_tasks()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
```

---

### P2-2: 错误信息暴露内部细节

**严重程度**: 🟡 Low
**影响范围**: 所有错误响应
**用户表现**: 无 (安全问题)

**问题位置**: 多处

**问题代码**:
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))  # ❌ 暴露内部错误
```

**修复方案**:
```python
import traceback

def safe_error_message(e: Exception, debug: bool = False) -> str:
    """生成安全的错误信息"""
    if debug:
        return str(e)

    # 映射常见错误到用户友好信息
    error_mappings = {
        "ConnectionError": "网络连接失败，请稍后重试",
        "TimeoutError": "请求超时，请稍后重试",
        "FileNotFoundError": "文件不存在",
    }

    error_type = type(e).__name__
    return error_mappings.get(error_type, "服务器内部错误，请稍后重试")
```

---

### P2-3: 并发下载没有限制

**严重程度**: 🟡 Medium
**影响范围**: 服务器资源
**用户表现**: 大量并发请求可能耗尽服务器资源

**问题位置**: `src/podscript_api/main.py:351-388`

**修复方案**:
```python
import asyncio

# 限制并发下载数
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(5)  # 最多 5 个并发下载

@app.post("/tasks", response_model=TaskSummary)
async def create_task(req: TaskCreateRequest, bg: BackgroundTasks, ...):
    # 检查当前正在下载的任务数
    downloading_count = sum(
        1 for t in TASKS.values()
        if t.status in [TaskStatus.queued, TaskStatus.downloading]
    )

    if downloading_count >= 10:
        raise HTTPException(
            status_code=429,
            detail="服务器繁忙，请稍后再试"
        )

    # ... 继续处理
```

---

## 🟢 P3 - 低优先级 (代码质量)

### P3-1: 日志级别不一致

**问题**: 有些地方用 `print()`，有些用 `logger`

**修复**: 统一使用 `logger`

---

### P3-2: 魔法数字硬编码

**问题**: 超时时间、重试次数等硬编码在代码中

**修复**: 提取到配置文件或环境变量

---

## ✅ 已有保护措施

| 模块 | 保护措施 | 状态 |
|------|---------|------|
| `tingwu_adapter.py` | 轮询超时 600s | ✅ 良好 |
| `tingwu_adapter.py` | 指数退避重试 | ✅ 良好 |
| `main.py` | ffprobe 超时 30s | ✅ 良好 |
| `main.py` | httpx 下载超时 300s | ✅ 良好 |
| OSS 上传 | connect_timeout=60s | ✅ 良好 |
| 积分系统 | 失败自动退款 | ✅ 良好 |

---

## 📋 修复优先级排序

| 序号 | 问题 ID | 问题描述 | 预计工时 |
|------|---------|---------|---------|
| 1 | P0-1 | 非 YouTube 网站无法下载 | 2h |
| 2 | P0-2 | yt-dlp 下载没有超时 | 0.5h |
| 3 | P0-3 | 缩略图下载没有超时 | 0.5h |
| 4 | P1-1 | URL 没有格式验证 | 1h |
| 5 | P1-2 | 文件上传没有大小限制 | 1h |
| 6 | P1-3 | 后台任务无法取消 | 3h |
| 7 | P2-1 | 任务内存无清理机制 | 2h |
| 8 | P2-2 | 错误信息暴露内部细节 | 1h |
| 9 | P2-3 | 并发下载没有限制 | 1h |

**总计预计工时**: 约 12 小时

---

## 🔧 建议修复顺序

### 第一阶段 (立即修复 - 解决核心功能问题)
1. P0-1: 支持非 YouTube 网站下载
2. P0-2: 添加 yt-dlp 超时配置
3. P0-3: 添加缩略图下载超时

### 第二阶段 (短期修复 - 提升稳定性)
4. P1-1: URL 格式验证
5. P1-2: 文件上传大小限制
6. P2-3: 并发下载限制

### 第三阶段 (长期优化 - 完善系统)
7. P1-3: 任务取消机制
8. P2-1: 任务内存清理
9. P2-2: 错误信息安全处理
