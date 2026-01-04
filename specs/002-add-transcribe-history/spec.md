# 002-Add-Transcribe-History: 转写历史记录功能

## Clarifications

### Session 2026-01-03

- Q: 删除记录时是否同时删除 artifacts 文件？ → A: 软删除（标记 deleted 状态，不从列表显示，文件保留）
- Q: 标签（tags）的来源方式？ → A: 自动提取 + 用户可编辑修改
- Q: 现有 artifacts 目录下的旧任务是否迁移？ → A: 仅记录新任务，旧任务不迁移
- Q: 标签自动提取的实现方式？ → A: 简单关键词提取（TF-IDF/词频统计，提取高频名词）
- Q: 历史记录数量是否限制？ → A: 不限制，JSON 文件可承载数千条记录

---

## 概述

在首页增加历史转写记录列表，用户可查看、管理和访问过往的转写任务。记录持久化存储于云服务器，支持跨会话访问。

## 功能需求

### 1. 历史记录列表

#### 1.1 位置布局

历史记录区块位于首页"转写结果"卡片下方，Footer 之前。

```
┌─────────────────────────────────────────────────────────────┐
│ 最近记录  (+16)                              查看全部 >      │
├─────────────────────────────────────────────────────────────┤
│ 文件        │ 标签      │ 类型      │ 时长   │ 大小   │ 创建时间  │ 操作 │
├─────────────────────────────────────────────────────────────┤
│ 🎬 视频标题  │ AI 泡沫   │ 音视频转写 │ 46:26 │ 183M │ 2025/12/16 │ ⋯  │
│ 🎤 音频名称  │ IVR GPU  │ 音视频转写 │ 01:04 │ 30M  │ 2025/12/02 │ ⋯  │
│ 🎤 项目会议• │ 行业 车厂 │ 音视频转写 │ 28:29 │ 13M  │ 2025/11/30 │ ⋯  │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 列表字段

| 字段 | 说明 |
|------|------|
| 文件 | 缩略图/图标 + 任务标题（可点击跳转） |
| 标签 | 转写完成后通过 TF-IDF 自动提取 Top 5 关键词，用户可在操作菜单中编辑 |
| 类型 | 音视频转写（固定） |
| 时长 | 媒体文件时长 (HH:MM:SS 或 MM:SS) |
| 大小 | 文件大小 (MB/GB) |
| 创建时间 | 任务创建日期（API 返回 ISO 8601，前端格式化显示为 YYYY/MM/DD） |
| 操作 | 更多操作菜单 (删除、重新转写等) |

#### 1.3 交互行为

- **文件名点击**：跳转到对应的转写结果页面 `/result.html?task_id={id}`
- **新记录标记**：未查看的记录显示红点标识
- **行悬停**：背景色变化，显示可点击状态
- **查看全部**：跳转到完整历史列表页面（可分页）
- **空状态**：无记录时显示占位图"暂无转写记录"

### 2. 操作菜单

点击操作列的"⋯"按钮，弹出下拉菜单：

- **查看详情**：跳转到转写结果页
- **下载 SRT**：直接下载字幕文件
- **下载 Markdown**：直接下载 MD 文件
- **复制链接**：复制结果页面链接
- **编辑标签**：弹窗编辑标签（支持添加/删除，最多 10 个标签，每个最长 20 字符）
- **删除记录**：软删除该条记录（需二次确认），标记为 deleted 状态，从列表隐藏但保留文件

### 3. 转写结果详情页

复用 001-UI-Redesign 中的 `/result.html` 页面，通过 `task_id` 参数加载对应任务的转写结果。

**兼容性要求**（验证见 Task T044）：
- result.html 必须支持 `?task_id=xxx` URL 参数
- 加载 `/artifacts/{task_id}/result.json` 获取转写数据
- 正确显示 SRT 和 Markdown 下载链接

---

## 数据存储方案

### 存储方式选型

**选择方案：JSON 文件存储**

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **JSON 文件** ✅ | 简单、无依赖、易备份、可读性好 | 并发写入需处理 | 小型应用、轻量需求 |
| SQLite | 结构化查询、性能好 | 额外依赖 | 中型应用 |
| 云数据库 | 高可用、可扩展 | 成本高、复杂 | 大型应用 |

**选择理由**：
1. Podscript 是轻量级工具，用户量有限
2. 无需引入额外数据库依赖
3. JSON 格式易于调试和手动编辑
4. 可通过文件锁处理并发写入

### 存储结构

#### 目录结构

```
artifacts/
├── history.json              # 历史记录索引文件
├── {task_id}/
│   ├── metadata.json         # 任务元数据
│   ├── result.srt            # SRT 字幕文件
│   ├── result.md             # Markdown 文件
│   ├── result.json           # 结构化转写数据
│   ├── audio.mp3             # 处理后的音频文件
│   └── thumbnail.jpg         # 视频缩略图（如有）
```

#### 数据结构

详细的 JSON Schema 定义见 [data-model.md](./data-model.md)：

- **HistoryIndex** (`history.json`): 历史记录索引，包含 version、updated_at、records 数组
- **HistoryRecord**: 单条历史记录摘要，12 位十六进制 task_id
- **TaskMetadata** (`metadata.json`): 单任务完整元数据，包含 source、media、transcription 详情

API 契约定义见 [contracts/openapi.yaml](./contracts/openapi.yaml)

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 唯一任务标识符 |
| title | string | 任务标题（从 YouTube 获取或用户指定） |
| source_url | string | 原始 URL（YouTube 链接或空） |
| source_type | enum | youtube / upload / url |
| media_type | enum | video / audio |
| duration | int | 时长（秒） |
| file_size | int | 文件大小（字节） |
| tags | array | 标签数组（手动或自动提取） |
| created_at | datetime | 创建时间（ISO 8601） |
| viewed | bool | 是否已查看（用于新记录标记） |
| thumbnail_url | string | 缩略图路径（视频有效） |
| status | enum | pending / downloading / downloaded / processing / completed / failed / deleted |

---

## API 设计

### 新增接口

#### 1. 获取历史记录列表

```
GET /history
Query Parameters:
  - page: int (default: 1)
  - limit: int (default: 20, max: 100)
  - status: string (optional, filter by status)

