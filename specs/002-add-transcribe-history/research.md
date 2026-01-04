# Research: 002-Add-Transcribe-History

## 1. JSON 文件并发写入处理

**Decision**: 使用 `filelock` 库实现文件锁

**Rationale**:
- Python 标准库 `fcntl` 仅支持 Unix，`filelock` 跨平台
- 轻量级，无需引入重型数据库
- 适合低并发场景（单用户/小团队）

**Alternatives considered**:
- `fcntl.flock()`: Unix only，不适合跨平台部署
- SQLite: 过重，引入额外依赖
- Redis 分布式锁: 过度设计，增加运维复杂度

**Implementation**:
```python
from filelock import FileLock

def save_history(history_path: Path, data: dict):
    lock = FileLock(f"{history_path}.lock")
    with lock:
        history_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
```

---

## 2. TF-IDF 关键词提取

**Decision**: 使用 `jieba` + 简单词频统计，不引入 sklearn

**Rationale**:
- 中文分词需要 jieba，已是成熟方案
- 对于短文本（转写结果），简单词频比 TF-IDF 更直观
- 避免引入 sklearn 的重型依赖

**Alternatives considered**:
- `sklearn.TfidfVectorizer`: 功能强大但依赖重
- `jieba.analyse.extract_tags()`: 内置 TF-IDF，轻量首选
- LLM API: 成本高，延迟大

**Implementation**:
```python
import jieba.analyse

def extract_keywords(text: str, topK: int = 5) -> list[str]:
    """从转写文本提取关键词"""
    # jieba 内置 TF-IDF 算法
    keywords = jieba.analyse.extract_tags(text, topK=topK)
    return keywords
```

**Dependencies**: `jieba` (已在中文 NLP 项目中广泛使用)

---

## 3. YouTube 缩略图获取

**Decision**: 使用 yt-dlp 提取的 `thumbnail` 字段，下载到本地

**Rationale**:
- yt-dlp 已在下载阶段获取视频信息，包含缩略图 URL
- 下载到本地避免外部依赖和跨域问题
- 缩略图文件小（通常 < 50KB）

**Alternatives considered**:
- 直接引用 YouTube CDN URL: 可能过期，跨域问题
- 生成视频帧截图: 需要 ffmpeg 额外处理，复杂
- 不显示缩略图: 用户体验差

**Implementation**:
```python
import urllib.request

def download_thumbnail(url: str, save_path: Path) -> bool:
    """下载缩略图到本地"""
    try:
        urllib.request.urlretrieve(url, save_path)
        return True
    except Exception:
        return False
```

---

## 4. 软删除实现策略

**Decision**: 在 `history.json` 中将 `status` 设为 `deleted`，API 查询时默认过滤

**Rationale**:
- 保留数据可恢复性
- 无需额外的回收站机制
- 简化实现，无需管理两套数据

**Alternatives considered**:
- 物理删除 + 独立回收站 JSON: 增加复杂度
- 移动到 `deleted/` 子目录: 文件操作多，出错风险高
- 标记 `deleted_at` 时间戳: 比布尔状态复杂，当前无需

**Implementation**:
```python
async def delete_record(task_id: str):
    """软删除：标记状态为 deleted"""
    record = get_record(task_id)
    record["status"] = "deleted"
    save_record(record)
```

---

## 5. 前端表格组件选型

**Decision**: 原生 HTML table + Tailwind CSS，不引入组件库

**Rationale**:
- 项目已使用 Tailwind CDN，保持一致
- 表格功能简单（展示 + 分页），无需复杂组件
- 避免增加 bundle 大小和学习成本

**Alternatives considered**:
- DataTables.js: 功能强但重（~100KB）
- AG Grid: 企业级，过度设计
- Vue/React Table: 需要引入框架

**Implementation**: 参考 `claude-style-ui.html` 中的表格样式

---

## 6. 分页策略

**Decision**: 后端分页，使用 `page` + `limit` 参数

**Rationale**:
- 历史记录可能达数千条，前端一次加载不现实
- 标准 REST 分页模式，易于理解和实现
- 首页只显示最近 5 条，完整页面支持翻页

**Alternatives considered**:
- 前端虚拟滚动: 实现复杂，对原生 JS 不友好
- Cursor-based 分页: 适合实时数据流，这里无需
- 无限滚动: 移动端友好，但桌面端体验一般

**Implementation**:
```
GET /history?page=1&limit=20

Response:
{
  "total": 156,
  "page": 1,
  "limit": 20,
  "records": [...]
}
```

---

## Dependencies Summary

| Package | Version | Purpose |
|---------|---------|---------|
| filelock | ^3.0 | JSON 文件并发写入锁 |
| jieba | ^0.42 | 中文分词和关键词提取 |

**Note**: 这两个依赖都是轻量级的，不会显著增加项目体积。
