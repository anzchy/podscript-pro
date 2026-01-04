# Quickstart: 002-Add-Transcribe-History

## Prerequisites

- Python 3.10-3.12
- 已有 Podscript 开发环境
- 已完成 001-UI-Redesign（result.html 页面）

## 安装新依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装新依赖
pip install filelock jieba
pip freeze > requirements.txt
```

## 实现顺序

### Step 1: 数据层 (HistoryManager)

1. **创建 Pydantic 模型** (`src/podscript_shared/models.py`)
   ```python
   # 添加 HistoryRecord, HistoryIndex 模型
   ```

2. **创建 HistoryManager** (`src/podscript_shared/history.py`)
   ```python
   class HistoryManager:
       def __init__(self, history_path: Path): ...
       def load(self) -> HistoryIndex: ...
       def save(self, index: HistoryIndex): ...
       def add_record(self, record: HistoryRecord): ...
       def get_record(self, task_id: str) -> HistoryRecord | None: ...
       def update_record(self, task_id: str, **kwargs): ...
       def delete_record(self, task_id: str): ...  # 软删除
       def list_records(self, page: int, limit: int, status: str | None) -> tuple[list, int]: ...
   ```

3. **创建关键词提取** (`src/podscript_shared/keywords.py`)
   ```python
   def extract_keywords(text: str, topK: int = 5) -> list[str]:
       import jieba.analyse
       return jieba.analyse.extract_tags(text, topK=topK)
   ```

4. **编写单元测试** (`tests/test_history.py`)
   - 测试 CRUD 操作
   - 测试并发写入
   - 测试软删除过滤

### Step 2: Pipeline 集成

1. **修改 pipeline.py** - 转写完成后保存历史记录
   ```python
   # 在 run_pipeline_transcribe 完成后
   from podscript_shared.history import HistoryManager
   from podscript_shared.keywords import extract_keywords

   def save_to_history(task_id: str, task_detail: TaskDetail, transcript_text: str):
       manager = HistoryManager(Path(cfg.artifacts_dir) / "history.json")
       keywords = extract_keywords(transcript_text)
       record = HistoryRecord(
           task_id=task_id,
           title=task_detail.title,
           tags=keywords,
           ...
       )
       manager.add_record(record)
   ```

### Step 3: API 端点

1. **添加路由** (`src/podscript_api/main.py`)
   ```python
   @app.get("/history")
   async def get_history(page: int = 1, limit: int = 20, status: str | None = None):
       ...

   @app.get("/history/{task_id}")
   async def get_history_record(task_id: str):
       ...

   @app.patch("/history/{task_id}")
   async def update_history_record(task_id: str, body: HistoryUpdateRequest):
       ...

   @app.delete("/history/{task_id}")
   async def delete_history_record(task_id: str):
       ...
   ```

2. **编写 API 测试** (`tests/test_api.py`)
   - 测试列表分页
   - 测试更新 viewed/tags
   - 测试软删除

### Step 4: 前端实现

1. **更新 index.html** - 添加历史记录区块
   - 参考 `specs/002-add-transcribe-history/claude-style-ui.html`

2. **创建 history.js** - 历史记录模块
   ```javascript
   async function loadHistory(limit = 5) { ... }
   function renderHistoryTable(records) { ... }
   function onRecordClick(taskId) { ... }
   function showOperationMenu(taskId, event) { ... }
   async function deleteRecord(taskId) { ... }
   async function editTags(taskId) { ... }
   ```

3. **创建 history.html** - 完整历史列表页
   - 分页组件
   - 搜索/过滤功能（可选）

## 测试验证

```bash
# 运行单元测试
PYTHONPATH=./src pytest tests/test_history.py -v

# 运行 API 测试
PYTHONPATH=./src pytest tests/test_api.py -v -k history

# 运行全部测试
PYTHONPATH=./src pytest --cov=src --cov-report=term-missing

# 启动开发服务器
PYTHONPATH=./src uvicorn podscript_api.main:app --port 8001 --reload
```

## API 手动测试

```bash
# 获取历史记录列表
curl http://localhost:8001/history?limit=5

# 获取单条记录
curl http://localhost:8001/history/abc123def456

# 更新记录（标记已读）
curl -X PATCH http://localhost:8001/history/abc123def456 \
  -H "Content-Type: application/json" \
  -d '{"viewed": true}'

# 更新标签
curl -X PATCH http://localhost:8001/history/abc123def456 \
  -H "Content-Type: application/json" \
  -d '{"tags": ["AI", "投资", "访谈"]}'

# 删除记录（软删除）
curl -X DELETE http://localhost:8001/history/abc123def456
```

## 验收清单

- [ ] `history.json` 文件正确创建和更新
- [ ] 转写完成后自动生成历史记录
- [ ] 关键词自动提取正常工作
- [ ] API 端点返回正确数据
- [ ] 首页显示历史记录列表
- [ ] 文件名点击跳转到 result.html
- [ ] 新记录红点标记正常
- [ ] 软删除后记录从列表隐藏
- [ ] 编辑标签功能可用
- [ ] 测试覆盖率 >= 80%