Response:
{
  "total": 16,
  "page": 1,
  "limit": 20,
  "records": [...]
}
```

#### 2. 获取单条记录详情

```
GET /history/{task_id}

Response:
{
  "task_id": "abc123",
  "title": "...",
  ...
}
```

#### 3. 更新记录（标记已读、更新标签）

```
PATCH /history/{task_id}
Body:
{
  "viewed": true,
  "tags": ["AI", "投资"]
}

Response:
{
  "success": true
}
```

#### 4. 删除记录

```
DELETE /history/{task_id}

Response:
{
  "success": true
}
```

### 现有接口扩展

任务完成时自动将记录写入 `history.json`（实现见 Task T012）：

1. 在 `pipeline.py` 转写完成后调用 `HistoryManager.add_record()`
2. 从 `TaskDetail` 提取元数据构建 `HistoryRecord`
3. 调用 `keywords.py` 提取关键词作为初始 tags
4. 使用文件锁确保并发安全写入

---

## 前端实现

### 文件结构

```
src/podscript_api/static/
├── index.html          # 主页（增加历史记录区块）
├── result.html         # 转写结果页
├── history.html        # 完整历史列表页（新增）
├── app.js              # 主页逻辑（增加历史记录加载）
├── history.js          # 历史记录相关逻辑（新增）
└── styles.css          # 样式
```

### 主页加载逻辑

```javascript
// 页面加载时获取历史记录
async function loadHistory() {
  const response = await fetch('/history?limit=5');
  const data = await response.json();
  renderHistoryTable(data.records);
}

// 文件名点击跳转
function onRecordClick(taskId) {
  // 标记为已读
  fetch(`/history/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify({ viewed: true })
  });
  // 跳转到结果页
  window.location.href = `/result.html?task_id=${taskId}`;
}
```

---

## UI 设计稿

参考文件：`specs/002-add-transcribe-history/claude-style-ui.html`

设计要点：
- 与现有 Claude 风格保持一致
- 表格行 hover 效果
- 新记录红点标识
- 响应式布局（小屏横向滚动）
- 空状态友好提示

---

## 实现步骤

### Phase 1: 数据层

1. [ ] 创建 `HistoryManager` 类处理 JSON 读写
2. [ ] 实现文件锁机制防止并发写入
3. [ ] 在任务完成时自动写入历史记录
4. [ ] 编写单元测试

### Phase 2: API 层

5. [ ] 实现 `GET /history` 接口
6. [ ] 实现 `GET /history/{task_id}` 接口
7. [ ] 实现 `PATCH /history/{task_id}` 接口
8. [ ] 实现 `DELETE /history/{task_id}` 接口
9. [ ] 编写 API 测试

### Phase 3: 前端层

10. [ ] 更新 `index.html` 添加历史记录区块
11. [ ] 实现历史记录加载和渲染
12. [ ] 实现文件名点击跳转逻辑
13. [ ] 实现操作菜单功能
14. [ ] 实现空状态显示
15. [ ] 响应式适配

### Phase 4: 集成测试

16. [ ] 端到端测试完整流程
17. [ ] 部署到云服务器验证

---

## 验收标准

- [ ] 首页正确显示历史记录列表
- [ ] 文件名可点击，正确跳转到结果页
- [ ] 新记录显示红点标记，查看后消失
- [ ] 操作菜单功能完整可用
- [ ] 删除记录需二次确认
- [ ] 数据持久化存储，重启服务后仍可访问
- [ ] "查看全部"跳转到完整列表页
- [ ] 空状态友好显示
- [ ] 响应式布局适配移动端
- [ ] API 接口返回正确的数据格式
