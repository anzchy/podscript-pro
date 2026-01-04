# Implementation Plan: 002-Add-Transcribe-History

**Branch**: `002-add-transcribe-history` | **Date**: 2026-01-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-add-transcribe-history/spec.md`

## Summary

在 Podscript 首页增加历史转写记录功能，实现任务持久化存储和管理。技术方案采用 JSON 文件存储（`history.json`），通过 FastAPI 新增 4 个 REST 接口，前端使用原生 JavaScript 渲染表格列表。关键决策包括：软删除策略、TF-IDF 关键词提取、仅记录新任务不迁移旧数据。

## Technical Context

**Language/Version**: Python 3.10-3.12
**Primary Dependencies**: FastAPI, Pydantic, yt-dlp, openai-whisper
**Storage**: JSON 文件 (`artifacts/history.json`) + 任务目录 (`artifacts/{task_id}/`)
**Testing**: pytest (80% coverage required)
**Target Platform**: Linux 云服务器 (Railway/自建)
**Project Type**: Web application (Python backend + vanilla JS frontend)
**Performance Goals**: GET /history P95 延迟 < 200ms（冷启动除外），支持 5000+ 条历史记录
**Constraints**: 无数据库依赖，文件锁处理并发写入
**Scale/Scope**: 单用户/小团队使用，历史记录数量不限

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Simplicity | ✅ PASS | JSON 文件存储，无额外数据库依赖 |
| Test-First | ✅ PASS | 需为 HistoryManager 和 API 编写单元测试 |
| Library-First | ✅ PASS | HistoryManager 作为独立模块在 podscript_shared |
| Observability | ✅ PASS | 标准 FastAPI 日志，可追踪操作 |

**Gate Result**: PASS - 可进入 Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/002-add-transcribe-history/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI spec)
└── claude-style-ui.html # UI design reference
```

### Source Code (repository root)

```text
src/
├── podscript_api/
│   ├── main.py              # Add history API endpoints
│   └── static/
│       ├── index.html       # Add history section
│       ├── app.js           # Add history loading logic
│       ├── history.html     # New: full history page
│       └── history.js       # New: history module
├── podscript_pipeline/
│   └── pipeline.py          # Hook to save history on completion
└── podscript_shared/
    ├── models.py            # Add HistoryRecord model
    ├── history.py           # New: HistoryManager class
    └── keywords.py          # New: TF-IDF keyword extraction

tests/
├── test_history.py          # New: HistoryManager tests
└── test_api.py              # Add history API tests

artifacts/
├── history.json             # Runtime: history index
└── {task_id}/
    └── metadata.json        # Runtime: task metadata
```

**Structure Decision**: 扩展现有 Web 应用结构，新增 `history.py` 和 `keywords.py` 模块到 `podscript_shared`，API 端点添加到 `main.py`。

## Complexity Tracking

> No violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |
